"""Regression tests for BUG-02: REST Slot Participant & Anonymous Matching Protection."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock

from fastapi import HTTPException

from app.api.v1.slots import get_slot
from app.db.models.slot import Slot, SlotStatus
from app.db.models.user import User


class TestSlotAuthorization(unittest.IsolatedAsyncioTestCase):
    async def test_third_party_user_forbidden_to_view_slot(self):
        """User who is neither reviewer, reviewee nor admin must receive 403 Forbidden."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        third_party_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="minishell",
            status=SlotStatus.BOOKED.value,
        )
        third_party = User(
            id=third_party_id,
            school21_login="charlie",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )

        mock_db = AsyncMock()
        mock_db.get.return_value = slot

        with self.assertRaises(HTTPException) as cm:
            await get_slot(slot_id=slot_id, user=third_party, db=mock_db)

        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("not authorized", cm.exception.detail.lower())

    async def test_participant_allowed_to_view_slot(self):
        """Reviewer or reviewee must be allowed to view the slot."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="minishell",
            status=SlotStatus.BOOKED.value,
        )
        reviewer = User(
            id=reviewer_id,
            school21_login="alice",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )

        mock_db = AsyncMock()
        mock_db.get.return_value = slot

        result = await get_slot(slot_id=slot_id, user=reviewer, db=mock_db)
        self.assertEqual(result.id, slot_id)


if __name__ == "__main__":
    unittest.main()
