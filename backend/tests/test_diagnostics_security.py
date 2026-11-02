"""Regression and security tests for Diagnostics Endpoint Protection and System Diagnostics."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.v1.diagnostics import get_system_diagnostics
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.db.models.user import User
from app.main import app


class TestDiagnosticsSecurity(unittest.IsolatedAsyncioTestCase):
    """Verify RBAC and authentication enforcement on GET /api/v1/diagnostics."""

    def setUp(self) -> None:
        self.mock_db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_anonymous_user_rejected_with_401(self) -> None:
        """Anonymous requests without Authorization header must be rejected with 401."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/diagnostics")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "Not authenticated")

    async def test_invalid_jwt_token_rejected_with_401(self) -> None:
        """Requests with malformed or invalid JWT tokens must be rejected with 401."""
        headers = {"Authorization": "Bearer malformed.jwt.token"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/diagnostics", headers=headers)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "Invalid or expired token")

    async def test_regular_user_forbidden_with_403(self) -> None:
        """Authenticated non-admin users must be rejected with 403 Forbidden."""
        user_id = uuid.uuid4()
        token = create_access_token(str(user_id))
        regular_user = User(
            id=user_id,
            school21_login="regular_peer",
            is_admin=False,
            is_active=True,
            is_logged_in=True,
        )
        self.mock_db.get.return_value = regular_user

        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/diagnostics", headers=headers)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("detail"), "Admin access required")

    async def test_active_admin_allowed_with_200(self) -> None:
        """Authenticated active admins must receive 200 OK and live diagnostics payload."""
        admin_id = uuid.uuid4()
        token = create_access_token(str(admin_id))
        admin_user = User(
            id=admin_id,
            school21_login="senior_admin",
            is_admin=True,
            is_active=True,
            is_logged_in=True,
        )
        self.mock_db.get.return_value = admin_user

        mock_diag = {
            "status": "healthy",
            "uptime": "1h 30m 0s",
            "uptime_seconds": 5400,
            "memory_mb": 128.5,
            "database": {"connected": True, "latency_ms": 2.5, "error": None},
            "redis": {"connected": True, "latency_ms": 0.8, "error": None},
            "environment": {"port": "8000", "pid": 1234},
        }

        with patch("app.api.v1.diagnostics.get_system_diagnostics", new_callable=AsyncMock) as mock_get_diag:
            mock_get_diag.return_value = mock_diag
            headers = {"Authorization": f"Bearer {token}"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/diagnostics", headers=headers)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertTrue(data.get("database", {}).get("connected"))
        self.assertTrue(data.get("redis", {}).get("connected"))
        mock_get_diag.assert_awaited_once()

    async def test_logged_out_admin_rejected_with_401(self) -> None:
        """Admin users who have logged out (is_logged_in=False) must receive 401 Unauthorized."""
        admin_id = uuid.uuid4()
        token = create_access_token(str(admin_id))
        logged_out_admin = User(
            id=admin_id,
            school21_login="logged_out_admin",
            is_admin=True,
            is_active=True,
            is_logged_in=False,
        )
        self.mock_db.get.return_value = logged_out_admin

        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/diagnostics", headers=headers)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "User not found, inactive or logged out")

    async def test_inactive_admin_rejected_with_401(self) -> None:
        """Deactivated admin users (is_active=False) must receive 401 Unauthorized."""
        admin_id = uuid.uuid4()
        token = create_access_token(str(admin_id))
        inactive_admin = User(
            id=admin_id,
            school21_login="inactive_admin",
            is_admin=True,
            is_active=False,
            is_logged_in=True,
        )
        self.mock_db.get.return_value = inactive_admin

        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/diagnostics", headers=headers)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "User not found, inactive or logged out")

    async def test_health_endpoint_remains_public(self) -> None:
        """GET /health must remain publicly accessible without Authorization header."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    async def test_internal_get_system_diagnostics_callable_without_auth(self) -> None:
        """get_system_diagnostics() function must remain directly invokable by internal callers."""
        from unittest.mock import MagicMock

        with patch("app.api.v1.diagnostics.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.api.v1.diagnostics.redis_client") as mock_redis:
            mock_session = AsyncMock()
            mock_res = MagicMock()
            mock_res.scalar.return_value = 1
            mock_session.execute.return_value = mock_res
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            mock_redis.ping = AsyncMock(return_value=True)

            diag = await get_system_diagnostics()

        self.assertIsInstance(diag, dict)
        self.assertEqual(diag["status"], "healthy")
        self.assertTrue(diag["database"]["connected"])
        self.assertTrue(diag["redis"]["connected"])
        self.assertIn("memory_mb", diag)
        self.assertIn("uptime", diag)
