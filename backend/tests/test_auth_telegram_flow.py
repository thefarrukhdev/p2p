"""Unit and integration tests for Telegram 2FA bot_url resolution and local staging OTP."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
from starlette.requests import Request

from app.api.v1.auth import login, verify_code, LoginRequest, VerifyCodeRequest
from app.core.config import settings
from app.db.models.user import User


class FakeRedis:
    def __init__(self):
        self._data = {}

    async def get(self, key: str):
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, val: str):
        self._data[key] = val

    async def delete(self, key: str):
        self._data.pop(key, None)


def make_request() -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    })


class TestAuthTelegramFlow(unittest.IsolatedAsyncioTestCase):
    async def test_configured_bot_username_generates_bot_url(self):
        """When TELEGRAM_BOT_USERNAME is configured, login returns valid t.me bot_url."""
        user = User(
            id=uuid.uuid4(),
            school21_login="tester_unlinked_1",
            is_active=True,
            is_logged_in=False,
            onboarding_done=False,
            telegram_id=None,
        )
        fake_redis = FakeRedis()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "s21-token"}
        mock_s21.get_profile.return_value = {"campus": "Tashkent", "className": "Core"}
        mock_s21.get_projects.return_value = []
        mock_s21.get_coalition.return_value = {}
        mock_s21.get_location.return_value = {}

        req = make_request()

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", "school21_p2p_bot"), \
             patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_bot_token"), \
             patch.object(settings, "LOCAL_STAGING", False):

            payload = LoginRequest(login="tester_unlinked_1", password="password123")
            resp = await login(request=req, payload=payload, db=mock_db)

            self.assertEqual(resp.status, "need_telegram")
            self.assertIsNotNone(resp.bot_url)
            self.assertTrue(resp.bot_url.startswith("https://t.me/school21_p2p_bot?start="))

    async def test_dynamic_get_me_resolution_via_telegram_api_base(self):
        """When bot username is not preconfigured, it queries getMe via TELEGRAM_API_BASE."""
        user = User(
            id=uuid.uuid4(),
            school21_login="tester_unlinked_2",
            is_active=True,
            is_logged_in=False,
            onboarding_done=False,
            telegram_id=None,
        )
        fake_redis = FakeRedis()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "s21-token"}
        mock_s21.get_profile.return_value = {"campus": "Tashkent"}
        mock_s21.get_projects.return_value = []
        mock_s21.get_coalition.return_value = {}
        mock_s21.get_location.return_value = {}

        req = make_request()

        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def get(self, url):
                m = MagicMock()
                m.json.return_value = {"ok": True, "result": {"username": "mocked_dynamic_bot"}}
                return m

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(httpx, "AsyncClient", MockAsyncClient), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", ""), \
             patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_token"), \
             patch.object(settings, "TELEGRAM_API_BASE", "http://mock-telegram:8080/bot"), \
             patch.object(settings, "LOCAL_STAGING", False):

            payload = LoginRequest(login="tester_unlinked_2", password="password123")
            resp = await login(request=req, payload=payload, db=mock_db)

            self.assertIsNone(resp.staging_otp)

    async def test_get_me_null_result_graceful_handling(self):
        """When getMe returns an error or null result payload, auth does not crash with AttributeError."""
        user = User(
            id=uuid.uuid4(),
            school21_login="tester_unlinked_null_result",
            is_active=True,
            is_logged_in=False,
            onboarding_done=False,
            telegram_id=None,
        )
        fake_redis = FakeRedis()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "s21-token"}
        mock_s21.get_profile.return_value = {"campus": "Tashkent"}
        mock_s21.get_projects.return_value = []
        mock_s21.get_coalition.return_value = {}
        mock_s21.get_location.return_value = {}

        req = make_request()

        class MockAsyncClientNullResult:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def get(self, url):
                m = MagicMock()
                m.status_code = 401
                m.json.return_value = {"ok": False, "result": None}
                return m

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(httpx, "AsyncClient", MockAsyncClientNullResult), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", ""), \
             patch.object(settings, "TELEGRAM_BOT_TOKEN", "invalid_token"), \
             patch.object(settings, "TELEGRAM_API_BASE", "http://mock-telegram:8080/bot"), \
             patch.object(settings, "LOCAL_STAGING", False):

            payload = LoginRequest(login="tester_unlinked_null_result", password="password123")
            resp = await login(request=req, payload=payload, db=mock_db)

            self.assertEqual(resp.status, "need_telegram")
            self.assertIsNone(resp.bot_url)
            self.assertIsNone(resp.staging_otp)

    async def test_local_staging_preseeds_otp_and_verifies_code(self):
        """In LOCAL_STAGING mode, OTP 123456 is pre-seeded in Redis and verify_code succeeds."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            school21_login="tester_staging_user",
            is_active=True,
            is_logged_in=False,
            onboarding_done=False,
            telegram_id=None,
        )
        fake_redis = FakeRedis()

        # In login: returns user. In verify_code (check existing telegram_id): returns None.
        mock_result_login = MagicMock()
        mock_result_login.scalar_one_or_none.return_value = user

        mock_result_verify = MagicMock()
        mock_result_verify.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [mock_result_login, mock_result_verify]
        mock_db.get.return_value = user

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "s21-token"}
        mock_s21.get_profile.return_value = {"campus": "Tashkent"}
        mock_s21.get_projects.return_value = []
        mock_s21.get_coalition.return_value = {}
        mock_s21.get_location.return_value = {}

        req = make_request()

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", ""), \
             patch.object(settings, "TELEGRAM_BOT_TOKEN", ""), \
             patch.object(settings, "LOCAL_STAGING", True):

            payload = LoginRequest(login="tester_staging_user", password="password123")
            resp = await login(request=req, payload=payload, db=mock_db)

            self.assertEqual(resp.status, "need_telegram")
            self.assertIsNotNone(resp.bot_url)
            self.assertTrue(resp.bot_url.startswith("https://t.me/p2p_staging_bot?start="))
            self.assertEqual(resp.staging_otp, "123456")

            # Check pre-seeded OTP in Redis
            otp_data = await fake_redis.get(f"otp:{user_id}")
            self.assertIsNotNone(otp_data)
            self.assertTrue(otp_data.startswith("123456:"))

            # Test verify_code with 123456
            verify_payload = VerifyCodeRequest(temp_token=resp.temp_token, code="123456")
            token_resp = await verify_code(request=req, payload=verify_payload, db=mock_db)

            self.assertIsNotNone(token_resp.access_token)
            self.assertTrue(user.is_logged_in)
            self.assertIsNotNone(user.telegram_id)


if __name__ == "__main__":
    unittest.main()

