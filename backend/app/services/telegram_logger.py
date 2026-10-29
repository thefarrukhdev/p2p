"""Service for dispatching DevOps alerts and logs to Telegram."""
from __future__ import annotations

import html
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_log(text: str, parse_mode: str = "HTML") -> bool:
    """Send a formatted message to the configured Telegram monitoring chat."""
    token = settings.TELEGRAM_LOGGER_BOT_TOKEN
    chat_id = settings.TELEGRAM_LOGGER_CHAT_ID

    if not token or not chat_id:
        logger.debug("Telegram logger is not configured (missing token or chat_id)")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            logger.warning(
                "Telegram logger returned non-200 code %s: %s",
                resp.status_code,
                resp.text,
            )
            return False
    except Exception as exc:
        logger.error("Failed to deliver Telegram log alert: %s", exc)
        return False


async def log_server_exception(
    method: str,
    path: str,
    status_code: int,
    error_type: str,
    error_msg: str,
    traceback_str: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Format and dispatch an uncaught server exception alert."""
    safe_method = html.escape(method)
    safe_path = html.escape(path)
    safe_ip = html.escape(client_ip or "Noma'lum")
    safe_err_type = html.escape(error_type)
    safe_err_msg = html.escape(error_msg[:300])

    lines = [
        f"🚨 <b>Backend Server Xatosi ({status_code})</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📍 <b>Endpoint:</b> <code>{safe_method} {safe_path}</code>",
        f"🌐 <b>Client IP:</b> <code>{safe_ip}</code>",
        f"⚠️ <b>Xato turi:</b> <code>{safe_err_type}</code>",
        f"💬 <b>Xabar:</b> {safe_err_msg}",
    ]

    if traceback_str:
        # Telegram limit 4096 belgini hisobga olgan holda oxirgi qismini qoldiramiz
        short_tb = html.escape(traceback_str[-1200:])
        lines.extend([
            "",
            "<b>Stacktrace:</b>",
            f"<pre>{short_tb}</pre>",
        ])

    lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    await send_telegram_log("\n".join(lines))


async def process_vercel_webhook(payload: dict[str, Any]) -> bool:
    """Parse a Vercel webhook event and forward as a Telegram alert."""
    event_type = payload.get("type", "unknown")
    deployment = payload.get("payload", {}).get("deployment", {})
    if not deployment and "deployment" in payload:
        deployment = payload["deployment"]

    name = html.escape(deployment.get("name") or payload.get("payload", {}).get("name") or "school21-p2p")
    url = deployment.get("url", "")
    target = html.escape(deployment.get("target") or "production")
    meta = deployment.get("meta", {})
    git_commit_msg = html.escape(meta.get("githubCommitMessage", "Noma'lum"))
    git_branch = html.escape(meta.get("githubCommitRef", "main"))
    git_author = html.escape(meta.get("githubCommitAuthorName", "Noma'lum"))

    if "created" in event_type:
        icon = "⏳"
        title = f"Vercel: Yangi Deploy Boshlandi ({target})"
    elif "succeeded" in event_type or "ready" in event_type:
        icon = "🚀"
        title = f"Vercel: Deployment Muvaffaqiyatli! ({target})"
    elif "error" in event_type or "failed" in event_type:
        icon = "❌"
        title = f"Vercel: Deploymentda Xatolik! ({target})"
    elif "canceled" in event_type:
        icon = "⚪️"
        title = f"Vercel: Deployment Bekor Qilindi ({target})"
    else:
        icon = "ℹ️"
        title = f"Vercel: {event_type}"

    lines = [
        f"{icon} <b>{title}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📦 <b>Loyiha:</b> <code>{name}</code>",
        f"🌿 <b>Branch:</b> <code>{git_branch}</code>",
        f"👤 <b>Muallif:</b> {git_author}",
        f"📝 <b>Commit:</b> <i>{git_commit_msg}</i>",
    ]

    if url:
        full_url = f"https://{url}" if not url.startswith("http") else url
        lines.append(f"🔗 <b>Havola:</b> <a href=\"{full_url}\">{full_url}</a>")

    lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    return await send_telegram_log("\n".join(lines))
