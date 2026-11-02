"""Logging security filters and formatters for redacting sensitive credentials and tokens."""
from __future__ import annotations

import logging
import re
from typing import Any

# Matches Telegram Bot API URL token patterns:
# e.g. https://api.telegram.org/bot<TOKEN>/... or /bot<TOKEN>/... or /file/bot<TOKEN>/...
TELEGRAM_TOKEN_REGEX = re.compile(
    r"((?:https?://api\.telegram\.org)?/(?:file/)?bot)[^/\s?\"'<>]+",
    re.IGNORECASE,
)


def redact_telegram_token(text: str) -> str:
    """Replace Telegram bot tokens in text or URL strings with [REDACTED]."""
    if not text:
        return text
    return TELEGRAM_TOKEN_REGEX.sub(r"\g<1>[REDACTED]", text)


def _sanitize_log_value(val: Any) -> Any:
    """Helper to redact sensitive tokens in log arguments without altering other types."""
    if val is None:
        return None
    val_str = str(val)
    if "bot" in val_str.lower():
        return redact_telegram_token(val_str)
    return val


class TelegramTokenRedactionFilter(logging.Filter):
    """Logging filter that redacts Telegram bot tokens from log records (msg, args, exc_text)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_telegram_token(record.msg)

        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(_sanitize_log_value(arg) for arg in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: _sanitize_log_value(v) for k, v in record.args.items()}

        if record.exc_text:
            record.exc_text = redact_telegram_token(record.exc_text)

        return True


class TelegramTokenRedactionFormatter(logging.Formatter):
    """Logging formatter that redacts Telegram bot tokens from formatted log output."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return redact_telegram_token(formatted)


def configure_secure_logging() -> None:
    """Attach redaction filters to httpx, httpcore, telegram, root loggers, and active handlers."""
    redaction_filter = TelegramTokenRedactionFilter()

    # 1. Attach filter to relevant HTTP and Telegram loggers
    for logger_name in ("httpx", "httpcore", "telegram", "telegram.ext", "app", "bot"):
        log_obj = logging.getLogger(logger_name)
        if not any(isinstance(f, TelegramTokenRedactionFilter) for f in log_obj.filters):
            log_obj.addFilter(redaction_filter)

    # 2. Attach filter and formatter to root logger and its handlers
    root = logging.getLogger()
    if not any(isinstance(f, TelegramTokenRedactionFilter) for f in root.filters):
        root.addFilter(redaction_filter)

    for handler in root.handlers:
        if not any(isinstance(f, TelegramTokenRedactionFilter) for f in handler.filters):
            handler.addFilter(redaction_filter)
        if handler.formatter and not isinstance(handler.formatter, TelegramTokenRedactionFormatter):
            original_fmt = getattr(handler.formatter, "_fmt", None)
            original_datefmt = getattr(handler.formatter, "datefmt", None)
            handler.setFormatter(TelegramTokenRedactionFormatter(original_fmt, original_datefmt))
