"""In-memory SQLite async fixtures for safe isolated testing without external database."""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

# Ensure SQLite can render PostgreSQL JSONB
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# Set safe dummy environment variables before importing app
os.environ["SECRET_KEY"] = "test-secret-key-safe-dummy-32bytes-min"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-safe-dummy-32bytes"
os.environ["FERNET_KEY"] = "cw_2n_8lQcQ5Ea0P6dYpY_5C2M7U7xX7dD6gK1mN3v4="
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.db.base import Base
import app.db.models  # ensure models are registered
from app.db.models.user import User
from app.db.models.slot import Slot, SlotStatus


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
