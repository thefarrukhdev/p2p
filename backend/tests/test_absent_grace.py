"""Regression tests for BUG-05: Absence Grace Period Enforcement."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.db.models.slot import Slot, SlotStatus
from app.db.models.user import User
from app.services import slot_service


class TestAbsentGrace(unittest.IsolatedAsyncioTestCase):
    async def test_premature_absent_rejected(self):
        """Calling mark_absent before 15 min after slot start must raise HTTP 400."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        # Slot starts 1 hour in the future
        future_start = datetime.now(timezone.utc) + timedelta(hours=1)
        future_end = future_start + timedelta(hours=1)

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="cub3d",
            status=SlotStatus.BOOKED.value,
            start_time=future_start,
            end_time=future_end,
        )
        reviewer = User(id=reviewer_id, school21_login="alice", is_active=True, is_logged_in=True, xp=100, peer_points=5)
        reviewee = User(id=reviewee_id, school21_login="bob", is_active=True, is_logged_in=True, xp=100, peer_points=5)

        mock_db = AsyncMock()
        mock_db.get.side_effect = lambda model, obj_id: reviewer if obj_id == reviewer_id else reviewee

        with self.assertRaises(HTTPException) as cm:
            await slot_service.mark_absent(db=mock_db, slot=slot, actor=reviewer)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("15 minutes", cm.exception.detail.lower())

    async def test_absent_allowed_after_grace_period(self):
        """Calling mark_absent 20 min after slot start must be allowed."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        # Slot started 20 minutes ago
        past_start = datetime.now(timezone.utc) - timedelta(minutes=20)
        past_end = past_start + timedelta(hours=1)

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="cub3d",
            status=SlotStatus.BOOKED.value,
            start_time=past_start,
            end_time=past_end,
        )
        reviewer = User(id=reviewer_id, school21_login="alice", is_active=True, is_logged_in=True, xp=100, peer_points=5)
        reviewee = User(id=reviewee_id, school21_login="bob", is_active=True, is_logged_in=True, xp=100, peer_points=5)

        mock_db = AsyncMock()
        mock_db.get.side_effect = lambda model, obj_id: reviewer if obj_id == reviewer_id else reviewee

        with patch("app.services.slot_service.create_notification", new_callable=AsyncMock), \
             patch("app.services.xp_service.apply_xp", new_callable=AsyncMock):
            result_slot = await slot_service.mark_absent(db=mock_db, slot=slot, actor=reviewer)

        self.assertEqual(result_slot.status, SlotStatus.ABSENT.value)
        self.assertEqual(result_slot.absent_by, reviewer_id)


if __name__ == "__main__":
    unittest.main()
