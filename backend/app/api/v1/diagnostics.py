"""Live diagnostics and health metrics for Backend, PostgreSQL, and Redis."""
from __future__ import annotations

import os
import resource
import time
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import CurrentAdmin
from app.db.base import AsyncSessionLocal
from app.services.cache import redis_client

router = APIRouter(prefix="/diagnostics", tags=["System Diagnostics"])

APP_START_TIME = time.time()


async def get_system_diagnostics() -> dict[str, Any]:
    """Collect real-time health metrics of Backend, DB, and Redis."""
    uptime_sec = int(time.time() - APP_START_TIME)
    hours, rem = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    # Memory usage in MB
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # On Linux ru_maxrss is in KB
        memory_mb = round(usage.ru_maxrss / 1024, 1)
    except Exception:
        memory_mb = -1

    # Database check
    db_ok = False
    db_latency_ms = -1
    db_error = None
    try:
        t0 = time.perf_counter()
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT 1"))
            val = res.scalar()
            if val == 1:
                db_ok = True
                db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        db_error = str(exc)

    # Redis check
    redis_ok = False
    redis_latency_ms = -1
    redis_error = None
    try:
        t0 = time.perf_counter()
        pong = await redis_client.ping()
        if pong:
            redis_ok = True
            redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        redis_error = str(exc)

    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "uptime": uptime_str,
        "uptime_seconds": uptime_sec,
        "memory_mb": memory_mb,
        "database": {
            "connected": db_ok,
            "latency_ms": db_latency_ms,
            "error": db_error,
        },
        "redis": {
            "connected": redis_ok,
            "latency_ms": redis_latency_ms,
            "error": redis_error,
        },
        "environment": {
            "port": os.environ.get("PORT", "8000"),
            "pid": os.getpid(),
        },
    }


@router.get("")
async def get_diagnostics(_admin: CurrentAdmin) -> dict[str, Any]:
    return await get_system_diagnostics()
