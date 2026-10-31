"""Comprehensive security and regression tests for Webhooks endpoints and signature verification."""
from __future__ import annotations

import hashlib
import hmac
import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.v1.webhooks import (
    _client_log_cache,
    handle_telegram_command,
    redact_sensitive_data,
    verify_vercel_signature,
)
from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.db.models.user import User
from app.main import app


class TestVerifyVercelSignatureHelper(unittest.TestCase):
    """Test constant-time HMAC-SHA1 signature verification helper function."""

    def test_verify_empty_inputs(self) -> None:
        self.assertFalse(verify_vercel_signature(b"{}", None, "secret"))
        self.assertFalse(verify_vercel_signature(b"{}", "", "secret"))
        self.assertFalse(verify_vercel_signature(b"{}", "sig", ""))

    def test_verify_valid_signature_raw_hex(self) -> None:
        secret = "super_secret_vercel_key"
        body = b'{"type": "deployment.created"}'
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        self.assertTrue(verify_vercel_signature(body, expected, secret))

    def test_verify_valid_signature_with_sha1_prefix(self) -> None:
        secret = "super_secret_vercel_key"
        body = b'{"type": "deployment.succeeded"}'
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        self.assertTrue(verify_vercel_signature(body, f"sha1={digest}", secret))

    def test_verify_tampered_body(self) -> None:
        secret = "super_secret_vercel_key"
        body = b'{"type": "deployment.created"}'
        sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        self.assertFalse(verify_vercel_signature(b'{"type": "deployment.hacked"}', sig, secret))

    def test_verify_wrong_secret(self) -> None:
        body = b'{"test": 1}'
        sig = hmac.new(b"secret1", body, hashlib.sha1).hexdigest()
        self.assertFalse(verify_vercel_signature(body, sig, "secret2"))


class TestRedactionHelper(unittest.TestCase):
    """Test recursive sanitization and credential/token redaction."""

    def test_redact_url_query_params(self) -> None:
        raw = "https://example.com/api?token=sec123&user=john&code=9988&key=mykey"
        redacted = redact_sensitive_data(raw)
        self.assertIn("token=[REDACTED]", redacted)
        self.assertIn("code=[REDACTED]", redacted)
        self.assertIn("key=[REDACTED]", redacted)
        self.assertIn("user=john", redacted)
        self.assertNotIn("sec123", redacted)

    def test_redact_bearer_token(self) -> None:
        raw = "Error occurred with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI.xyz"
        redacted = redact_sensitive_data(raw)
        self.assertIn("Bearer [REDACTED]", redacted)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI", redacted)

    def test_redact_nested_dict_keys(self) -> None:
        data = {
            "normal": "hello",
            "password": "secret_password_value",
            "nested": {
                "authToken": "raw_token_xyz",
                "safe": "visible",
            },
        }
        res = redact_sensitive_data(data)
        self.assertEqual(res["password"], "[REDACTED]")
        self.assertEqual(res["nested"]["authToken"], "[REDACTED]")
        self.assertEqual(res["nested"]["safe"], "visible")
        self.assertEqual(res["normal"], "hello")


