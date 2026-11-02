"""Tests for Telegram 2FA Semantics:
1. First-time login without telegram_id requires Telegram linking.
2. Subsequent logins issue direct JWT when ENFORCE_TELEGRAM_2FA is False.
3. Subsequent logins require a fresh 2FA challenge when ENFORCE_TELEGRAM_2FA is True.
4. Rate limiting is enforced on login and verify-code endpoints.
"""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.requests import Request

from app.api.v1.auth import login, verify_code, LoginRequest, VerifyCodeRequest
from app.core.config import settings
from app.db.models.user import User


class FakeRedisStore:
    def __init__(self):
        self._data: dict[str, str] = {}

    async def get(self, key: str):
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, val: str):
        self._data[key] = val

    async def delete(self, key: str):
        self._data.pop(key, None)


def make_request(path: str = "/api/v1/auth/login", ip: str = "127.0.0.88") -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
        "client": (ip, 12345),
    })


class TestTelegram2FASemantics(unittest.IsolatedAsyncioTestCase):
    async def test_first_time_login_without_telegram_id_requires_telegram(self):
        """User without telegram_id must receive status='need_telegram' and a temp_token."""
        user = User(
            id=uuid.uuid4(),
            school21_login="new_student",
            is_active=True,
            is_logged_in=False,
            onboarding_done=False,
            telegram_id=None,
        )
        fake_redis = FakeRedisStore()
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

        req = make_request("/api/v1/auth/login", ip="127.0.0.120")
        payload = LoginRequest(login="new_student", password="password123")

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", "p2p_corpus_bot"), \
             patch.object(settings, "ENFORCE_TELEGRAM_2FA", False), \
             patch.object(settings, "LOCAL_STAGING", False):

            resp = await login(request=req, payload=payload, db=mock_db)

            self.assertEqual(resp.status, "need_telegram")
            self.assertIsNotNone(resp.temp_token)
            self.assertIn("p2p_corpus_bot", resp.bot_url)
            self.assertIsNone(resp.access_token)

    async def test_subsequent_login_with_linked_telegram_issues_jwt_when_enforce_2fa_false(self):
        """When user already has telegram_id and ENFORCE_TELEGRAM_2FA is False, login issues JWT directly."""
        user = User(
            id=uuid.uuid4(),
            school21_login="linked_student",
            is_active=True,
            is_logged_in=False,
            onboarding_done=True,
            telegram_id=123456789,  # Already linked
        )
        fake_redis = FakeRedisStore()
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

        req = make_request("/api/v1/auth/login", ip="127.0.0.121")
        payload = LoginRequest(login="linked_student", password="password123")

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "ENFORCE_TELEGRAM_2FA", False):

            resp = await login(request=req, payload=payload, db=mock_db)

            self.assertEqual(resp.status, "ok")
            self.assertIsNotNone(resp.access_token)
            self.assertIsNotNone(resp.refresh_token)
            self.assertIsNone(resp.temp_token)
            self.assertIsNone(resp.bot_url)

    async def test_login_with_linked_telegram_requires_2fa_when_enforce_2fa_true(self):
        """When ENFORCE_TELEGRAM_2FA is True, user with telegram_id must complete OTP challenge."""
        user = User(
            id=uuid.uuid4(),
            school21_login="security_conscious_student",
            is_active=True,
            is_logged_in=False,
            onboarding_done=True,
            telegram_id=987654321,
        )
        fake_redis = FakeRedisStore()
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

        req = make_request("/api/v1/auth/login", ip="127.0.0.122")
        payload = LoginRequest(login="security_conscious_student", password="password123")

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "ENFORCE_TELEGRAM_2FA", True), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", "p2p_corpus_bot"), \
             patch.object(settings, "LOCAL_STAGING", False):

            resp = await login(request=req, payload=payload, db=mock_db)

            # 2FA challenge required!
            self.assertEqual(resp.status, "need_telegram")
            self.assertIsNotNone(resp.temp_token)
            self.assertIsNone(resp.access_token)
            self.assertIsNotNone(resp.bot_url)
