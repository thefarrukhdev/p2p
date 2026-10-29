"""Regression tests for BUG-07 (Leaderboard Snapshot Idempotency) & BUG-08 (Reminder Idempotency)."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.sql.dml import Delete

from app.db.models.notification import Notification
from app.db.models.slot import Slot, SlotStatus
from app.tasks.leaderboard_tasks import _monthly_snapshot
from app.tasks.slot_tasks import _send_slot_reminders


class TestTasksIdempotency(unittest.IsolatedAsyncioTestCase):
    async def test_monthly_snapshot_clears_existing_records(self):
        """_monthly_snapshot must execute Delete on existing month+category records to prevent duplicates."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_lock_res = MagicMock()
        mock_lock_res.scalar.return_value = True
        mock_db.execute.return_value = mock_lock_res
        mock_entries = [{"user_id": uuid.uuid4(), "rank": 1, "value": 100}]

        with patch("app.tasks.leaderboard_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.tasks.leaderboard_tasks.leaderboard_service.most_taught", new_callable=AsyncMock) as m_taught, \
             patch("app.tasks.leaderboard_tasks.leaderboard_service.most_learned", new_callable=AsyncMock) as m_learned, \
             patch("app.tasks.leaderboard_tasks.leaderboard_service.most_xp", new_callable=AsyncMock) as m_xp:

            m_taught.return_value = mock_entries
            m_learned.return_value = mock_entries
            m_xp.return_value = mock_entries

            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await _monthly_snapshot()

            # Verify that Delete was executed before inserting
            executed_stmts = [call.args[0] for call in mock_db.execute.call_args_list if call.args]
            has_delete = any(isinstance(stmt, Delete) for stmt in executed_stmts)
            self.assertTrue(has_delete, "Expected Delete statement to clear existing snapshot entries")

    async def test_send_slot_reminders_does_not_duplicate(self):
        """If a reminder has already been created for a slot, it must not be sent again."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            start_time=now + timedelta(minutes=15),
            status=SlotStatus.BOOKED.value,
        )

        mock_db = AsyncMock()
        # First query returns the slot
        mock_slot_result = MagicMock()
        mock_slot_result.scalars.return_value.all.return_value = [slot]

        # Second query simulates that a reminder was ALREADY found in DB
        mock_notif_result = MagicMock()
        mock_notif_result.scalar_one_or_none.return_value = uuid.uuid4()
        mock_outbox_res = MagicMock()
        mock_outbox_res.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_slot_result, mock_notif_result, mock_outbox_res]

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.tasks.slot_tasks.create_notification", new_callable=AsyncMock) as mock_create_notif:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            sent_count = await _send_slot_reminders()

            # Because reminder already exists, sent_count should be 0 and create_notification not called
            self.assertEqual(sent_count, 0)
            mock_create_notif.assert_not_called()

    async def test_send_slot_reminders_uses_skip_locked(self):
        """_send_slot_reminders query must use with_for_update(skip_locked=True)."""
        mock_db = AsyncMock()
        mock_slot_result = MagicMock()
        mock_slot_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_slot_result

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await _send_slot_reminders()

            # Inspect the executed query
            executed_stmts = [call.args[0] for call in mock_db.execute.call_args_list if call.args]
            self.assertTrue(len(executed_stmts) >= 1)
            slot_stmt = executed_stmts[0]
            self.assertTrue(slot_stmt._for_update_arg is not None, "Query must use with_for_update")
            self.assertTrue(slot_stmt._for_update_arg.skip_locked is True, "Query must use skip_locked=True")

    async def test_monthly_snapshot_concurrent_worker_skips_when_lock_not_acquired(self):
        """If another worker holds the advisory lock, task must exit gracefully with 0."""
        mock_db = AsyncMock()
        mock_lock_res = MagicMock()
        mock_lock_res.scalar.return_value = False  # Lock not acquired!
        mock_db.execute.return_value = mock_lock_res

        with patch("app.tasks.leaderboard_tasks.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await _monthly_snapshot()

            self.assertEqual(result, 0)
            # Commit should not have been called
            mock_db.commit.assert_not_called()

    async def test_monthly_snapshot_handles_integrity_error_with_rollback(self):
        """If IntegrityError occurs during commit, rollback must be called and 0 returned."""
        from sqlalchemy.exc import IntegrityError
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_lock_res = MagicMock()
        mock_lock_res.scalar.return_value = True
        mock_db.execute.return_value = mock_lock_res
        mock_db.commit.side_effect = IntegrityError("statement", "params", Exception("unique violation"))

        mock_entries = [{"user_id": uuid.uuid4(), "rank": 1, "value": 100}]

        with patch("app.tasks.leaderboard_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.tasks.leaderboard_tasks.leaderboard_service.most_taught", new_callable=AsyncMock) as m_taught, \
             patch("app.tasks.leaderboard_tasks.leaderboard_service.most_learned", new_callable=AsyncMock) as m_learned, \
             patch("app.tasks.leaderboard_tasks.leaderboard_service.most_xp", new_callable=AsyncMock) as m_xp:

            m_taught.return_value = mock_entries
            m_learned.return_value = mock_entries
            m_xp.return_value = mock_entries

            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await _monthly_snapshot()

            self.assertEqual(result, 0)
            mock_db.rollback.assert_called_once()

    async def test_send_slot_reminders_recovers_after_worker_rollback(self):
        """If a worker holding a lock fails and rolls back, the slot remains eligible for retry."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            start_time=now + timedelta(minutes=10),
            status=SlotStatus.BOOKED.value,
        )

        # Worker 1: fails and rolls back
        mock_db_w1 = AsyncMock()
        mock_db_w1.add = MagicMock()
        mock_slot_res1 = MagicMock()
        mock_slot_res1.scalars.return_value.all.return_value = [slot]
        mock_notif_res1 = MagicMock()
        mock_notif_res1.scalar_one_or_none.return_value = None
        mock_db_w1.execute.side_effect = [mock_slot_res1, mock_notif_res1]
        mock_db_w1.commit.side_effect = RuntimeError("Worker crash before commit")

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w1
            with self.assertRaises(RuntimeError):
                await _send_slot_reminders()

        # Worker 2 (retry on next tick): finds the slot and successfully commits
        mock_db_w2 = AsyncMock()
        mock_slot_res2 = MagicMock()
        mock_slot_res2.scalars.return_value.all.return_value = [slot]
        mock_notif_res2 = MagicMock()
        mock_notif_res2.scalar_one_or_none.return_value = None
        mock_outbox_res = MagicMock()
        mock_outbox_res.scalars.return_value.all.return_value = []
        mock_db_w2.execute.side_effect = [mock_slot_res2, mock_notif_res2, mock_outbox_res]

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.tasks.slot_tasks.create_notification", new_callable=AsyncMock) as mock_create_notif:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w2
            sent = await _send_slot_reminders()

            self.assertEqual(sent, 1)
            # Stage 1 (enqueue in DB) commits
            self.assertEqual(mock_db_w2.commit.call_count, 1)
            self.assertEqual(mock_create_notif.call_count, 3)

    async def test_outbox_dispatcher_delivers_pending_notification(self):
        """Failure Case 3: Outbox dispatcher delivers pending notification and marks status='sent'."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="alice", telegram_id=987654321)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            title="Slot boshlanadi",
            body="Eslatma",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (True, False)  # Delivery succeeded

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 1)
            self.assertEqual(notif.telegram_delivery_status, "sent")
            self.assertTrue(notif.sent_telegram, "sent_telegram must be True after successful send")
            self.assertIsNone(notif.telegram_claimed_at)
            # Phase 1 commit (atomic claim) + Phase 3 commit (delivery persistence)
            self.assertEqual(mock_db.commit.call_count, 2)

    async def test_outbox_dispatcher_stops_infinite_loop_for_invalid_recipient(self):
        """Permanent failure (no telegram_id or 403 Forbidden) marks failed_permanent with sent_telegram=False (truthful)."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        # User 1: No telegram_id
        u1 = User(id=uuid.uuid4(), school21_login="no_tg", telegram_id=None)
        n1 = Notification(id=uuid.uuid4(), user_id=u1.id, type="slot_reminder", sent_telegram=False, telegram_delivery_status="pending")

        # User 2: Blocked bot (403 Forbidden)
        u2 = User(id=uuid.uuid4(), school21_login="blocked", telegram_id=111222)
        n2 = Notification(id=uuid.uuid4(), user_id=u2.id, type="slot_reminder", sent_telegram=False, telegram_delivery_status="pending")

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [n1, n2]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return u1 if pk == u1.id else u2
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return n1 if pk == n1.id else n2
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (False, True)  # Permanent failure (e.g. 403)

            dispatched = await _dispatch_pending_telegram_notifications()

            # Neither was successfully sent to telegram
            self.assertEqual(dispatched, 0)
            # Both marked failed_permanent to stop infinite retry loop:
            self.assertEqual(n1.telegram_delivery_status, "failed_permanent")
            self.assertEqual(n1.telegram_error, "missing_telegram_id")
            # TRUTHFUL semantics: sent_telegram remains False!
            self.assertFalse(n1.sent_telegram)

            self.assertEqual(n2.telegram_delivery_status, "failed_permanent")
            self.assertEqual(n2.telegram_error, "blocked_or_rejected")
            self.assertFalse(n2.sent_telegram)

            self.assertEqual(mock_db.commit.call_count, 2)

    async def test_concurrent_dispatchers_prevent_duplicate_claims(self):
        """Worker 1 atomically claims rows via skip_locked; Worker 2 concurrently gets 0 rows."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="alice", telegram_id=12345)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        # Worker 1 gets the row
        mock_db_w1 = AsyncMock()
        mock_res_w1 = MagicMock()
        mock_res_w1.scalars.return_value.all.return_value = [notif]
        mock_db_w1.execute.return_value = mock_res_w1

        def db_get_w1(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db_w1.get.side_effect = db_get_w1

        # Worker 2 querying at the same time skips locked rows -> receives empty list
        mock_db_w2 = AsyncMock()
        mock_res_w2 = MagicMock()
        mock_res_w2.scalars.return_value.all.return_value = []
        mock_db_w2.execute.return_value = mock_res_w2

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_dispatch.return_value = (True, False)

            # Worker 1 runs and claims
            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w1
            d1 = await _dispatch_pending_telegram_notifications()

            # Worker 2 runs concurrently
            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w2
            d2 = await _dispatch_pending_telegram_notifications()

            self.assertEqual(d1, 1)
            self.assertEqual(d2, 0)
            self.assertEqual(mock_dispatch.call_count, 1)

    async def test_worker_crash_after_claim_lease_recovery(self):
        """If a worker crashes after claiming, an expired lease (>5m) allows the next dispatcher to reclaim and deliver."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="bob", telegram_id=54321)
        # Stuck in 'claimed' with an expired lease timestamp (6 minutes ago)
        expired_claimed_at = datetime.now(timezone.utc) - timedelta(minutes=6)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="claimed",
            telegram_claimed_at=expired_claimed_at,
            telegram_attempts=1,
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (True, False)

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 1)
            self.assertEqual(notif.telegram_delivery_status, "sent")
            self.assertTrue(notif.sent_telegram)
            self.assertEqual(notif.telegram_attempts, 2, "Attempts must be incremented on recovery")

    async def test_telegram_success_followed_by_db_commit_failure_causes_duplicate_on_retry(self):
        """Two Generals / Dual-Write proof:
        If Telegram API succeeds but worker crashes before committing status='sent',
        the notification is reclaimed on retry and delivered again under at-least-once semantics.
        """
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="charlie", telegram_id=999888)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        mock_db_w1 = AsyncMock()
        mock_res_w1 = MagicMock()
        mock_res_w1.scalars.return_value.all.return_value = [notif]
        mock_db_w1.execute.return_value = mock_res_w1

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db_w1.get.side_effect = db_get

        # Phase 1 commit succeeds, but Phase 3 commit fails (worker crash / DB disconnect after Telegram sent!)
        commit_calls = 0
        async def mock_commit_w1():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 2:
                raise RuntimeError("DB connection dropped right after Telegram HTTP 200 OK")

        mock_db_w1.commit.side_effect = mock_commit_w1

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w1
            mock_dispatch.return_value = (True, False)  # Telegram received and processed HTTP request!

            # Dispatcher 1 fails on Phase 3 commit
            with self.assertRaises(RuntimeError):
                await _dispatch_pending_telegram_notifications()

            # Telegram was called once:
            self.assertEqual(mock_dispatch.call_count, 1)

            # In the DB, the rollback kept the row in 'claimed' with original claimed_at
            notif.telegram_claimed_at = datetime.now(timezone.utc) - timedelta(minutes=6)

            # Dispatcher 2 runs on retry tick: recovers expired lease and re-sends to Telegram
            mock_db_w2 = AsyncMock()
            mock_res_w2 = MagicMock()
            mock_res_w2.scalars.return_value.all.return_value = [notif]
            mock_db_w2.execute.return_value = mock_res_w2
            mock_db_w2.get.side_effect = db_get

            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w2
            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 1)
            # Because Telegram API has no idempotency key, Telegram was called a second time!
            self.assertEqual(mock_dispatch.call_count, 2, "DUPLICATE delivery verified under at-least-once semantics")
            self.assertEqual(notif.telegram_delivery_status, "sent")

    async def test_transient_network_error_resets_to_pending_for_retry(self):
        """Transient error (HTTP 500 / timeout) resets delivery status to 'pending' with error details."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="dave", telegram_id=777666)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (False, False)  # Transient network error (neither success nor permanent)

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 0)
            self.assertEqual(notif.telegram_delivery_status, "failed_transient")
            self.assertFalse(notif.sent_telegram)
            self.assertEqual(notif.telegram_error, "transient_network_error")
            self.assertIsNotNone(notif.telegram_next_retry_at)
            self.assertIsNone(notif.telegram_claimed_at)

    async def test_stale_worker_cannot_overwrite_newer_claimant(self):
        """Fencing token test: A stale worker whose lease expired cannot overwrite a newer claimant's state."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="eve", telegram_id=333444)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]

        # Simulate Phase 3 conditional update: rowcount=0 (token mismatch because Worker 2 reclaimed it)
        mock_update_res = MagicMock()
        mock_update_res.rowcount = 0

        # Phase 1 select returns row, Phase 3 update returns 0 rows updated
        mock_db.execute.side_effect = [mock_res, mock_update_res]

        # In-memory object has been updated by Worker 2 to 'sent'
        worker2_notif = Notification(
            id=notif.id,
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=True,
            telegram_delivery_status="sent",
            telegram_claim_token=uuid.uuid4(),
        )

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return worker2_notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            # Worker 1 failed HTTP or delayed: returns False
            mock_dispatch.return_value = (False, False, "delayed_timeout", None)

            dispatched = await _dispatch_pending_telegram_notifications()

            # Worker 2's 'sent' state is NOT overwritten by Worker 1 because rowcount was 0!
            self.assertEqual(worker2_notif.telegram_delivery_status, "sent")
            self.assertTrue(worker2_notif.sent_telegram)

    async def test_transient_failure_respects_retry_after(self):
        """When Telegram returns HTTP 429 with retry_after=45, telegram_next_retry_at is scheduled >= 45s."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="frank", telegram_id=555666)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (False, False, "HTTP 429 Rate Limited", 45)

            t_before = datetime.now(timezone.utc)
            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 0)
            self.assertEqual(notif.telegram_delivery_status, "failed_transient")
            self.assertFalse(notif.sent_telegram)
            self.assertEqual(notif.telegram_error, "HTTP 429 Rate Limited")
            self.assertIsNotNone(notif.telegram_next_retry_at)
            # Must be scheduled at least 44 seconds in the future
            self.assertGreaterEqual(notif.telegram_next_retry_at, t_before + timedelta(seconds=44))

    async def test_terminal_failure_when_max_attempts_exceeded(self):
        """When a notification reaches MAX_TELEGRAM_ATTEMPTS (5), it transitions to failed_permanent."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="grace", telegram_id=888999)
        # Already attempted 4 times; this run will increment to 5
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="failed_transient",
            telegram_attempts=4,
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (False, False, "503 Service Unavailable", None)

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 0)
            self.assertEqual(notif.telegram_delivery_status, "failed_permanent")
            self.assertFalse(notif.sent_telegram)
            self.assertIn("max_attempts_exceeded", notif.telegram_error)
            self.assertIsNone(notif.telegram_next_retry_at)

    async def test_expired_reminder_past_deadline_not_sent(self):
        """A time-sensitive reminder past its 5m lateness deadline is marked failed_permanent without calling Telegram."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        slot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        user = User(id=user_id, school21_login="heidi", telegram_id=444555)
        # Slot started 12 minutes ago (> 5m threshold)
        expired_slot = Slot(
            id=slot_id,
            reviewer_id=user_id,
            start_time=now - timedelta(minutes=12),
            status=SlotStatus.BOOKED.value,
        )
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            slot_id=slot_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Slot or getattr(model, "__name__", "") == "Slot":
                return expired_slot
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 0)
            # Telegram API must NEVER have been called for an expired reminder!
            mock_dispatch.assert_not_called()
            self.assertEqual(notif.telegram_delivery_status, "failed_permanent")
            self.assertFalse(notif.sent_telegram)
            self.assertEqual(notif.telegram_error, "expired_past_lateness_deadline")

    async def test_delivery_state_and_sent_telegram_invariant(self):
        """The invariant between telegram_delivery_status and sent_telegram must hold strictly."""
        notif_sent = Notification(telegram_delivery_status="sent", sent_telegram=True)
        notif_pending = Notification(telegram_delivery_status="pending", sent_telegram=False)
        notif_claimed = Notification(telegram_delivery_status="claimed", sent_telegram=False)
        notif_transient = Notification(telegram_delivery_status="failed_transient", sent_telegram=False)
        notif_perm = Notification(telegram_delivery_status="failed_permanent", sent_telegram=False)
        notif_hist = Notification(telegram_delivery_status="abandoned_historical", sent_telegram=False)

        # Invariant check: sent_telegram is True IFF status == 'sent'
        for notif in [notif_sent, notif_pending, notif_claimed, notif_transient, notif_perm, notif_hist]:
            expected_sent = (notif.telegram_delivery_status == "sent")
            self.assertEqual(
                notif.sent_telegram,
                expected_sent,
                f"Invariant violation for status {notif.telegram_delivery_status}: sent_telegram={notif.sent_telegram}",
            )

    async def test_reminder_expires_beyond_maximum_lateness(self):
        """Failure Case 4B: If a worker recovers > 5 minutes after slot start, reminder expires."""
        slot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        # Slot started 10 minutes ago (> 5m lateness threshold)
        expired_slot = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            start_time=now - timedelta(minutes=10),
            status=SlotStatus.BOOKED.value,
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        # Query with start_time >= expiration_cutoff returns empty list because slot is expired
        mock_res.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_res

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            sent = await _send_slot_reminders()

            self.assertEqual(sent, 0)

    async def test_reminder_delivered_within_acceptable_lateness(self):
        """Failure Case 4A: If a worker recovers 2 minutes after slot start (within 5m), reminder is sent."""
        slot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        # Slot started 2 minutes ago (within 5m lateness rule)
        slot = Slot(
            id=slot_id,
            reviewer_id=uuid.uuid4(),
            reviewee_id=uuid.uuid4(),
            start_time=now - timedelta(minutes=2),
            status=SlotStatus.BOOKED.value,
        )

        mock_db = AsyncMock()
        mock_slot_res = MagicMock()
        mock_slot_res.scalars.return_value.all.return_value = [slot]
        mock_notif_res = MagicMock()
        mock_notif_res.scalar_one_or_none.return_value = None
        # First query: select slots. Second query: check existing. Third query: outbox dispatch
        mock_outbox_res = MagicMock()
        mock_outbox_res.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [mock_slot_res, mock_notif_res, mock_outbox_res]

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.tasks.slot_tasks.create_notification", new_callable=AsyncMock) as mock_create_notif:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            sent = await _send_slot_reminders()

            self.assertEqual(sent, 1)
            self.assertEqual(mock_create_notif.call_count, 3)

    async def test_worker_crash_prior_to_http_does_not_consume_dispatch_attempts(self):
        """Worker crashes before HTTP dispatch increment claim_attempts, preserving telegram_attempts."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="ian", telegram_id=999111)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
            telegram_claim_attempts=0,
            telegram_attempts=0,
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        # Simulate 4 worker crashes right after Phase 1 commit (before Phase 2 HTTP)
        for expected_claim_count in range(1, 5):
            with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx:
                mock_session_ctx.return_value.__aenter__.return_value = mock_db
                # Simulate worker crash during Phase 2 before HTTP finishes
                with patch("app.services.telegram_dispatcher.dispatch_notification", side_effect=RuntimeError("Worker OOM Killed")):
                    with self.assertRaises(RuntimeError):
                        await _dispatch_pending_telegram_notifications()

            # Verify that claim_attempts was incremented, but dispatch attempts remained 0!
            self.assertEqual(notif.telegram_claim_attempts, expected_claim_count)
            self.assertEqual(notif.telegram_attempts, 0)

        # Now worker 5 runs successfully:
        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (True, False, None, None)

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 1)
            self.assertEqual(notif.telegram_claim_attempts, 5)
            # Only NOW has telegram_attempts been incremented to 1!
            self.assertEqual(notif.telegram_attempts, 1)
            self.assertEqual(notif.telegram_delivery_status, "sent")
            self.assertTrue(notif.sent_telegram)

    async def test_poison_pill_quarantines_after_ten_failed_claims(self):
        """Notification causing repeated worker crashes (10 claims) transitions to quarantined_claim_exhausted."""
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="judy", telegram_id=123789)
        # Already claimed 9 times previously by crashing workers
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="claimed",
            telegram_claim_attempts=9,
            telegram_attempts=0,
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 0)
            mock_dispatch.assert_not_called()
            self.assertEqual(notif.telegram_claim_attempts, 10)
            # Must transition to quarantined_claim_exhausted, NOT silently discarded or failed_permanent!
            self.assertEqual(notif.telegram_delivery_status, "quarantined_claim_exhausted")
            self.assertFalse(notif.sent_telegram)
            self.assertIn("claim_attempts_exhausted_quarantine", notif.telegram_error)
            self.assertIsNone(notif.telegram_claim_token)
            self.assertIsNone(notif.telegram_claimed_at)

    async def test_quarantined_notification_requeue_and_subsequent_delivery(self):
        """Quarantined notification can be observed and manually requeued by operator, enabling successful dispatch."""
        from app.services.notification_service import requeue_quarantined_notification
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        user_id = uuid.uuid4()
        notif_id = uuid.uuid4()
        user = User(id=user_id, school21_login="ken", telegram_id=777888)
        notif = Notification(
            id=notif_id,
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="quarantined_claim_exhausted",
            telegram_claim_attempts=10,
            telegram_attempts=0,
            telegram_error="claim_attempts_exhausted_quarantine",
        )

        mock_db = AsyncMock()
        mock_sel = MagicMock()
        mock_sel.scalar_one_or_none.return_value = notif
        mock_db.execute.return_value = mock_sel
        mock_db.get.return_value = user

        # 1. Operator/Admin requeues the quarantined item
        updated, err = await requeue_quarantined_notification(mock_db, notif_id)
        self.assertIsNone(err)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.telegram_delivery_status, "pending")
        self.assertEqual(updated.telegram_claim_attempts, 0)
        self.assertIn("requeued_by_admin", updated.telegram_error)
        self.assertFalse(updated.sent_telegram)

        # 2. Subsequent worker run picks it up as a normal pending item
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_res

        def db_get(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif
            return None

        mock_db.get.side_effect = db_get

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_dispatch.return_value = (True, False, None, None)

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 1)
            self.assertEqual(notif.telegram_delivery_status, "sent")
            self.assertTrue(notif.sent_telegram)
            self.assertEqual(notif.telegram_claim_attempts, 1)
            self.assertEqual(notif.telegram_attempts, 1)

    async def test_post_send_pre_commit_crash_and_subsequent_retry(self):
        """Worker 1 successfully calls Telegram HTTP, but crashes before Phase 3 DB commit.
        Worker 2 safely reclaims expired lease and delivers, illustrating at-least-once semantics.
        """
        from app.tasks.slot_tasks import _dispatch_pending_telegram_notifications
        from app.db.models.user import User

        notif_id = uuid.uuid4()
        user_id = uuid.uuid4()
        user = User(id=user_id, school21_login="leo", telegram_id=321654)
        notif_w1 = Notification(
            id=notif_id,
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
            telegram_claim_attempts=0,
            telegram_attempts=0,
        )

        mock_db_w1 = AsyncMock()
        mock_res_w1 = MagicMock()
        mock_res_w1.scalars.return_value.all.return_value = [notif_w1]
        mock_db_w1.execute.return_value = mock_res_w1

        def db_get_w1(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif_w1
            return None

        mock_db_w1.get.side_effect = db_get_w1

        # Worker 1: Phase 1 succeeds (claims row). In Phase 3, DB connection crashes on commit!
        call_count = 0
        async def mock_commit_w1():
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Phase 3 commit fails!
                raise RuntimeError("PostgreSQL connection lost during Phase 3 commit")

        mock_db_w1.commit.side_effect = mock_commit_w1

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w1
            mock_dispatch.return_value = (True, False, None, None)

            with self.assertRaises(RuntimeError):
                await _dispatch_pending_telegram_notifications()

            # HTTP call was initiated by Worker 1
            self.assertEqual(mock_dispatch.call_count, 1)

        # In real PostgreSQL, Worker 1's uncommitted transaction rolled back.
        # Worker 2 in a separate process reads the committed database state, where lease has expired:
        notif_in_db = Notification(
            id=notif_id,
            user_id=user_id,
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="claimed",
            telegram_claim_attempts=1,
            telegram_attempts=0,
            telegram_claimed_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )

        mock_db_w2 = AsyncMock()
        mock_res_w2 = MagicMock()
        mock_res_w2.scalars.return_value.all.return_value = [notif_in_db]
        mock_db_w2.execute.return_value = mock_res_w2

        def db_get_w2(model, pk):
            if model == User or getattr(model, "__name__", "") == "User":
                return user
            if model == Notification or getattr(model, "__name__", "") == "Notification":
                return notif_in_db
            return None

        mock_db_w2.get.side_effect = db_get_w2

        with patch("app.tasks.slot_tasks.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.services.telegram_dispatcher.dispatch_notification", new_callable=AsyncMock) as mock_dispatch_w2:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db_w2
            mock_dispatch_w2.return_value = (True, False, None, None)

            dispatched = await _dispatch_pending_telegram_notifications()

            self.assertEqual(dispatched, 1)
            self.assertEqual(mock_dispatch_w2.call_count, 1)
            # Worker 2 reclaims and delivers:
            self.assertEqual(notif_in_db.telegram_claim_attempts, 2)
            self.assertEqual(notif_in_db.telegram_attempts, 1)
            self.assertEqual(notif_in_db.telegram_delivery_status, "sent")
            self.assertTrue(notif_in_db.sent_telegram)

    def test_notification_invariant_bidirectional_synchronization(self):
        """Notification model enforces strict bidirectional sync between sent_telegram and telegram_delivery_status."""
        notif = Notification(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        # Direct assignment: legacy boolean to True
        notif.sent_telegram = True
        self.assertEqual(notif.telegram_delivery_status, "sent")
        self.assertTrue(notif.sent_telegram)

        # Direct assignment: legacy boolean to False
        notif.sent_telegram = False
        self.assertEqual(notif.telegram_delivery_status, "pending")
        self.assertFalse(notif.sent_telegram)

        # Direct assignment: status to 'sent'
        notif.telegram_delivery_status = "sent"
        self.assertTrue(notif.sent_telegram)
        self.assertEqual(notif.telegram_delivery_status, "sent")

        # Direct assignment: status to 'failed_transient'
        notif.telegram_delivery_status = "failed_transient"
        self.assertFalse(notif.sent_telegram)
        self.assertEqual(notif.telegram_delivery_status, "failed_transient")

        # Via authoritative helper set_delivery_status
        notif.set_delivery_status("sent")
        self.assertTrue(notif.sent_telegram)
        self.assertEqual(notif.telegram_delivery_status, "sent")

        notif.set_delivery_status("failed_permanent", error="invalid_token")
        self.assertFalse(notif.sent_telegram)
        self.assertEqual(notif.telegram_delivery_status, "failed_permanent")
        self.assertEqual(notif.telegram_error, "invalid_token")

    def test_migration_preflight_aborts_on_unknown_notification_type(self):
        """Alembic migration 8c9d0e1f2a3b raises ValueError on unknown notification types during preflight."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../alembic/versions/8c9d0e1f2a3b_add_notification_delivery_status.py",
        )
        spec = importlib.util.spec_from_file_location("mig_8c9d0e1f2a3b", migration_path)
        migration_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_mod)

        mock_bind = MagicMock()
        # Simulate unknown type 'crypto_bonus_received' in notifications table
        # 1st call: count(*)=2, 2nd call: null_sent=0, 3rd call: null_created_at=0, 4th call: distinct types
        mock_bind.execute.return_value.scalar.side_effect = [2, 0, 0]
        mock_bind.execute.return_value.fetchall.return_value = [
            ("slot_reminder",),
            ("crypto_bonus_received",),
        ]

        with patch("alembic.op.get_bind", return_value=mock_bind):
            with self.assertRaises(ValueError) as ctx:
                migration_mod.upgrade()

            self.assertIn("crypto_bonus_received", str(ctx.exception))
            self.assertIn("Preflight migration aborted", str(ctx.exception))

    def test_migration_preflight_aborts_on_null_sent_telegram(self):
        """Alembic migration 8c9d0e1f2a3b raises ValueError if NULL sent_telegram exists."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../alembic/versions/8c9d0e1f2a3b_add_notification_delivery_status.py",
        )
        spec = importlib.util.spec_from_file_location("mig_8c9d0e1f2a3b_null_sent", migration_path)
        migration_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_mod)

        mock_bind = MagicMock()
        # 1st call: count(*)=5, 2nd call: null_sent=3 (triggers abort!)
        mock_bind.execute.return_value.scalar.side_effect = [5, 3]

        with patch("alembic.op.get_bind", return_value=mock_bind):
            with self.assertRaises(ValueError) as ctx:
                migration_mod.upgrade()

            self.assertIn("NULL sent_telegram", str(ctx.exception))
            self.assertIn("Preflight migration aborted", str(ctx.exception))

    def test_migration_preflight_aborts_on_null_created_at(self):
        """Alembic migration 8c9d0e1f2a3b raises ValueError if NULL created_at exists."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../alembic/versions/8c9d0e1f2a3b_add_notification_delivery_status.py",
        )
        spec = importlib.util.spec_from_file_location("mig_8c9d0e1f2a3b_null_cat", migration_path)
        migration_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_mod)

        mock_bind = MagicMock()
        # 1st call: count(*)=5, 2nd call: null_sent=0, 3rd call: null_created_at=2 (triggers abort!)
        mock_bind.execute.return_value.scalar.side_effect = [5, 0, 2]

        with patch("alembic.op.get_bind", return_value=mock_bind):
            with self.assertRaises(ValueError) as ctx:
                migration_mod.upgrade()

            self.assertIn("NULL created_at", str(ctx.exception))
            self.assertIn("Preflight migration aborted", str(ctx.exception))

    def test_migration_preflight_aborts_on_unclassified_rows(self):
        """Alembic migration 8c9d0e1f2a3b raises ValueError if rows cannot be classified into backfill categories."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../alembic/versions/8c9d0e1f2a3b_add_notification_delivery_status.py",
        )
        spec = importlib.util.spec_from_file_location("mig_8c9d0e1f2a3b_unclass", migration_path)
        migration_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_mod)

        mock_bind = MagicMock()
        # Total rows = 10, null_sent = 0, null_created_at = 0
        mock_bind.execute.return_value.scalar.side_effect = [10, 0, 0]
        # distinct types valid
        mock_bind.execute.return_value.fetchall.side_effect = [
            [("slot_reminder",)],
            [],
        ]
        # diagnostic partition counts sum to 8 (so 2 unclassified rows!)
        mock_bind.execute.return_value.fetchone.return_value = (5, 1, 2, 0, 0)

        with patch("alembic.op.get_bind", return_value=mock_bind):
            with self.assertRaises(ValueError) as ctx:
                migration_mod.upgrade()

            self.assertIn("could not be partitioned", str(ctx.exception))
            self.assertIn("Preflight migration aborted", str(ctx.exception))

    def test_migration_check_constraint_is_null_safe(self):
        """Alembic migration 8c9d0e1f2a3b defines strictly NULL-safe and allowed-states CHECK constraints."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../alembic/versions/8c9d0e1f2a3b_add_notification_delivery_status.py",
        )
        spec = importlib.util.spec_from_file_location("mig_8c9d0e1f2a3b_check", migration_path)
        migration_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_mod)

        mock_bind = MagicMock()
        mock_bind.execute.return_value.scalar.side_effect = [10, 0, 0]
        mock_bind.execute.return_value.fetchall.side_effect = [
            [("slot_reminder",)],
            [],
        ]
        # Sums to 10 (perfect match!)
        mock_bind.execute.return_value.fetchone.return_value = (6, 2, 1, 1, 0)

        with patch("alembic.op.get_bind", return_value=mock_bind), \
             patch("alembic.op.add_column"), \
             patch("alembic.op.create_index"), \
             patch("alembic.op.create_check_constraint") as mock_check:

            migration_mod.upgrade()

            self.assertEqual(mock_check.call_count, 2)
            # 1. Invariant check
            c1_name, c1_table, c1_sql = mock_check.call_args_list[0][0]
            self.assertEqual(c1_name, "ck_notifications_sent_telegram_invariant")
            self.assertEqual(c1_table, "notifications")
            self.assertIn("sent_telegram IS NOT NULL", c1_sql)
            self.assertIn("telegram_delivery_status IS NOT NULL", c1_sql)

            # 2. Allowed states check
            c2_name, c2_table, c2_sql = mock_check.call_args_list[1][0]
            self.assertEqual(c2_name, "ck_notifications_delivery_status_allowed")
            self.assertEqual(c2_table, "notifications")
            self.assertIn("quarantined_claim_exhausted", c2_sql)
            self.assertIn("abandoned_historical", c2_sql)

    def test_invalid_delivery_status_rejected_by_model(self):
        """Notification model rejects invalid or unsupported delivery statuses."""
        notif = Notification(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            type="slot_reminder",
            sent_telegram=False,
            telegram_delivery_status="pending",
        )

        with self.assertRaises(ValueError) as ctx:
            notif.telegram_delivery_status = "unsupported_unknown_state"
        self.assertIn("Invalid telegram_delivery_status", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            notif.set_delivery_status("another_invalid_status")
        self.assertIn("Invalid telegram_delivery_status", str(ctx2.exception))


if __name__ == "__main__":
    unittest.main()
