"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.cache import close_redis
from app.services.school21_client import school21_client
from app.ws.slot_ws import router as ws_router

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await school21_client.start()
    from app.ws.manager import manager
    await manager.start()
    yield
    await manager.stop()
    await school21_client.stop()
    await close_redis()


app = FastAPI(
    title="P2P Platform",
    version="3.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
