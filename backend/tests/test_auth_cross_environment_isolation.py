"""Regression tests for cross-environment authentication isolation:
1. No login credentials or OTP requests are ever forwarded to Production.
2. Missing temp_tokens and missing OTP records fail closed.
3. 123456 synthetic OTP is strictly rejected in Production.
4. Single-use OTP tokens are destroyed immediately upon verification.
"""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.auth import login, verify_code, LoginRequest, VerifyCodeRequest
from app.core.config import settings
from app.db.models.user import User


class MemoryRedis:
    def __init__(self):
        self._data: dict[str, str] = {}

    async def get(self, key: str):
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, val: str):
        self._data[key] = val

    async def delete(self, key: str):
        self._data.pop(key, None)


def make_request(path: str = "/api/v1/auth/login", ip: str = "127.0.0.99") -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
        "client": (ip, 12345),
    })


class TestAuthCrossEnvironmentIsolation(unittest.IsolatedAsyncioTestCase):
    async def test_login_never_calls_production_render_backend(self):
        """POST /login must strictly remain local and never forward credentials to Render."""
        user = User(
            id=uuid.uuid4(),
            school21_login="charlie_local",
            is_active=True,
            is_logged_in=False,
            onboarding_done=False,
            telegram_id=None,
        )
        fake_redis = MemoryRedis()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_s21 = AsyncMock()
        mock_s21.login.return_value = {"access_token": "valid-token"}
        mock_s21.get_profile.return_value = {"campus": "Tashkent", "className": "Core"}
        mock_s21.get_projects.return_value = []
        mock_s21.get_coalition.return_value = {}
        mock_s21.get_location.return_value = {}

        req = make_request("/api/v1/auth/login", ip="127.0.0.101")
        payload = LoginRequest(login="charlie_local", password="secret_password_here")

        with patch("app.api.v1.auth.school21_client", mock_s21), \
             patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "TELEGRAM_BOT_USERNAME", "p2p_corpus_bot"), \
             patch.object(settings, "LOCAL_STAGING", False), \
             patch("httpx.AsyncClient") as mock_client_cls:

            resp = await login(request=req, payload=payload, db=mock_db)

            # Ensure httpx.AsyncClient was never used to POST to Render
            for call in mock_client_cls.mock_calls:
                call_str = str(call)
                self.assertNotIn("p2p-o1ex.onrender.com", call_str)

            self.assertEqual(resp.status, "need_telegram")
            self.assertIsNotNone(resp.temp_token)
            self.assertEqual(resp.bot_url, f"https://t.me/p2p_corpus_bot?start={resp.temp_token}")
            self.assertIsNone(resp.staging_otp)

    async def test_verify_code_never_calls_production_render_backend(self):
        """POST /verify-code must verify strictly in configured Redis, never calling Render."""
        fake_redis = MemoryRedis()
        req = make_request("/api/v1/auth/verify-code", ip="127.0.0.102")
        payload = VerifyCodeRequest(temp_token="unknown_token", code="654321")
        mock_db = AsyncMock()

        with patch("app.api.v1.auth.redis_client", fake_redis), \
             patch("httpx.AsyncClient") as mock_client_cls:

            # Missing temp_token must fail closed with 400 Bad Request
            with self.assertRaises(HTTPException) as cm:
                await verify_code(request=req, payload=payload, db=mock_db)

            self.assertEqual(cm.exception.status_code, 400)
            self.assertIn("yaroqsiz yoki muddati o'tgan", cm.exception.detail.lower())

            # Verify no HTTP calls were made to production
            self.assertEqual(mock_client_cls.call_count, 0)

    async def test_missing_otp_record_fails_closed(self):
        """If temp_token is found but OTP has expired or was not created, must fail closed."""
        user_id = uuid.uuid4()
        fake_redis = MemoryRedis()
        await fake_redis.setex("temp:valid_temp_tok", 300, str(user_id))

        req = make_request("/api/v1/auth/verify-code", ip="127.0.0.103")
        payload = VerifyCodeRequest(temp_token="valid_temp_tok", code="123456")
        mock_db = AsyncMock()

        with patch("app.api.v1.auth.redis_client", fake_redis):
            with self.assertRaises(HTTPException) as cm:
                await verify_code(request=req, payload=payload, db=mock_db)

            self.assertEqual(cm.exception.status_code, 400)
            self.assertIn("kod topilmadi", cm.exception.detail.lower())

    async def test_production_environment_rejects_123456_otp(self):
        """In production environment, code 123456 must be unconditionally rejected."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            school21_login="prod_user",
            is_active=True,
            is_logged_in=False,
            telegram_id=None,
        )
        fake_redis = MemoryRedis()
        await fake_redis.setex("temp:prod_temp_token", 300, str(user_id))
        # Even if 123456 was somehow present in Redis
        await fake_redis.setex(f"otp:{user_id}", 300, "123456:999888777")

        req = make_request("/api/v1/auth/verify-code", ip="127.0.0.104")
        payload = VerifyCodeRequest(temp_token="prod_temp_token", code="123456")

        mock_db = AsyncMock()
        mock_db.get.return_value = user

        with patch("app.api.v1.auth.redis_client", fake_redis), \
             patch.object(settings, "ENVIRONMENT", "production"):

            with self.assertRaises(HTTPException) as cm:
                await verify_code(request=req, payload=payload, db=mock_db)

            self.assertEqual(cm.exception.status_code, 400)
            self.assertIn("kod noto'g'ri", cm.exception.detail.lower())

    async def test_single_use_otp_deleted_upon_successful_verification(self):
        """After successful verify_code, both OTP and temp_token must be purged from Redis."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            school21_login="otp_user",
            is_active=True,
            is_logged_in=False,
            telegram_id=None,
            onboarding_done=False,
        )
        fake_redis = MemoryRedis()
        await fake_redis.setex("temp:tok_single_use", 300, str(user_id))
        await fake_redis.setex(f"otp:{user_id}", 300, "789123:555444333")

        req = make_request("/api/v1/auth/verify-code", ip="127.0.0.105")
        payload = VerifyCodeRequest(temp_token="tok_single_use", code="789123")

        mock_db = AsyncMock()
        mock_db.get.return_value = user
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        with patch("app.api.v1.auth.redis_client", fake_redis):
            resp = await verify_code(request=req, payload=payload, db=mock_db)

            self.assertIsNotNone(resp.access_token)
            # Both keys must be erased
            self.assertIsNone(await fake_redis.get("temp:tok_single_use"))
            self.assertIsNone(await fake_redis.get(f"otp:{user_id}"))
