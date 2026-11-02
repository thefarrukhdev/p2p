"""Application settings loaded from environment / .env file."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent


def _resolve_env_files() -> tuple[str, ...] | None:
    # In production or on Render, do not load arbitrary local .env files
    if os.environ.get("RENDER") == "true" or os.environ.get("ENVIRONMENT") == "production":
        return None

    # Explicit ENV_FILE takes precedence
    custom_env = os.environ.get("ENV_FILE")
    if custom_env and Path(custom_env).is_file():
        return (custom_env,)

    # Only load verified local repository files: backend/.env or repo_root/.env
    candidates: list[str] = []
    backend_env = _BACKEND_DIR / ".env"
    if backend_env.is_file():
        candidates.append(str(backend_env))
    repo_env = _REPO_ROOT / ".env"
    if repo_env.is_file() and str(repo_env) not in candidates:
        candidates.append(str(repo_env))

    return tuple(candidates) if candidates else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    SECRET_KEY: str = "change-me"
    DEBUG: bool = False
    LOCAL_STAGING: bool = False
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "https://t.me,https://school21-p2p.vercel.app"

    # Database / Redis
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/p2p_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # School21
    SCHOOL21_API_BASE: str = (
        "https://platform.21-school.ru/services/21-school/api/v1"
    )
    KEYCLOAK_TOKEN_URL: str = (
        "https://auth.21-school.ru/auth/realms/EduPowerKeycloak/protocol/openid-connect/token"
    )
    FERNET_KEY: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = "p2p_corpus_bot"
    TELEGRAM_API_BASE: str = "https://api.telegram.org/bot"
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_REQUIRED_CHANNEL: str = ""
    ADMIN_IDS: str = ""  # Comma separated Telegram IDs
    ENFORCE_TELEGRAM_2FA: bool = False

    # Web Admin (SQLAdmin) Credentials — No default/fallback credentials
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""

    # Telegram DevOps Logger (GitHub/Vercel/Error Alerts)
    TELEGRAM_LOGGER_BOT_TOKEN: str = ""
    TELEGRAM_LOGGER_CHAT_ID: str = ""

    # Vercel Integration
    VERCEL_TOKEN: str = ""
    VERCEL_PROJECT_ID: str = "prj_gvSNNdflPJB5Vqydo4iR5McuoB30"

    # Webhook Secrets
    VERCEL_WEBHOOK_SECRET: str = ""
    VERCEL_LOG_DRAIN_SECRET: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
