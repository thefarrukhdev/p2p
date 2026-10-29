"""Application settings loaded from environment / .env file."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    SECRET_KEY: str = "change-me"
    DEBUG: bool = False
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
    FERNET_KEY: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_REQUIRED_CHANNEL: str = ""
    ADMIN_IDS: str = ""  # Comma separated Telegram IDs

    # Telegram DevOps Logger (GitHub/Vercel/Error Alerts)
    TELEGRAM_LOGGER_BOT_TOKEN: str = ""
    TELEGRAM_LOGGER_CHAT_ID: str = ""

    # Vercel Integration
    VERCEL_TOKEN: str = ""
    VERCEL_PROJECT_ID: str = "prj_gvSNNdflPJB5Vqydo4iR5McuoB30"

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
