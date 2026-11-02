"""Runtime fail-fast configuration safety guard.

Enforces strict isolation for local staging environments and blocks any
accidental connection to production Render, PostgreSQL, Redis, Telegram,
or School 21 APIs.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Known production indicators / hosts that must NEVER be contacted in staging
PRODUCTION_DISALLOWED_PATTERNS = [
    r"p2p-o1ex\.onrender\.com",
    r"p2p-r5l6\.onrender\.com",
    r"dpg-[a-z0-9]+",  # Render managed PostgreSQL host prefix
    r"red-[a-z0-9]+",  # Render managed Redis host prefix
    r"\.oregon-postgres\.render\.com",
    r"\.frankfurt-postgres\.render\.com",
    r"\.render\.com",
    r"school21-p2p\.vercel\.app",
]

# Real Telegram bot token pattern: digits (8-10) : alphanumeric/underscore/hyphen (35)
REAL_BOT_TOKEN_PATTERN = re.compile(r"^\d{8,10}:[A-Za-z0-9_-]{35}$")


class SafetyViolationError(RuntimeError):
    """Raised when an unsafe configuration is detected in staging."""
    pass


def verify_staging_safety(settings_obj=None) -> None:
    """Validate runtime settings for local staging isolation.

    Raises SafetyViolationError if any rule is violated.
    """
    if settings_obj is None:
        from app.core.config import settings
        settings_obj = settings

    env = (getattr(settings_obj, "ENVIRONMENT", "") or os.getenv("ENVIRONMENT", "")).lower()
    is_local_staging = (
        bool(getattr(settings_obj, "LOCAL_STAGING", False))
        or os.getenv("LOCAL_STAGING", "0") in ("1", "true", "True")
        or env in ("local_staging", "staging")
    )

    # 1. Reject production environment flags
    if env == "production":
        raise SafetyViolationError("ENVIRONMENT is set to 'production' in local staging context.")

    if os.getenv("RENDER"):
        raise SafetyViolationError("RENDER environment variable is set; local staging cannot run inside Render.")

    # 2. Database URL safety
    db_url = getattr(settings_obj, "DATABASE_URL", "") or os.getenv("DATABASE_URL", "")
    if not db_url:
        raise SafetyViolationError("DATABASE_URL is not configured.")

    for pattern in PRODUCTION_DISALLOWED_PATTERNS:
        if re.search(pattern, db_url, re.IGNORECASE):
            raise SafetyViolationError(f"DATABASE_URL points to a production host matching '{pattern}'.")

    if is_local_staging:
        parsed_db = urlparse(db_url.replace("postgresql+asyncpg://", "http://"))
        db_host = parsed_db.hostname or ""
        allowed_db_hosts = {"postgres", "localhost", "127.0.0.1"}
        if db_host not in allowed_db_hosts:
            raise SafetyViolationError(
                f"Local staging DATABASE_URL host must be one of {allowed_db_hosts}, got '{db_host}'."
            )
        db_name = parsed_db.path.lstrip("/")
        if db_name in ("peer_learn_prod", "p2p_prod", "production"):
            raise SafetyViolationError(f"DATABASE_URL targets production database name '{db_name}'.")

    # 3. Redis and Celery URLs safety
    redis_urls = {
        "REDIS_URL": getattr(settings_obj, "REDIS_URL", "") or os.getenv("REDIS_URL", ""),
        "CELERY_BROKER_URL": getattr(settings_obj, "CELERY_BROKER_URL", "") or os.getenv("CELERY_BROKER_URL", ""),
        "CELERY_RESULT_BACKEND": getattr(settings_obj, "CELERY_RESULT_BACKEND", "") or os.getenv("CELERY_RESULT_BACKEND", ""),
    }

    for name, r_url in redis_urls.items():
        if not r_url:
            raise SafetyViolationError(f"{name} is not configured.")
        for pattern in PRODUCTION_DISALLOWED_PATTERNS:
            if re.search(pattern, r_url, re.IGNORECASE):
                raise SafetyViolationError(f"{name} points to a production host matching '{pattern}'.")
        if is_local_staging:
            parsed_r = urlparse(r_url)
            r_host = parsed_r.hostname or ""
            allowed_r_hosts = {"redis", "localhost", "127.0.0.1"}
            if r_host not in allowed_r_hosts:
                raise SafetyViolationError(
                    f"Local staging {name} host must be one of {allowed_r_hosts}, got '{r_host}'."
                )

    # 4. Telegram API base safety
    tg_base = getattr(settings_obj, "TELEGRAM_API_BASE", "") or os.getenv("TELEGRAM_API_BASE", "")
    if is_local_staging:
        if "api.telegram.org" in tg_base:
            raise SafetyViolationError(
                "Local staging must not use 'api.telegram.org'. It must point to local mock-telegram."
            )
        if not tg_base or ("mock-telegram" not in tg_base and "localhost" not in tg_base and "127.0.0.1" not in tg_base):
            raise SafetyViolationError(
                f"Local staging TELEGRAM_API_BASE must point to mock-telegram or localhost, got '{tg_base}'."
            )

    # 5. School 21 API base and Keycloak URL safety
    s21_base = getattr(settings_obj, "SCHOOL21_API_BASE", "") or os.getenv("SCHOOL21_API_BASE", "")
    keycloak_url = getattr(settings_obj, "KEYCLOAK_TOKEN_URL", "") or os.getenv("KEYCLOAK_TOKEN_URL", "")
    if is_local_staging:
        if "21-school.ru" in s21_base:
            raise SafetyViolationError(
                "Local staging must not contact real '21-school.ru' API. Must point to local mock-school21."
            )
        if "21-school.ru" in keycloak_url:
            raise SafetyViolationError(
                "Local staging must not contact real '21-school.ru' Keycloak. Must point to local mock-school21."
            )
        if not s21_base or ("mock-school21" not in s21_base and "localhost" not in s21_base and "127.0.0.1" not in s21_base):
            raise SafetyViolationError(
                f"Local staging SCHOOL21_API_BASE must point to mock-school21 or localhost, got '{s21_base}'."
            )

    # 6. Telegram Bot Token safety
    bot_token = getattr(settings_obj, "TELEGRAM_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if is_local_staging:
        if not bot_token:
            raise SafetyViolationError("TELEGRAM_BOT_TOKEN is missing for local staging bot.")
        if REAL_BOT_TOKEN_PATTERN.match(bot_token) and not bot_token.startswith("000000"):
            raise SafetyViolationError(
                "TELEGRAM_BOT_TOKEN matches a live Telegram production token format! Must use test fake token."
            )

    # 7. Disallow external notification tokens in local staging
    logger_token = getattr(settings_obj, "TELEGRAM_LOGGER_BOT_TOKEN", "") or os.getenv("TELEGRAM_LOGGER_BOT_TOKEN", "")
    logger_chat = getattr(settings_obj, "TELEGRAM_LOGGER_CHAT_ID", "") or os.getenv("TELEGRAM_LOGGER_CHAT_ID", "")
    if is_local_staging and (logger_token or logger_chat):
        raise SafetyViolationError(
            "TELEGRAM_LOGGER_BOT_TOKEN and TELEGRAM_LOGGER_CHAT_ID must be empty in local staging to prevent real alert spam."
        )

    # 8. Disallow real Vercel integration secrets in local staging
    vercel_token = getattr(settings_obj, "VERCEL_TOKEN", "") or os.getenv("VERCEL_TOKEN", "")
    vercel_webhook = getattr(settings_obj, "VERCEL_WEBHOOK_SECRET", "") or os.getenv("VERCEL_WEBHOOK_SECRET", "")
    vercel_drain = getattr(settings_obj, "VERCEL_LOG_DRAIN_SECRET", "") or os.getenv("VERCEL_LOG_DRAIN_SECRET", "")
    if is_local_staging and (vercel_token or vercel_webhook or vercel_drain):
        raise SafetyViolationError(
            "VERCEL_TOKEN, VERCEL_WEBHOOK_SECRET, and VERCEL_LOG_DRAIN_SECRET must be empty in local staging."
        )


def main() -> None:
    try:
        verify_staging_safety()
        print("PASS: Staging runtime safety guard verified. All isolation boundaries intact.")
    except SafetyViolationError as err:
        print(f"FATAL: Safety violation: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
