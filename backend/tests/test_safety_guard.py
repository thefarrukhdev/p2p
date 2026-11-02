"""Unit tests for staging runtime safety guard."""
import unittest
from types import SimpleNamespace

from app.core.safety_guard import SafetyViolationError, verify_staging_safety


def get_valid_staging_settings() -> SimpleNamespace:
    return SimpleNamespace(
        ENVIRONMENT="local_staging",
        LOCAL_STAGING=True,
        DATABASE_URL="postgresql+asyncpg://p2p_user:pass@postgres:5432/p2p_local_staging_db",
        REDIS_URL="redis://redis:6379/0",
        CELERY_BROKER_URL="redis://redis:6379/1",
        CELERY_RESULT_BACKEND="redis://redis:6379/2",
        TELEGRAM_API_BASE="http://mock-telegram:8080/bot",
        SCHOOL21_API_BASE="http://mock-school21:8081/services/21-school/api/v1",
        KEYCLOAK_TOKEN_URL="http://mock-school21:8081/auth/realms/EduPowerKeycloak/protocol/openid-connect/token",
        TELEGRAM_BOT_TOKEN="local-staging-fake-bot-token",
        TELEGRAM_LOGGER_BOT_TOKEN="",
        TELEGRAM_LOGGER_CHAT_ID="",
        VERCEL_TOKEN="",
        VERCEL_WEBHOOK_SECRET="",
        VERCEL_LOG_DRAIN_SECRET="",
    )


class TestSafetyGuard(unittest.TestCase):
    def test_valid_staging_passes(self):
        settings = get_valid_staging_settings()
        # Must not raise
        verify_staging_safety(settings)

    def test_reject_production_environment(self):
        settings = get_valid_staging_settings()
        settings.ENVIRONMENT = "production"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("production", str(cm.exception))

    def test_reject_render_db_hostname(self):
        settings = get_valid_staging_settings()
        settings.DATABASE_URL = "postgresql+asyncpg://user:pass@dpg-c1234567890:5432/db"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("production host", str(cm.exception))

    def test_reject_external_db_host_in_staging(self):
        settings = get_valid_staging_settings()
        settings.DATABASE_URL = "postgresql+asyncpg://user:pass@external-db.aws.com:5432/db"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("host must be one of", str(cm.exception))

    def test_reject_external_redis_in_staging(self):
        settings = get_valid_staging_settings()
        settings.REDIS_URL = "redis://my-external-redis.com:6379/0"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("host must be one of", str(cm.exception))

    def test_reject_real_telegram_api_in_staging(self):
        settings = get_valid_staging_settings()
        settings.TELEGRAM_API_BASE = "https://api.telegram.org/bot"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("api.telegram.org", str(cm.exception))

    def test_reject_real_school21_api_in_staging(self):
        settings = get_valid_staging_settings()
        settings.SCHOOL21_API_BASE = "https://platform.21-school.ru/services/21-school/api/v1"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("21-school.ru", str(cm.exception))

    def test_reject_real_keycloak_in_staging(self):
        settings = get_valid_staging_settings()
        settings.KEYCLOAK_TOKEN_URL = "https://auth.21-school.ru/auth/realms/EduPowerKeycloak/protocol/openid-connect/token"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("21-school.ru", str(cm.exception))

    def test_reject_real_bot_token_format(self):
        settings = get_valid_staging_settings()
        settings.TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("live Telegram production token", str(cm.exception))

    def test_reject_telegram_logger_in_staging(self):
        settings = get_valid_staging_settings()
        settings.TELEGRAM_LOGGER_BOT_TOKEN = "some-token"
        settings.TELEGRAM_LOGGER_CHAT_ID = "-100123456"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("TELEGRAM_LOGGER_BOT_TOKEN", str(cm.exception))

    def test_reject_vercel_secrets_in_staging(self):
        settings = get_valid_staging_settings()
        settings.VERCEL_TOKEN = "real-vercel-token"
        with self.assertRaises(SafetyViolationError) as cm:
            verify_staging_safety(settings)
        self.assertIn("VERCEL_TOKEN", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
