"""Telegram outbox dispatch client."""
from __future__ import annotations

import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def dispatch_notification(
    telegram_id: int, title: str | None, body: str | None
) -> tuple[bool, bool, str | None, int | None]:
    """Send Telegram message via Telegram Bot API outside of database transactions.

    Returns:
        (success: bool, permanent_failure: bool, error_msg: str | None, retry_after: int | None)
        - success=True: delivered to Telegram API.
        - permanent_failure=True: e.g. 403 Forbidden (bot blocked by user) or 400 (chat not found).
          Must NOT be retried to prevent infinite retry loops.
        - success=False, permanent_failure=False: temporary error (network timeout, 429 rate limit, 5xx).
          Eligible for subsequent retry with backoff.
        - retry_after: integer seconds if Telegram API provided a Retry-After header/parameter.
    """
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "mock-bot-token":
        # Dev / test environment: treat as safely dispatched without external network call
        return True, False, None, None

    text = f"<b>{title or 'Bildirishnoma'}</b>\n\n{body or ''}"
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True, False, None, None
            elif resp.status_code in (400, 403):
                err = f"HTTP {resp.status_code}: {resp.text[:120]}"
                logger.warning(
                    "Permanent Telegram delivery failure for user %s: %s",
                    telegram_id,
                    err,
                )
                return False, True, err, None
            elif resp.status_code == 429:
                retry_after: int | None = None
                try:
                    data = resp.json()
                    retry_after = data.get("parameters", {}).get("retry_after")
                except Exception:
                    pass
                if not retry_after and "Retry-After" in resp.headers:
                    try:
                        retry_after = int(resp.headers["Retry-After"])
                    except ValueError:
                        pass
                err = f"HTTP 429 Rate Limited (retry_after={retry_after})"
                logger.warning(
                    "Telegram rate limit for user %s: %s",
                    telegram_id,
                    err,
                )
                return False, False, err, retry_after
            else:
                err = f"HTTP {resp.status_code}: {resp.text[:120]}"
                logger.warning(
                    "Temporary Telegram delivery error for user %s: %s",
                    telegram_id,
                    err,
                )
                return False, False, err, None
    except Exception as exc:
        err = f"NetworkError: {type(exc).__name__}: {str(exc)[:120]}"
        logger.warning("Telegram network error for user %s: %s", telegram_id, err)
        return False, False, err, None