class TestVercelWebhookSecurity(unittest.IsolatedAsyncioTestCase):
    """Test signature enforcement and security on POST /api/v1/webhooks/vercel."""

    def setUp(self) -> None:
        self.orig_secret = settings.VERCEL_WEBHOOK_SECRET

    def tearDown(self) -> None:
        settings.VERCEL_WEBHOOK_SECRET = self.orig_secret

    async def test_fails_closed_when_secret_not_configured(self) -> None:
        """When VERCEL_WEBHOOK_SECRET is empty, all webhook requests must be rejected with 401."""
        settings.VERCEL_WEBHOOK_SECRET = ""
        payload = {"type": "deployment.created"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel", json=payload)

        self.assertEqual(resp.status_code, 401)
        self.assertIn("not configured", resp.json().get("detail", ""))

    async def test_rejected_when_signature_header_missing(self) -> None:
        """Requests without x-vercel-signature header must return 401 Unauthorized."""
        settings.VERCEL_WEBHOOK_SECRET = "sec_test_vercel_123"
        payload = {"type": "deployment.created"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel", json=payload)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "Invalid webhook signature")

    async def test_rejected_when_signature_is_invalid(self) -> None:
        """Requests with forged or incorrect signature must return 401 Unauthorized."""
        settings.VERCEL_WEBHOOK_SECRET = "sec_test_vercel_123"
        body = b'{"type": "deployment.created"}'
        headers = {
            "x-vercel-signature": "0123456789abcdef0123456789abcdef01234567",
            "Content-Type": "application/json",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel", content=body, headers=headers)

        self.assertEqual(resp.status_code, 401)

    async def test_accepted_when_signature_is_valid(self) -> None:
        """Valid HMAC-SHA1 signature must be accepted with 200 OK and background task dispatched."""
        settings.VERCEL_WEBHOOK_SECRET = "sec_test_vercel_123"
        body = json.dumps({"type": "deployment.created", "payload": {"name": "p2p-fe"}}).encode("utf-8")
        sig = hmac.new(b"sec_test_vercel_123", body, hashlib.sha1).hexdigest()
        headers = {"x-vercel-signature": sig, "Content-Type": "application/json"}

        with patch("app.api.v1.webhooks.process_vercel_webhook", new_callable=AsyncMock) as mock_task:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/vercel", content=body, headers=headers)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "accepted"})
            mock_task.assert_called_once_with({"type": "deployment.created", "payload": {"name": "p2p-fe"}})

    async def test_invalid_json_body_with_valid_signature_rejected(self) -> None:
        """Valid signature over invalid JSON body must return 400 Bad Request."""
        settings.VERCEL_WEBHOOK_SECRET = "sec_test_vercel_123"
        body = b"not-a-valid-json{"
        sig = hmac.new(b"sec_test_vercel_123", body, hashlib.sha1).hexdigest()
        headers = {"x-vercel-signature": sig, "Content-Type": "application/json"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel", content=body, headers=headers)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("detail"), "Invalid JSON payload")


class TestVercelLogDrainSecurity(unittest.IsolatedAsyncioTestCase):
    """Test signature enforcement and security on POST /api/v1/webhooks/vercel-log-drain."""

    def setUp(self) -> None:
        self.orig_drain_secret = settings.VERCEL_LOG_DRAIN_SECRET
        self.orig_webhook_secret = settings.VERCEL_WEBHOOK_SECRET

    def tearDown(self) -> None:
        settings.VERCEL_LOG_DRAIN_SECRET = self.orig_drain_secret
        settings.VERCEL_WEBHOOK_SECRET = self.orig_webhook_secret

    async def test_fails_closed_when_no_drain_secret_configured(self) -> None:
        """Log drain endpoint must return 401 if VERCEL_LOG_DRAIN_SECRET is not set."""
        settings.VERCEL_LOG_DRAIN_SECRET = ""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel-log-drain", content=b"{}")

        self.assertEqual(resp.status_code, 401)
        self.assertIn("not configured", resp.json().get("detail", ""))

    async def test_no_silent_fallback_to_webhook_secret(self) -> None:
        """Log drain MUST NOT fall back to VERCEL_WEBHOOK_SECRET when drain secret is unset."""
        settings.VERCEL_LOG_DRAIN_SECRET = ""
        settings.VERCEL_WEBHOOK_SECRET = "webhook_secret_xyz"

        body = b'{"type": "error"}'
        sig = hmac.new(b"webhook_secret_xyz", body, hashlib.sha1).hexdigest()
        headers = {"x-vercel-signature": sig}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel-log-drain", content=body, headers=headers)

        self.assertEqual(resp.status_code, 401)
        self.assertIn("Vercel log drain secret not configured", resp.json().get("detail", ""))

    async def test_rejects_missing_signature(self) -> None:
        settings.VERCEL_LOG_DRAIN_SECRET = "drain_sec_999"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/vercel-log-drain", content=b"{}")

        self.assertEqual(resp.status_code, 401)

    async def test_accepts_valid_signature_and_dispatches_error_logs(self) -> None:
        """Valid drain payload with HTTP 500 error entry must trigger Telegram log alert."""
        settings.VERCEL_LOG_DRAIN_SECRET = "drain_sec_999"
        log_entry = {
            "statusCode": 500,
            "type": "stderr",
            "message": "Crash in handler: <script>alert(1)</script>",
            "path": "/api/broken",
            "clientIp": "192.168.1.50",
        }
        body = json.dumps(log_entry).encode("utf-8")
        sig = hmac.new(b"drain_sec_999", body, hashlib.sha1).hexdigest()
        headers = {"x-vercel-signature": sig, "Content-Type": "application/x-ndjson"}

        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/vercel-log-drain", content=body, headers=headers)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "processed", "count": "1"})
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][0]
            # Ensure HTML entities escaped
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", call_text)
            self.assertNotIn("<script>", call_text)

    async def test_ignores_non_error_log_entries(self) -> None:
        """200 OK log entries without errors must not trigger Telegram notifications."""
        settings.VERCEL_LOG_DRAIN_SECRET = "drain_sec_999"
        log_entry = {
            "statusCode": 200,
            "type": "stdout",
            "message": "Page loaded successfully",
            "path": "/index.html",
        }
        body = json.dumps(log_entry).encode("utf-8")
        sig = hmac.new(b"drain_sec_999", body, hashlib.sha1).hexdigest()
        headers = {"x-vercel-signature": sig}

        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/vercel-log-drain", content=body, headers=headers)

            self.assertEqual(resp.status_code, 200)
            mock_send.assert_not_called()


class TestTelegramBotWebhookSecurity(unittest.IsolatedAsyncioTestCase):
    """Test security and disabled-by-default behavior on POST /api/v1/webhooks/telegram-bot."""

    def setUp(self) -> None:
        self.orig_secret = settings.TELEGRAM_WEBHOOK_SECRET

    def tearDown(self) -> None:
        settings.TELEGRAM_WEBHOOK_SECRET = self.orig_secret

    async def test_disabled_by_default_when_secret_unset(self) -> None:
        """When TELEGRAM_WEBHOOK_SECRET is empty, return 404 and run no background tasks."""
        settings.TELEGRAM_WEBHOOK_SECRET = ""
        body = {"message": {"text": "/status"}}
        with patch("app.api.v1.webhooks.handle_telegram_command", new_callable=AsyncMock) as mock_cmd:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/telegram-bot", json=body)

            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.json().get("detail"), "Telegram bot webhook is disabled")
            mock_cmd.assert_not_called()

    async def test_rejects_missing_secret_token_header(self) -> None:
        settings.TELEGRAM_WEBHOOK_SECRET = "tg_webhook_secret_tok_123"
        body = {"message": {"text": "/status"}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/telegram-bot", json=body)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "Invalid Telegram secret token")

    async def test_rejects_wrong_secret_token_header(self) -> None:
        settings.TELEGRAM_WEBHOOK_SECRET = "tg_webhook_secret_tok_123"
        body = {"message": {"text": "/status"}}
        headers = {"x-telegram-bot-api-secret-token": "wrong_secret_token"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/telegram-bot", json=body, headers=headers)

        self.assertEqual(resp.status_code, 401)

    async def test_accepts_valid_secret_and_dispatches_command(self) -> None:
        settings.TELEGRAM_WEBHOOK_SECRET = "tg_webhook_secret_tok_123"
        body = {"message": {"text": "/status@p2p_bot"}}
        headers = {"x-telegram-bot-api-secret-token": "tg_webhook_secret_tok_123"}

        with patch("app.api.v1.webhooks.handle_telegram_command", new_callable=AsyncMock) as mock_cmd:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/telegram-bot", json=body, headers=headers)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "ok"})
            mock_cmd.assert_called_once_with("/status")


class TestClientLogSecurity(unittest.IsolatedAsyncioTestCase):
    """Test anonymous abuse prevention, auth enforcement, body limits, and redaction on POST /api/v1/webhooks/log."""

    def setUp(self) -> None:
        _client_log_cache.clear()
        self.mock_db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_anonymous_request_recorded_internally_and_never_triggers_telegram(self) -> None:
        """Anonymous client telemetry must be recorded internally and NEVER sent to Telegram."""
        payload = {
            "level": "ERROR",
            "source": "frontend",
            "message": "Crash on login page: network timeout",
            "details": {"url": "https://school21-p2p.vercel.app/login"},
        }

        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/log", json=payload)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "recorded_internally"})
            # MUST NEVER FORWARD TO TELEGRAM
            mock_send.assert_not_called()

    async def test_authenticated_user_request_triggers_telegram_with_attribution(self) -> None:
        """Authenticated client telemetry triggers Telegram alert with verified user attribution."""
        user_id = uuid.uuid4()
        token = create_access_token(str(user_id))
        user = User(
            id=user_id,
            school21_login="peer_reporter",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )
        self.mock_db.get.return_value = user

        payload = {
            "level": "ERROR",
            "source": "frontend",
            "message": "Component crashed inside SlotDetailPage",
            "details": {"slotId": "slot-123"},
        }
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/log", json=payload, headers=headers)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "queued"})
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][0]
            self.assertIn("peer_reporter", call_text)
            self.assertIn("Component crashed inside SlotDetailPage", call_text)

    async def test_redacts_sensitive_tokens_and_credentials_before_forwarding(self) -> None:
        """Sensitive URL query parameters and credentials must be redacted from alert text."""
        user_id = uuid.uuid4()
        token = create_access_token(str(user_id))
        user = User(
            id=user_id,
            school21_login="peer_reporter",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )
        self.mock_db.get.return_value = user

        payload = {
            "level": "ERROR",
            "source": "frontend",
            "message": "Request failed with Authorization: Bearer secret_jwt_token_12345 to /auth?token=raw_tok_99",
            "details": {
                "url": "https://example.com/api?token=sensitive_token_abc&code=auth_code_xyz",
                "password": "plain_user_password",
                "safeParam": "ok_value",
            },
        }
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/log", json=payload, headers=headers)

            self.assertEqual(resp.status_code, 200)
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][0]
            self.assertNotIn("secret_jwt_token_12345", call_text)
            self.assertNotIn("raw_tok_99", call_text)
            self.assertNotIn("sensitive_token_abc", call_text)
            self.assertNotIn("plain_user_password", call_text)
            self.assertIn("Bearer [REDACTED]", call_text)
            self.assertIn("token=[REDACTED]", call_text)
            self.assertIn("[REDACTED]", call_text)

    async def test_throttles_authenticated_duplicate_messages(self) -> None:
        user_id = uuid.uuid4()
        token = create_access_token(str(user_id))
        user = User(
            id=user_id,
            school21_login="peer_reporter",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )
        self.mock_db.get.return_value = user

        payload = {
            "level": "ERROR",
            "source": "frontend",
            "message": "Repeated connection error",
        }
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r1 = await client.post("/api/v1/webhooks/log", json=payload, headers=headers)
                r2 = await client.post("/api/v1/webhooks/log", json=payload, headers=headers)

            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r1.json(), {"status": "queued"})
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r2.json(), {"status": "throttled"})
            self.assertEqual(mock_send.call_count, 1)

    async def test_rejects_untrusted_origin_header(self) -> None:
        payload = {"level": "ERROR", "message": "Test msg"}
        headers = {"Origin": "https://malicious-attacker-site.com"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/log", json=payload, headers=headers)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("detail"), "Untrusted origin")

    async def test_allows_missing_origin_header(self) -> None:
        """Requests without Origin header (e.g. backend/mobile) are allowed and processed according to auth."""
        payload = {"level": "ERROR", "message": "Test msg"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/log", json=payload)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "recorded_internally"})

    async def test_rejects_raw_body_exceeding_10kb(self) -> None:
        oversized_body = b"{" + b'"a": "' + (b"X" * 11_000) + b'"}'
        headers = {"Content-Type": "application/json"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/log", content=oversized_body, headers=headers)

        self.assertEqual(resp.status_code, 413)
        self.assertIn("too large", resp.json().get("detail", ""))

    async def test_rejects_oversized_details_dictionary(self) -> None:
        payload = {
            "level": "ERROR",
            "message": "Valid error message",
            "details": {"heavyKey": "Y" * 2500},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/log", json=payload)

        self.assertEqual(resp.status_code, 422)
        self.assertIn("exceeds maximum allowed size", resp.json().get("detail", ""))

    async def test_validates_message_max_length(self) -> None:
        payload = {"level": "ERROR", "message": "A" * 1001}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/log", json=payload)

        self.assertEqual(resp.status_code, 422)


class TestTestLoggerSecurity(unittest.IsolatedAsyncioTestCase):
    """Test RBAC protection on POST /api/v1/webhooks/test."""

    def setUp(self) -> None:
        self.mock_db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_anonymous_user_rejected_with_401(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/test")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("detail"), "Not authenticated")

    async def test_regular_user_rejected_with_403(self) -> None:
        user_id = uuid.uuid4()
        token = create_access_token(str(user_id))
        regular_user = User(
            id=user_id,
            school21_login="regular_user",
            is_admin=False,
            is_active=True,
            is_logged_in=True,
        )
        self.mock_db.get.return_value = regular_user

        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/webhooks/test", headers=headers)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("detail"), "Admin access required")

    async def test_admin_user_allowed_with_200(self) -> None:
        admin_id = uuid.uuid4()
        token = create_access_token(str(admin_id))
        admin_user = User(
            id=admin_id,
            school21_login="admin_user",
            is_admin=True,
            is_active=True,
            is_logged_in=True,
        )
        self.mock_db.get.return_value = admin_user

        headers = {"Authorization": f"Bearer {token}"}
        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/webhooks/test", headers=headers)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"status": "test_dispatched"})
            mock_send.assert_called_once()


class TestTelegramCommandHandler(unittest.IsolatedAsyncioTestCase):
    """Test execution and error redaction of Telegram interactive commands."""

    async def test_handle_ping_command(self) -> None:
        with patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send:
            await handle_telegram_command("/ping")
            mock_send.assert_called_once()
            self.assertIn("Pong!", mock_send.call_args[0][0])

    async def test_handle_logs_command_handles_exceptions_without_credential_leak(self) -> None:
        """Errors in /logs must log generic message and never expose credentials or stack trace."""
        with (
            patch("app.core.config.settings.VERCEL_TOKEN", "sensitive_vercel_token_xyz"),
            patch("httpx.AsyncClient.get", side_effect=RuntimeError("Connection failed to vercel with sensitive_token")),
            patch("app.api.v1.webhooks.send_telegram_log", new_callable=AsyncMock) as mock_send,
        ):
            await handle_telegram_command("/logs")
            mock_send.assert_called_once()
            sent_text = mock_send.call_args[0][0]
            self.assertIn("Loglarni olishda xatolik yuz berdi.", sent_text)
            self.assertNotIn("sensitive_vercel_token_xyz", sent_text)
            self.assertNotIn("Connection failed to vercel", sent_text)
