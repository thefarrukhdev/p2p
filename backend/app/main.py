"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.cache import close_redis
from app.services.school21_client import school21_client
from app.services.telegram_logger import log_server_exception, send_telegram_log
from app.ws.slot_ws import router as ws_router

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await school21_client.start()
    from app.ws.manager import manager
    await manager.start()
    try:
        await send_telegram_log(
            "✅ <b>[Backend Server Ishga Tushdi] (Render Cloud)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Platforma: Render\n"
            "Versiya: 3.0.0\n"
            "FastAPI va WebSocket tayyor."
        )
    except Exception:
        pass

    yield

    try:
        await send_telegram_log(
            "❌ <b>[Backend Server To'xtatildi / Qayta Yuklanmoqda]</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Render serveri to'xtatildi yoki qayta ishga tushirilmoqda."
        )
    except Exception:
        pass
    await manager.stop()
    await school21_client.stop()
    await close_redis()


class ApiDetailedLoggerMiddleware(BaseHTTPMiddleware):
    """Log 4xx/5xx API errors and slow requests (>3s) to Telegram."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 1)

        path = request.url.path
        # Exclude internal/noise endpoints
        if not path.startswith(("/health", "/docs", "/openapi", "/api/v1/webhooks", "/ws")):
            client_ip = request.client.host if request.client else "unknown"

            # 4xx or 5xx error alert
            if response.status_code >= 400:
                text = (
                    f"❌ <b>[Backend API Xatosi] HTTP {response.status_code}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Endpoint: <code>{request.method} {path}</code>\n"
                    f"Client IP: <code>{client_ip}</code>\n"
                    f"Davomiyligi: <code>{duration_ms}ms</code>\n"
                    f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
                )
                asyncio.create_task(send_telegram_log(text))

            # Slow request alert (>3000ms)
            elif duration_ms > 3000:
                text = (
                    f"❌ <b>[Backend Sekin So'rov] {duration_ms}ms</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Endpoint: <code>{request.method} {path}</code>\n"
                    f"Status: <code>{response.status_code}</code>\n"
                    f"Client IP: <code>{client_ip}</code>\n"
                    f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
                )
                asyncio.create_task(send_telegram_log(text))

        return response


app = FastAPI(
    title="P2P Platform",
    version="3.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# API monitoring middleware
app.add_middleware(ApiDetailedLoggerMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    tb = traceback.format_exc()
    client_ip = request.client.host if request.client else "unknown"
    try:
        await log_server_exception(
            method=request.method,
            path=request.url.path,
            status_code=500,
            error_type=type(exc).__name__,
            error_msg=str(exc),
            traceback_str=tb,
            client_ip=client_ip,
        )
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Session middleware (SQLAdmin auth uchun kerak)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS — faqat whitelist domenlar
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)
app.include_router(ws_router)

# SQLAdmin panel (auth bilan himoyalangan)
try:
    from admin.setup import init_admin
    init_admin(app)
except Exception:
    pass


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
