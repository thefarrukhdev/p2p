"""Webhook endpoints for Vercel, client errors, and DevOps logging."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

from app.services.telegram_logger import (
    process_vercel_webhook,
    send_telegram_log,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Logging"])


class ClientLogRequest(BaseModel):
    level: str = "INFO"
    source: str = "frontend"
    message: str
    details: dict[str, Any] | None = None


@router.post("/vercel")
async def vercel_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Receive and forward Vercel deployment webhooks to Telegram."""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "invalid_json"}

    background_tasks.add_task(process_vercel_webhook, payload)
    return {"status": "accepted"}


@router.post("/log")
async def client_log(
    req: ClientLogRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Log an event or error message directly to the Telegram group."""
    icon = "⚡️"
    if req.level.upper() in ("ERROR", "CRITICAL", "FATAL"):
        icon = "🚨"
    elif req.level.upper() == "WARN":
        icon = "⚠️"

    text = (
        f"{icon} <b>[{req.source.upper()}] Log ({req.level.upper()})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 <b>Xabar:</b> {req.message}\n"
    )
    if req.details:
        import json
        details_str = json.dumps(req.details, indent=2, ensure_ascii=False)[:1000]
        text += f"\n<pre>{details_str}</pre>\n"

    background_tasks.add_task(send_telegram_log, text)
    return {"status": "queued"}


@router.post("/test")
async def test_logger(
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Test Telegram logger bot integration."""
    text = (
        "✅ <b>DevOps Test Xabari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "P2P FastAPI Webhook va Telegram Logger muvaffaqiyatli ishlamoqda!"
    )
    background_tasks.add_task(send_telegram_log, text)
    return {"status": "test_dispatched"}
