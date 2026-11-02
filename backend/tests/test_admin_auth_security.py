"""Regression tests for Admin Authentication security:
1. Default admin/admin123 credentials must never authenticate.
2. Unconfigured admin credentials must never grant access.
3. Database is_admin and is_active authorization must be strictly enforced.
4. Revoked administrator sessions must be terminated immediately.
"""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.requests import Request

from admin.setup import AdminAuth
from app.core.config import settings
from app.core.security import create_access_token
from app.db.models.user import User


def make_admin_login_request(username: str, password: str, client_ip: str = "127.0.0.1") -> Request:
    async def receive():
        return {
            "type": "http.request",
            "body": f"username={username}&password={password}".encode(),
            "more_body": False,
        }

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/admin/login",
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
            "session": {},
            "client": (client_ip, 12345),
        },
        receive=receive,
    )


def make_authenticated_request(token: str | None, client_ip: str = "127.0.0.1") -> Request:
    req = Request({
        "type": "http",
        "method": "GET",
        "path": "/admin/",
        "headers": [],
        "session": {"admin_token": token} if token else {},
        "client": (client_ip, 12345),
    })
    # Mock url_for for redirect
    req.scope["router"] = MagicMock()
    req.url_for = lambda name: f"http://test/admin/{name.split(':')[-1]}"
    return req


class TestAdminAuthSecurity(unittest.IsolatedAsyncioTestCase):
    async def test_default_admin_admin123_rejected(self):
        """Default credentials admin/admin123 must be unconditionally rejected."""
        auth = AdminAuth(secret_key="test-key")
        req = make_admin_login_request("admin", "admin123")

        with patch.object(settings, "ADMIN_USERNAME", "admin"), \
             patch.object(settings, "ADMIN_PASSWORD", "admin123"):
            result = await auth.login(req)
            self.assertFalse(result)
            self.assertNotIn("admin_token", req.session)

    async def test_unconfigured_admin_credentials_rejected(self):
        """When ADMIN_USERNAME/ADMIN_PASSWORD are not configured, static login fails."""
        auth = AdminAuth(secret_key="test-key")
        req = make_admin_login_request("admin", "somepassword")

        with patch.object(settings, "ADMIN_USERNAME", ""), \
             patch.object(settings, "ADMIN_PASSWORD", ""), \
             patch("app.services.school21_client.school21_client.login", side_effect=Exception("S21 failed")):
            result = await auth.login(req)
            self.assertFalse(result)
            self.assertNotIn("admin_token", req.session)

    async def test_non_admin_database_user_rejected(self):
        """School21 authenticated user with is_admin=False cannot access admin panel."""
        auth = AdminAuth(secret_key="test-key")
        req = make_admin_login_request("regular_student", "password123")

        user = User(
            id=uuid.uuid4(),
            school21_login="regular_student",
            is_active=True,
            is_admin=False,  # Not an admin!
        )

        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "valid"}

        with patch("app.services.school21_client.school21_client", mock_s21), \
             patch("admin.setup.AsyncSessionLocal", return_value=mock_db), \
             patch.object(settings, "ADMIN_USERNAME", ""), \
             patch.object(settings, "ADMIN_PASSWORD", ""):
            result = await auth.login(req)
            self.assertFalse(result)
            self.assertNotIn("admin_token", req.session)

    async def test_active_admin_database_user_succeeds(self):
        """School21 authenticated user with is_admin=True and is_active=True succeeds."""
        auth = AdminAuth(secret_key="test-key")
        req = make_admin_login_request("admin_hero", "password123")

        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            school21_login="admin_hero",
            is_active=True,
            is_admin=True,
        )

        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_res

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "valid"}

        with patch("app.services.school21_client.school21_client", mock_s21), \
             patch("admin.setup.AsyncSessionLocal", return_value=mock_db), \
             patch.object(settings, "ADMIN_USERNAME", ""), \
             patch.object(settings, "ADMIN_PASSWORD", ""):
            result = await auth.login(req)
            self.assertTrue(result)
            self.assertIn("admin_token", req.session)

    async def test_revoked_or_inactive_admin_session_terminated(self):
        """When an admin's is_active or is_admin is revoked, authenticate() terminates session."""
        auth = AdminAuth(secret_key="test-key")
        user_id = uuid.uuid4()
        token = create_access_token(str(user_id), {"admin": True, "sub": str(user_id)})
        req = make_authenticated_request(token)

        # User is now deactivated
        revoked_user = User(
            id=user_id,
            school21_login="former_admin",
            is_active=False,
            is_admin=True,
        )

        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.get.return_value = revoked_user

        with patch("admin.setup.AsyncSessionLocal", return_value=mock_db):
            res = await auth.authenticate(req)
            # Must return RedirectResponse (302) and clear session
            self.assertNotEqual(res, True)
            self.assertEqual(res.status_code, 302)
            self.assertNotIn("admin_token", req.session)
