"""Regression tests for HTTPX and Telegram token log redaction."""
from __future__ import annotations

import io
import logging
import unittest
import httpx

from app.core.logging import (
    TelegramTokenRedactionFilter,
    TelegramTokenRedactionFormatter,
    configure_secure_logging,
    redact_telegram_token,
)


class TestHttpxSecretRedaction(unittest.TestCase):
    """Verify that Telegram bot tokens are never leaked into HTTPX or application logs."""

    def setUp(self) -> None:
        self.fake_token = "123456789:ABCdefGHIjkl-SecretToken_9876543210"
        self.log_stream = io.StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)

        configure_secure_logging()

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(self.handler)
        self.handler.addFilter(TelegramTokenRedactionFilter())
        self.handler.setFormatter(TelegramTokenRedactionFormatter("%(levelname)s:%(name)s:%(message)s"))

    def tearDown(self) -> None:
        root = logging.getLogger()
        root.removeHandler(self.handler)

    def test_pure_function_redaction(self) -> None:
        """Verify redact_telegram_token replaces tokens across various URL shapes."""
        raw_urls = [
            f"https://api.telegram.org/bot{self.fake_token}/getMe",
            f"https://api.telegram.org/file/bot{self.fake_token}/doc.pdf",
            f"/bot{self.fake_token}/sendMessage?chat_id=123",
            f"Failed calling https://api.telegram.org/bot{self.fake_token}/setWebhook",
        ]
        for url in raw_urls:
            redacted = redact_telegram_token(url)
            self.assertNotIn(self.fake_token, redacted)
            self.assertIn("/bot[REDACTED]", redacted)

    def test_httpx_request_logging_redacts_token_while_retaining_status(self) -> None:
        """Verify httpx INFO log redacts the token but keeps status and method visible."""
        url = f"https://api.telegram.org/bot{self.fake_token}/getMe"

        # Dispatch an outgoing request via httpx
        with httpx.Client() as client:
            try:
                client.get(url, timeout=5.0)
            except Exception:
                pass

        log_output = self.log_stream.getvalue()

        # Token must NOT be present
        self.assertNotIn(self.fake_token, log_output)
        # Redacted URL structure must be present
        self.assertIn("https://api.telegram.org/bot[REDACTED]/getMe", log_output)
        # HTTP response info must remain visible (401 Unauthorized or Request error)
        self.assertTrue(
            "401" in log_output or "Unauthorized" in log_output or "HTTP Request" in log_output,
            f"Useful HTTP info missing in: {log_output}",
        )

    def test_application_error_logs_preserve_error_details(self) -> None:
        """Verify application warnings and errors preserve diagnostic details without token."""
        url = f"https://api.telegram.org/bot{self.fake_token}/sendMessage"
        test_logger = logging.getLogger("app.services.telegram_dispatcher")

        test_logger.warning("Permanent delivery failure: HTTP 403 Forbidden for chat 999 at %s", url)

        log_output = self.log_stream.getvalue()
        self.assertNotIn(self.fake_token, log_output)
        self.assertIn("Permanent delivery failure: HTTP 403 Forbidden for chat 999", log_output)
        self.assertIn("https://api.telegram.org/bot[REDACTED]/sendMessage", log_output)

    def test_traceback_exception_redaction(self) -> None:
        """Verify exception tracebacks containing Telegram URLs redact the token."""
        url = f"https://api.telegram.org/bot{self.fake_token}/getUpdates"
        test_logger = logging.getLogger("bot.main")

        try:
            raise httpx.ConnectError(f"Cannot reach {url}")
        except Exception:
            test_logger.error("Polling connection failed", exc_info=True)

        log_output = self.log_stream.getvalue()
        self.assertNotIn(self.fake_token, log_output)
        self.assertIn("Polling connection failed", log_output)
        self.assertIn("Cannot reach https://api.telegram.org/bot[REDACTED]/getUpdates", log_output)


if __name__ == "__main__":
    unittest.main()
