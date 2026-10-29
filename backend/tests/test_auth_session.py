"""Regression tests for BUG-03: Session Revocation & Logout Enforcement."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.auth import refresh, RefreshRequest
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token
from app.db.models.user import User


class TestAuthSessionRevocation(unittest.IsolatedAsyncioTestCase):
    async def test_logged_out_user_rejected_by_get_current_user(self):
        """User with is_logged_in=False must be rejected with 401 Unauthorized."""
        user = User(
            id=uuid.uuid4(),
            school21_login="test_logged_out",
            is_active=True,
            is_logged_in=False,  # Logged out
        )
        mock_db = AsyncMock()
        mock_db.get.return_value = user

        token = create_access_token(str(user.id))
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with self.assertRaises(HTTPException) as cm:
            await get_current_user(db=mock_db, credentials=credentials)

        self.assertEqual(cm.exception.status_code, 401)
        self.assertIn("logged out", cm.exception.detail.lower())

    async def test_logged_out_user_cannot_refresh_token(self):
        """User with is_logged_in=False cannot refresh token (must receive 401)."""
        user = User(
            id=uuid.uuid4(),
            school21_login="test_refresh_logout",
            is_active=True,
            is_logged_in=False,  # Logged out
        )
        mock_db = AsyncMock()
        mock_db.get.return_value = user

        ref_token = create_refresh_token(str(user.id))
        req = RefreshRequest(refresh_token=ref_token)

        with self.assertRaises(HTTPException) as cm:
            await refresh(payload=req, db=mock_db)

        self.assertEqual(cm.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
