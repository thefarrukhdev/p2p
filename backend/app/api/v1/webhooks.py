"""Webhook endpoints for Vercel, Telegram Bot interactive commands, and DevOps logging."""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.v1.diagnostics import get_system_diagnostics
from app.core.config import settings
from app.core.dependencies import CurrentAdmin, DbSession
from app.core.security import decode_token
from app.db.models.user import User
from app.services.telegram_logger import (
    process_vercel_webhook,
    send_telegram_log,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Logging"])

# Simple in-memory sliding cache to throttle duplicate client error reports
_client_log_cache: dict[str, float] = {}
_CLIENT_LOG_THROTTLE_SECONDS = 30.0
_CLIENT_LOG_MAX_ENTRIES = 5000


class ClientLogRequest(BaseModel):
    level: str = Field(default="INFO", max_length=20)
    source: str = Field(default="frontend", max_length=50)
    message: str = Field(..., min_length=1, max_length=1000)
    details: dict[str, Any] | None = None


def redact_sensitive_data(val: Any) -> Any:
    """Recursively redact sensitive query params, Bearer tokens, passwords, and secrets."""
    if isinstance(val, str):
        # 1. Redact URL query parameters
        s = re.sub(
            r"([?&](?:token|access_token|refresh_token|password|secret|key|api_key|auth|code)=)[^&\s]+",
            r"\1[REDACTED]",
            val,
            flags=re.IGNORECASE,
        )
        # 2. Redact Bearer tokens
        s = re.sub(
            r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
            "Bearer [REDACTED]",
            s,
            flags=re.IGNORECASE,
        )
        # 3. Redact sensitive JSON key-values
        s = re.sub(
            r"((\"|')(?:password|secret|token|refresh_token|access_token)(\"|')\s*[:=]\s*(\"|'))[^\"']+",
            r"\1[REDACTED]",
            s,
            flags=re.IGNORECASE,
        )
        return s
    elif isinstance(val, dict):
        redacted: dict[str, Any] = {}
        for k, v in val.items():
            if any(
                term in str(k).lower()
                for term in ("password", "secret", "token", "auth", "credential")
            ):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    elif isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    return val


def verify_vercel_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    """Verify Vercel webhook HMAC-SHA1 signature using constant-time comparison."""
    if not secret or not signature:
        return False
    sig = signature.strip().lower()
    if sig.startswith("sha1="):
        sig = sig[5:]
    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest().lower()
    return hmac.compare_digest(computed, sig)


@router.post("/vercel")
async def vercel_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_vercel_signature: str | None = Header(None, alias="x-vercel-signature"),
) -> dict[str, str]:
    """Receive and forward authenticated Vercel deployment webhooks to Telegram."""
    if not settings.VERCEL_WEBHOOK_SECRET:
        logger.warning("Vercel webhook rejected: VERCEL_WEBHOOK_SECRET is not configured")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vercel webhook secret not configured or signature invalid",
        )

    raw_body = await request.body()
    sig = x_vercel_signature or request.headers.get("x-vercel-signature")
    if not verify_vercel_signature(raw_body, sig, settings.VERCEL_WEBHOOK_SECRET):
        logger.warning("Vercel webhook rejected: signature mismatch or missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    background_tasks.add_task(process_vercel_webhook, payload)
    return {"status": "accepted"}


@router.post("/vercel-log-drain")
async def vercel_log_drain(
    request: Request,
    background_tasks: BackgroundTasks,
    x_vercel_signature: str | None = Header(None, alias="x-vercel-signature"),
) -> dict[str, str]:
    """Receive authenticated Vercel Log Drain events and forward critical logs to Telegram."""
    # Separate dedicated secret: fail closed if VERCEL_LOG_DRAIN_SECRET is missing
    secret = settings.VERCEL_LOG_DRAIN_SECRET
    if not secret:
        logger.warning(
            "Vercel log drain rejected: VERCEL_LOG_DRAIN_SECRET is not configured"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vercel log drain secret not configured or signature invalid",
        )

    raw_body = await request.body()
    sig = x_vercel_signature or request.headers.get("x-vercel-signature")
    if not verify_vercel_signature(raw_body, sig, secret):
        logger.warning("Vercel log drain rejected: signature mismatch or missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error parsing log drain body",
        )

    for item in entries:
        if not isinstance(item, dict):
            continue
        status_code = item.get("statusCode") or item.get("proxy", {}).get("statusCode")
        log_type = item.get("type", "")
        message = item.get("message") or item.get("stderr") or ""
        path = item.get("path") or item.get("proxy", {}).get("path") or ""

        # Only error logs or 4xx/5xx requests forwarded to monitoring group
        is_error = (
            (status_code and isinstance(status_code, int) and status_code >= 400)
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
                lines.append(f"Yo'l: <code>{html.escape(str(path)[:200])}</code>")
            if message:
                lines.append(f"Xabar: <code>{html.escape(str(message)[:500])}</code>")

            client_ip = item.get("proxy", {}).get("clientIp") or item.get("clientIp")
            if client_ip:
                lines.append(f"Client IP: <code>{html.escape(str(client_ip)[:100])}</code>")

            lines.append(
                f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
            )
            background_tasks.add_task(send_telegram_log, "\n".join(lines))

    return {"status": "processed", "count": str(len(entries))}


async def handle_telegram_command(command: str) -> None:
    """Execute Telegram bot interactive command and reply to the group."""
    cmd = command.strip().lower()
    if cmd in ("/status", "/health", "status", "health"):
        try:
            diag = await get_system_diagnostics()
        except Exception:
            logger.exception("Failed to get diagnostics in Telegram command")
            await send_telegram_log("❌ Diagnostika ma'lumotlarini olishda xatolik yuz berdi.")
            return

        # Check frontend ping
        fe_ok = False
        fe_latency = -1.0
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get("https://school21-p2p.vercel.app")
                if res.status_code == 200:
                    fe_ok = True
                    fe_latency = round((time.perf_counter() - t0) * 1000, 1)
        except Exception:
            pass

        db_icon = "✅" if diag.get("database", {}).get("connected") else "❌"
        db_lat = (
            f"{diag.get('database', {}).get('latency_ms', 0)}ms"
            if diag.get("database", {}).get("connected")
            else "Ulanmagan"
        )
        redis_icon = "✅" if diag.get("redis", {}).get("connected") else "❌"
        redis_lat = (
            f"{diag.get('redis', {}).get('latency_ms', 0)}ms"
            if diag.get("redis", {}).get("connected")
            else "Ulanmagan"
        )
        fe_icon = "✅" if fe_ok else "❌"
        fe_lat = f"{fe_latency}ms" if fe_ok else "Javob bermadi"
        mem_val = diag.get("memory_mb", "Noma'lum")
        uptime_val = diag.get("uptime", "Noma'lum")

        text = (
            "✅ <b>Serverlar Holati (Batafsil Diagnostika)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{fe_icon} <b>Frontend (Vercel):</b> {fe_lat}\n"
            f"✅ <b>Backend (Render):</b> Ishlamoqda\n"
            f"{db_icon} <b>Database (PostgreSQL):</b> {db_lat}\n"
            f"{redis_icon} <b>Redis Kesh:</b> {redis_lat}\n"
            f"RAM Ishlatilishi: <code>{mem_val} MB</code>\n"
            f"Server Uptime: <code>{uptime_val}</code>\n"
            f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
        )
        await send_telegram_log(text)

    elif cmd in ("/logs", "logs"):
        lines = [
            "<b>[Vercel So'nggi Deploy Loglari]</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        if settings.VERCEL_TOKEN:
            try:
                url = (
                    f"https://api.vercel.com/v6/deployments"
                    f"?projectId={settings.VERCEL_PROJECT_ID}&limit=1"
                )
                headers = {"Authorization": f"Bearer {settings.VERCEL_TOKEN}"}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        deps = data.get("deployments", [])
                        if deps:
                            dep = deps[0]
                            dep_state = dep.get("state", "UNKNOWN")
                            icon = (
                                "✅"
                                if dep_state == "READY"
                                else "❌"
                                if dep_state in ("ERROR", "CANCELED")
                                else "⏳"
                            )
                            lines[0] = f"{icon} <b>[Vercel So'nggi Deploy Holati]</b>"
                            raw_commit_msg = (
                                dep.get("meta", {}).get("githubCommitMessage") or "Noma'lum"
                            )
                            safe_commit_msg = html.escape(str(raw_commit_msg)[:300])
                            dep_url = html.escape(str(dep.get("url", "")))
                            dep_uid = html.escape(str(dep.get("uid", "")))
                            lines.extend([
                                f"Holat: <code>{dep_state}</code>",
                                f"Commit: <i>{safe_commit_msg}</i>",
                                f"Sayt: <a href=\"https://{dep_url}\">{dep_url}</a>",
                                f"Deploy ID: <code>{dep_uid}</code>",
                            ])
                            if dep_state in ("ERROR", "CANCELED"):
                                ev_url = (
                                    f"https://api.vercel.com/v2/deployments/{dep.get('uid')}"
                                    f"/events?limit=25"
                                )
                                ev_resp = await client.get(ev_url, headers=headers)
                                if ev_resp.status_code == 200:
                                    events = ev_resp.json()
                                    err_lines = [
                                        str(e.get("payload", {}).get("text", ""))[:200]
                                        for e in events
                                        if e.get("payload", {}).get("text")
                                    ]
                                    if err_lines:
                                        safe_err_text = html.escape("\n".join(err_lines[-6:]))
                                        lines.extend([
                                            "",
                                            "<b>Xatolik logi:</b>",
                                            f"<pre>{safe_err_text[:1200]}</pre>",
                                        ])
                    else:
                        lines.append(f"Vercel API xatosi: {resp.status_code}")
            except Exception:
                logger.exception("Failed to retrieve Vercel deployment logs")
                lines.append("Loglarni olishda xatolik yuz berdi.")
        else:
            lines.append("VERCEL_TOKEN sozlanmagan.")

        lines.append(
            f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
        )
        await send_telegram_log("\n".join(lines))

    elif cmd in ("/help", "help"):
        text = (
            "<b>P2P DevOps Bot Buyruqlari:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• <code>/status</code> - Serverlar, Database va Redisning jonli holati\n"
            "• <code>/logs</code> - Vercelning so'nggi deploy va build loglari\n"
            "• <code>/ping</code> - Tezkor aloqa tekshiruvi\n"
            "• <code>/help</code> - Ushbu yordam oynasi"
        )
        await send_telegram_log(text)

    elif cmd in ("/ping", "ping"):
        text = (
            f"✅ <b>Pong!</b> Backend (Render) ishlamoqda. Vaqt: "
            f"<code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
        )
        await send_telegram_log(text)


@router.post("/telegram-bot")
async def telegram_bot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(
        None, alias="x-telegram-bot-api-secret-token"
    ),
) -> dict[str, str]:
    """Handle incoming Telegram webhook commands (/status, /health, etc)."""
    # Safe disabled-by-default when no secret is configured
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram bot webhook is disabled",
        )

    token = x_telegram_bot_api_secret_token or request.headers.get(
        "x-telegram-bot-api-secret-token"
    )
    if not token or not hmac.compare_digest(
        token.strip(), settings.TELEGRAM_WEBHOOK_SECRET.strip()
    ):
        logger.warning("Telegram webhook rejected: secret token mismatch or missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram secret token",
        )

    try:
        update = await request.json()
        if not isinstance(update, dict):
            raise ValueError("Update must be a JSON object")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    message = update.get("message") or update.get("channel_post") or {}
    text = message.get("text", "")
    if text.startswith("/"):
        cmd = text.split()[0].split("@")[0]
        background_tasks.add_task(handle_telegram_command, cmd)

    return {"status": "ok"}


@router.post("/log")
async def client_log(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> dict[str, str]:
    """Log a client-side error or telemetry event with bounded ingestion, redaction, and auth-based forwarding."""
    # 1. Enforce total raw body limit (10 KB max)
    raw_body = await request.body()
    if len(raw_body) > 10_240:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Telemetry payload too large (max 10KB)",
        )

    # 2. Defense-in-depth Origin verification if provided by browser
    origin = request.headers.get("origin")
    if origin:
        allowed = set(settings.cors_origins) | {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        }
        if origin not in allowed:
            logger.warning("Client log rejected: untrusted origin %s", origin)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Untrusted origin",
            )

    # 3. Parse JSON safely
    try:
        data = json.loads(raw_body)
        if not isinstance(data, dict):
            raise ValueError("Payload must be a JSON object")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # 4. Enforce nested details size limit (max 2048 chars when serialized)
    raw_details = data.get("details")
    if raw_details is not None:
        if not isinstance(raw_details, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Details must be a dictionary object",
            )
        details_str = json.dumps(raw_details)
        if len(details_str) > 2048:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Details dictionary exceeds maximum allowed size (2048 bytes)",
            )

    # 5. Validate with Pydantic model
    try:
        req = ClientLogRequest(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exc}",
        )

    # 6. Redact sensitive tokens/credentials and HTML-escape all user-controlled text
    redacted_message = redact_sensitive_data(req.message.strip()[:1000])
    safe_message = html.escape(str(redacted_message))
    safe_level = html.escape(req.level.strip()[:20].upper())
    safe_source = html.escape(req.source.strip()[:50])

    redacted_details = redact_sensitive_data(req.details) if req.details else None
    safe_details_str = ""
    if redacted_details:
        details_json = json.dumps(redacted_details, indent=2, ensure_ascii=False)[:1000]
        safe_details_str = html.escape(details_json)

    # 7. Server-verifiable authentication check
    auth_header = request.headers.get("authorization")
    authenticated_user: User | None = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            sub = payload.get("sub")
            if sub:
                try:
                    user_id = uuid.UUID(sub)
                    candidate = await db.get(User, user_id)
                    if candidate and candidate.is_active and candidate.is_logged_in:
                        authenticated_user = candidate
                except Exception:
                    authenticated_user = None

    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )

    # 8. ANONYMOUS REQUEST POLICY:
    # "An anonymous browser request must not directly trigger an arbitrary Telegram alert."
    # Bounded, sanitized internal collection only!
    if authenticated_user is None:
        logger.warning(
            "[ANONYMOUS TELEMETRY] [%s] [%s] %s | IP: %s | Details: %s",
            safe_source,
            safe_level,
            safe_message,
            client_ip,
            safe_details_str[:200] if safe_details_str else "none",
        )
        return {"status": "recorded_internally"}

    # 9. AUTHENTICATED REQUEST POLICY:
    # Authenticated user can trigger Telegram alert if level is ERROR/WARN, subject to throttling
    if safe_level not in ("ERROR", "CRITICAL", "FATAL", "WARN", "WARNING"):
        return {"status": "recorded_internally"}

    # Throttling by user_id + message fingerprint
    cache_key = f"{authenticated_user.id}:{safe_level}:{safe_message[:80]}"
    now = time.time()

    # Clean up stale cache entries if map exceeds maximum allowed entries
    if len(_client_log_cache) > _CLIENT_LOG_MAX_ENTRIES:
        stale_keys = [
            k
            for k, v in _client_log_cache.items()
            if now - v > _CLIENT_LOG_THROTTLE_SECONDS * 2
        ]
        for k in stale_keys:
            _client_log_cache.pop(k, None)

    last_time = _client_log_cache.get(cache_key)
    if last_time and (now - last_time < _CLIENT_LOG_THROTTLE_SECONDS):
        return {"status": "throttled"}

    _client_log_cache[cache_key] = now

    icon = "❌" if safe_level in ("ERROR", "CRITICAL", "FATAL") else "⚠️"
    text_parts = [
        f"{icon} <b>[{safe_source}] Log ({safe_level})</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"Foydalanuvchi: <code>{authenticated_user.school21_login}</code> (ID: <code>{authenticated_user.id}</code>)",
        f"Xabar: {safe_message}",
    ]
    if safe_details_str:
        text_parts.append(f"\n<pre>{safe_details_str}</pre>")

    background_tasks.add_task(send_telegram_log, "\n".join(text_parts))
    return {"status": "queued"}


@router.post("/test")
async def test_logger(
    admin: CurrentAdmin,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Test Telegram logger bot integration (authenticated admin only)."""
    text = (
        "✅ <b>DevOps Test Xabari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "P2P FastAPI Webhook va Telegram Logger muvaffaqiyatli ishlamoqda."
    )
    background_tasks.add_task(send_telegram_log, text)
    return {"status": "test_dispatched"}
