"""Regression tests for BUG-04: Slot Booking Concurrency & Row Locking."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.sql.selectable import Select

from app.db.models.slot import Slot, SlotStatus
from app.db.models.user import User
from app.services import slot_service


class TestBookingConcurrency(unittest.IsolatedAsyncioTestCase):
    async def test_booking_uses_row_locking_on_slot_and_user(self):
        """book_slot must execute select with with_for_update() to prevent race conditions."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewer_project="ft_printf",
            status=SlotStatus.OPEN.value,
        )
        reviewee = User(
            id=reviewee_id,
            school21_login="bob",
            peer_points=1,
            is_active=True,
            is_logged_in=True,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [slot, reviewee]
        mock_db.execute.return_value = mock_result

        with patch("app.services.slot_service.create_notification", new_callable=AsyncMock):
            await slot_service.book_slot(
                db=mock_db,
                slot=slot,
                reviewee=reviewee,
                reviewee_project="libft",
            )

        # Verify that db.execute was called with a Select query having for_update
        executed_stmts = [call.args[0] for call in mock_db.execute.call_args_list if call.args]
        self.assertTrue(len(executed_stmts) >= 1, "Expected select statements to be executed")

        has_for_update = False
        has_populate_existing = False
        for stmt in executed_stmts:
            if isinstance(stmt, Select):
                if stmt._for_update_arg is not None:
                    has_for_update = True
                if stmt._execution_options.get("populate_existing") is True:
                    has_populate_existing = True

        self.assertTrue(has_for_update, "select statement did not have with_for_update() enabled")
        self.assertTrue(has_populate_existing, "select statement did not have populate_existing=True enabled")

    async def test_book_already_booked_slot_raises_conflict(self):
        """Attempting to book a slot that changed status to BOOKED must raise 409 Conflict."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        # Slot was open in caller, but locked slot returned from DB is now BOOKED (concurrency)
        caller_slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewer_project="ft_printf",
            status=SlotStatus.OPEN.value,
        )
        locked_db_slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewer_project="ft_printf",
            status=SlotStatus.BOOKED.value,  # Already taken by another worker!
        )
        reviewee = User(
            id=reviewee_id,
            school21_login="bob",
            peer_points=5,
            is_active=True,
            is_logged_in=True,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = locked_db_slot
        mock_db.execute.return_value = mock_result

        with self.assertRaises(HTTPException) as cm:
            await slot_service.book_slot(
                db=mock_db,
                slot=caller_slot,
                reviewee=reviewee,
                reviewee_project="libft",
            )

        self.assertEqual(cm.exception.status_code, 409)
        self.assertIn("not open", cm.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
