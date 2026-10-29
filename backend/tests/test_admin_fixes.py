"""Regression tests for BUG-06 (Admin Resolve Refund) and BUG-11 (User Deletion Safety)."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.api.v1.admin import (
    delete_user,
    list_quarantined_notifications,
    resolve_slot,
    retry_quarantined_notification,
)
from app.db.models.notification import Notification
from app.db.models.slot import Slot, SlotStatus
from app.db.models.user import User


class TestAdminFixes(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_already_cancelled_slot_raises_conflict(self):
        """Calling resolve_slot on an already CANCELLED slot must raise 409 Conflict."""
        slot_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            reviewee_id=reviewee_id,
            reviewer_project="philosophers",
            status=SlotStatus.CANCELLED.value,  # Already cancelled!
        )
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = slot
        mock_db.execute.return_value = mock_res

        with self.assertRaises(HTTPException) as cm:
            await resolve_slot(slot_id=slot_id, admin=admin, db=mock_db)

        self.assertEqual(cm.exception.status_code, 409)
        self.assertIn("cannot be resolved", cm.exception.detail.lower())

    async def test_resolve_slot_atomic_refund_and_locking(self):
        """resolve_slot must lock Slot then User and refund 1 point atomically."""
        slot_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            reviewee_id=reviewee_id,
            reviewer_project="philosophers",
            status=SlotStatus.BOOKED.value,
        )
        reviewee = User(
            id=reviewee_id,
            school21_login="charlie",
            peer_points=2,
            is_active=True,
            is_logged_in=True,
        )
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.side_effect = [slot, reviewee]
        mock_db.execute.return_value = mock_res

        resolved = await resolve_slot(slot_id=slot_id, admin=admin, db=mock_db)

        self.assertEqual(resolved.status, SlotStatus.CANCELLED.value)
        self.assertEqual(reviewee.peer_points, 3)  # Refunded 1 point
        mock_db.commit.assert_called_once()

    async def test_resolve_slot_rollback_on_failure(self):
        """If database commit fails during refund, db.rollback() must be executed."""
        slot_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            reviewee_id=reviewee_id,
            reviewer_project="philosophers",
            status=SlotStatus.BOOKED.value,
        )
        reviewee = User(
            id=reviewee_id,
            school21_login="charlie",
            peer_points=2,
            is_active=True,
            is_logged_in=True,
        )
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.side_effect = [slot, reviewee]
        mock_db.execute.return_value = mock_res
        mock_db.commit.side_effect = RuntimeError("DB write error")

        with self.assertRaises(RuntimeError):
            await resolve_slot(slot_id=slot_id, admin=admin, db=mock_db)

        mock_db.rollback.assert_called_once()

    async def test_resolve_slot_simultaneous_attempts_prevents_double_refund(self):
        """Two simultaneous admin attempts: first succeeds, second gets 409 and does not double-refund."""
        slot_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        initial_points = 2

        reviewee = User(
            id=reviewee_id,
            school21_login="charlie",
            peer_points=initial_points,
            is_active=True,
            is_logged_in=True,
        )
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)

        # Attempt 1: Slot is BOOKED
        slot_attempt1 = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            reviewee_id=reviewee_id,
            reviewer_project="philosophers",
            status=SlotStatus.BOOKED.value,
        )
        mock_db1 = AsyncMock()
        mock_res1 = MagicMock()
        mock_res1.scalar_one_or_none.side_effect = [slot_attempt1, reviewee]
        mock_db1.execute.return_value = mock_res1

        await resolve_slot(slot_id=slot_id, admin=admin, db=mock_db1)
        # First attempt refunds 1 point and sets CANCELLED
        self.assertEqual(reviewee.peer_points, initial_points + 1)
        self.assertEqual(slot_attempt1.status, SlotStatus.CANCELLED.value)

        # Attempt 2 (concurrent admin whose lock unblocks after Attempt 1 commits):
        # Database now returns the slot in CANCELLED state
        slot_attempt2 = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            reviewee_id=reviewee_id,
            reviewer_project="philosophers",
            status=SlotStatus.CANCELLED.value,
        )
        mock_db2 = AsyncMock()
        mock_res2 = MagicMock()
        mock_res2.scalar_one_or_none.return_value = slot_attempt2
        mock_db2.execute.return_value = mock_res2

        with self.assertRaises(HTTPException) as cm:
            await resolve_slot(slot_id=slot_id, admin=admin, db=mock_db2)

        self.assertEqual(cm.exception.status_code, 409)
        # Crucial: reviewee points must NOT be incremented again (must still be 3, not 4!)
        self.assertEqual(reviewee.peer_points, initial_points + 1)

    async def test_delete_user_with_dependencies_deactivates_safely(self):
        """Deleting a user with slot history must soft-deactivate instead of hard deleting (avoiding FK errors)."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            school21_login="active_student",
            is_active=True,
            is_logged_in=True,
        )
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)

        mock_db = AsyncMock()
        mock_db.get.return_value = user

        # Simulate user having existing slots
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = Slot(id=uuid.uuid4(), reviewer_id=user_id)
        mock_db.execute.return_value = mock_result

        await delete_user(user_id=user_id, admin=admin, db=mock_db)

        # Hard delete should NOT be called
        mock_db.delete.assert_not_called()
        # Soft deactivate should be applied
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_logged_in)

    async def test_delete_user_without_dependencies_hard_deletes(self):
        """Deleting a user with NO relations anywhere executes hard delete."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            school21_login="ghost_user",
            is_active=True,
            is_logged_in=True,
        )
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)

        mock_db = AsyncMock()
        mock_db.get.return_value = user

        # Simulate user having NO records in any dependent table
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        await delete_user(user_id=user_id, admin=admin, db=mock_db)

        # Hard delete should be called
        mock_db.delete.assert_called_once_with(user)

    async def test_list_quarantined_notifications(self):
        """Admin can list all notifications in quarantined_claim_exhausted status."""
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="quarantined_claim_exhausted",
            telegram_claim_attempts=10,
            telegram_error="claim_attempts_exhausted_quarantine",
        )
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        res = await list_quarantined_notifications(admin=admin, db=mock_db, limit=50)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], str(notif.id))
        self.assertEqual(res[0]["claim_attempts"], 10)

    async def test_retry_quarantined_notification_resets_state(self):
        """Admin can retry a quarantined notification, resetting it back to pending with 0 claim attempts."""
        from datetime import datetime, timezone
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)
        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="valid_user", telegram_id=555666)
        notif_id = uuid.uuid4()
        notif = Notification(
            id=notif_id,
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="quarantined_claim_exhausted",
            telegram_claim_attempts=10,
            telegram_attempts=2,
            telegram_error="claim_attempts_exhausted_quarantine",
        )
        mock_db = AsyncMock()
        mock_sel = MagicMock()
        mock_sel.scalar_one_or_none.return_value = notif
        mock_db.execute.return_value = mock_sel
        mock_db.get.return_value = user

        res = await retry_quarantined_notification(
            notification_id=notif_id, admin=admin, db=mock_db
        )
        self.assertEqual(res["status"], "requeued")
        self.assertEqual(res["delivery_status"], "pending")
        self.assertEqual(res["claim_attempts"], 0)
        # Verify attempts is preserved:
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(notif.telegram_delivery_status, "pending")
        self.assertEqual(notif.telegram_claim_attempts, 0)
        self.assertEqual(notif.telegram_attempts, 2)
        self.assertIn("requeued_by_admin", notif.telegram_error)
        mock_db.commit.assert_awaited_once()

    async def test_retry_non_quarantined_notification_raises_409_conflict(self):
        """Attempting to retry a notification that is not in quarantined status raises 409 Conflict."""
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)
        notif_id = uuid.uuid4()
        notif = Notification(
            id=notif_id,
            user_id=uuid.uuid4(),
            type="slot_reminder",
            sent_telegram=True,
            telegram_delivery_status="sent",
        )
        mock_db = AsyncMock()
        mock_sel = MagicMock()
        mock_sel.scalar_one_or_none.return_value = notif
        mock_db.execute.return_value = mock_sel

        with self.assertRaises(HTTPException) as cm:
            await retry_quarantined_notification(
                notification_id=notif_id, admin=admin, db=mock_db
            )
        self.assertEqual(cm.exception.status_code, 409)
        self.assertIn("sent", cm.exception.detail)

    async def test_retry_missing_notification_raises_404(self):
        """Attempting to retry a notification that does not exist raises 404 Not Found."""
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)
        notif_id = uuid.uuid4()
        mock_db = AsyncMock()
        mock_sel = MagicMock()
        mock_sel.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_sel

        with self.assertRaises(HTTPException) as cm:
            await retry_quarantined_notification(
                notification_id=notif_id, admin=admin, db=mock_db
            )
        self.assertEqual(cm.exception.status_code, 404)

    async def test_retry_notification_missing_telegram_id_raises_400(self):
        """Attempting to retry a notification whose recipient has no telegram_id raises 400 Bad Request."""
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)
        user_id = uuid.uuid4()
        user_no_tg = User(id=user_id, school21_login="no_tg_user", telegram_id=None)
        notif_id = uuid.uuid4()
        notif = Notification(
            id=notif_id,
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="quarantined_claim_exhausted",
            telegram_claim_attempts=10,
        )
        mock_db = AsyncMock()
        mock_sel = MagicMock()
        mock_sel.scalar_one_or_none.return_value = notif
        mock_db.execute.return_value = mock_sel
        mock_db.get.return_value = user_no_tg

        with self.assertRaises(HTTPException) as cm:
            await retry_quarantined_notification(
                notification_id=notif_id, admin=admin, db=mock_db
            )
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Telegram account", cm.exception.detail)
        # Notification should have transitioned to failed_permanent
        self.assertEqual(notif.telegram_delivery_status, "failed_permanent")

    async def test_retry_expired_reminder_raises_400(self):
        """Attempting to retry an expired reminder past its 5m lateness deadline raises 400 Bad Request."""
        from datetime import datetime, timedelta, timezone
        admin = User(id=uuid.uuid4(), is_admin=True, is_active=True, is_logged_in=True)
        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="student", telegram_id=123456)
        slot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        # Slot started 15 minutes ago (> 5m threshold)
        expired_slot = Slot(
            id=slot_id,
            reviewer_id=user_id,
            start_time=now - timedelta(minutes=15),
            status=SlotStatus.BOOKED.value,
        )
        notif_id = uuid.uuid4()
        notif = Notification(
            id=notif_id,
            user_id=user_id,
            slot_id=slot_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="quarantined_claim_exhausted",
            telegram_claim_attempts=10,
        )
        mock_db = AsyncMock()
        mock_sel = MagicMock()
        mock_sel.scalar_one_or_none.return_value = notif
        mock_db.execute.return_value = mock_sel

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Slot or getattr(model, "__name__", "") == "Slot":
                return expired_slot
            return None

        mock_db.get.side_effect = db_get

        with self.assertRaises(HTTPException) as cm:
            await retry_quarantined_notification(
                notification_id=notif_id, admin=admin, db=mock_db
            )
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("lateness deadline", cm.exception.detail)
        self.assertEqual(notif.telegram_delivery_status, "failed_permanent")

    async def test_non_admin_user_rejected_by_get_current_admin(self):
        """Non-admin user calling get_current_admin is rejected with 403 Forbidden."""
        from app.core.dependencies import get_current_admin
        regular_user = User(id=uuid.uuid4(), is_admin=False, is_active=True, is_logged_in=True)
        with self.assertRaises(HTTPException) as cm:
            await get_current_admin(user=regular_user)
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("Admin access required", cm.exception.detail)


if __name__ == "__main__":
    unittest.main()
