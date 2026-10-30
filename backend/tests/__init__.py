"""Test package initialization with safe isolated mock environments.

CRITICAL ARCHITECTURE INVARIANT:
This module is strictly located at /home/Bekzod/Desktop/p2p/backend/tests/__init__.py.
It is exclusively executed by test runners (unittest, pytest).
Application entry points (app.main, bot.main, Celery, Alembic) do NOT import the tests package.
"""
import os

# Production runtime guard: Ensure test package is never loaded in production or Render cloud
if os.environ.get("RENDER") == "true" or os.environ.get("ENVIRONMENT") == "production":
    raise RuntimeError("SECURITY VIOLATION: Test package must never be imported in production runtime!")

# Set safe in-memory database defaults ONLY during test execution
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:mock-test-token-safe")
os.environ.setdefault("SECRET_KEY", "test-secret-key-safe-dummy-32bytes-min")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-safe-dummy-32bytes")
os.environ.setdefault("FERNET_KEY", "cw_2n_8lQcQ5Ea0P6dYpY_5C2M7U7xX7dD6gK1mN3v4=")
