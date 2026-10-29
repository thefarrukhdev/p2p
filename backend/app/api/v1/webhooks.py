"""Webhook endpoints for Vercel, Telegram Bot interactive commands, and DevOps logging."""
from __future__ import annotations

import html
import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

from app.api.v1.diagnostics import get_system_diagnostics
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


@router.post("/vercel-log-drain")
async def vercel_log_drain(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Receive Vercel Log Drain events and forward critical logs to Telegram."""
    try:
        raw_body = await request.body()
        # Vercel Log Drain can send newline-delimited JSON or a JSON array
        entries: list[dict[str, Any]] = []
        body_text = raw_body.decode("utf-8", errors="replace")
        for line in body_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, list):
                    entries.extend(item)
                elif isinstance(item, dict):
                    entries.append(item)
            except Exception:
                continue
    except Exception:
        return {"status": "error_parsing"}

    for item in entries:
        status_code = item.get("statusCode") or item.get("proxy", {}).get("statusCode")
        log_type = item.get("type", "")
        message = item.get("message") or item.get("stderr") or ""
        path = item.get("path") or item.get("proxy", {}).get("path") or ""

        # Faqat xatoliklar yoki 4xx/5xx so'rovlarni guruhga yuboramiz
        is_error = (
            (status_code and status_code >= 400)
            or log_type in ("stderr", "error")
            or "error" in str(message).lower()
        )

        if is_error and (path or message):
            code_str = f" ({status_code})" if status_code else ""
            lines = [
                f"❌ <b>[Vercel Log Drain] Xatolik{code_str}</b>",
                "━━━━━━━━━━━━━━━━━━━━",
            ]
            if path:
                lines.append(f"Yo'l: <code>{html.escape(path)}</code>")
            if message:
                lines.append(f"Xabar: <code>{html.escape(str(message)[:500])}</code>")
            
            client_ip = item.get("proxy", {}).get("clientIp") or item.get("clientIp")
            if client_ip:
                lines.append(f"Client IP: <code>{html.escape(client_ip)}</code>")

            lines.append(f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
            background_tasks.add_task(send_telegram_log, "\n".join(lines))

    return {"status": "processed", "count": str(len(entries))}


async def handle_telegram_command(command: str) -> None:
    """Execute Telegram bot interactive command and reply to the group."""
    cmd = command.strip().lower()
    if cmd in ("/status", "/health", "status", "health"):
        diag = await get_system_diagnostics()

        # Check frontend ping
        fe_ok = False
        fe_latency = -1
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get("https://school21-p2p.vercel.app")
                if res.status_code == 200:
                    fe_ok = True
                    fe_latency = round((time.perf_counter() - t0) * 1000, 1)
        except Exception:
            pass

        db_icon = "✅" if diag["database"]["connected"] else "❌"
        db_lat = f"{diag['database']['latency_ms']}ms" if diag["database"]["connected"] else "Ulanmagan"
        redis_icon = "✅" if diag["redis"]["connected"] else "❌"
        redis_lat = f"{diag['redis']['latency_ms']}ms" if diag["redis"]["connected"] else "Ulanmagan"
        fe_icon = "✅" if fe_ok else "❌"
        fe_lat = f"{fe_latency}ms" if fe_ok else "Javob bermadi"

        text = (
            "✅ <b>Serverlar Holati (Batafsil Diagnostika)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{fe_icon} <b>Frontend (Vercel):</b> {fe_lat}\n"
            f"✅ <b>Backend (Render):</b> Ishlamoqda\n"
            f"{db_icon} <b>Database (PostgreSQL):</b> {db_lat}\n"
            f"{redis_icon} <b>Redis Kesh:</b> {redis_lat}\n"
            f"RAM Ishlatilishi: <code>{diag['memory_mb']} MB</code>\n"
            f"Server Uptime: <code>{diag['uptime']}</code>\n"
            f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
        )
        await send_telegram_log(text)

    elif cmd in ("/help", "help"):
        text = (
            "<b>P2P DevOps Bot Buyruqlari:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• <code>/status</code> - Serverlar, Database va Redisning jonli holati\n"
            "• <code>/ping</code> - Tezkor aloqa tekshiruvi\n"
            "• <code>/help</code> - Ushbu yordam oynasi"
        )
        await send_telegram_log(text)

    elif cmd in ("/ping", "ping"):
        text = f"✅ <b>Pong!</b> Backend (Render) ishlamoqda. Vaqt: <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
        await send_telegram_log(text)


@router.post("/telegram-bot")
async def telegram_bot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Handle incoming Telegram webhook commands (/status, /health, etc)."""
    try:
        update = await request.json()
        message = update.get("message") or update.get("channel_post") or {}
        text = message.get("text", "")
        if text.startswith("/"):
            # Command parsed
            cmd = text.split()[0].split("@")[0]  # Masalan /status@p2p_devops_bot -> /status
            background_tasks.add_task(handle_telegram_command, cmd)
    except Exception:
        pass

    return {"status": "ok"}


@router.post("/log")
async def client_log(
    req: ClientLogRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Log an event or error message directly to the Telegram group."""
    if req.level.upper() in ("ERROR", "CRITICAL", "FATAL"):
        icon = "❌"
    else:
        icon = "✅"

    text = (
        f"{icon} <b>[{req.source.upper()}] Log ({req.level.upper()})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Xabar: {req.message}\n"
    )
    if req.details:
        details_str = json.dumps(req.details, indent=2, ensure_ascii=False)[:1000]
        text += f"\n<pre>{html.escape(details_str)}</pre>\n"

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
        "P2P FastAPI Webhook va Telegram Logger muvaffaqiyatli ishlamoqda."
    )
    background_tasks.add_task(send_telegram_log, text)
    return {"status": "test_dispatched"}
