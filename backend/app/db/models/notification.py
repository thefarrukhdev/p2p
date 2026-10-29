"""Notification model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base, TimestampMixin

ALLOWED_DELIVERY_STATUSES = frozenset({
    "pending",
    "claimed",
    "sent",
    "failed_transient",
    "failed_permanent",
    "quarantined_claim_exhausted",
    "abandoned_historical",
    "not_eligible",
})


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slots.id"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_telegram: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    telegram_delivery_status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False, server_default="pending"
    )
    telegram_claim_token: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    telegram_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    telegram_claim_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )
    telegram_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )
    telegram_next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    telegram_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    @validates("sent_telegram")
    def validate_sent_telegram(self, key: str, value: bool) -> bool:
        """Enforce delivery invariant: legacy boolean aligns delivery status."""
        if getattr(self, "_in_delivery_validation", False):
            return value
        self._in_delivery_validation = True
        try:
            current_status = getattr(self, "telegram_delivery_status", None)
            if value and current_status != "sent":
                self.telegram_delivery_status = "sent"
            elif not value and current_status == "sent":
                self.telegram_delivery_status = "pending"
        finally:
            self._in_delivery_validation = False
        return value

    @validates("telegram_delivery_status")
    def validate_delivery_status(self, key: str, value: str) -> str:
        """Enforce delivery invariant and validate allowed delivery status domain."""
        if value not in ALLOWED_DELIVERY_STATUSES:
            raise ValueError(
                f"Invalid telegram_delivery_status: {value!r}. "
                f"Allowed states: {sorted(ALLOWED_DELIVERY_STATUSES)}"
            )
        if getattr(self, "_in_delivery_validation", False):
            return value
        self._in_delivery_validation = True
        try:
            target_sent = (value == "sent")
            if getattr(self, "sent_telegram", None) != target_sent:
                self.sent_telegram = target_sent
        finally:
            self._in_delivery_validation = False
        return value

    def set_delivery_status(
        self,
        status: str,
        *,
        error: str | None = None,
        next_retry: datetime | None = None,
    ) -> None:
        """Authoritative state transition helper enforcing the delivery invariant:
        sent_telegram == (telegram_delivery_status == 'sent')
        """
        if status not in ALLOWED_DELIVERY_STATUSES:
            raise ValueError(
                f"Invalid telegram_delivery_status: {status!r}. "
                f"Allowed states: {sorted(ALLOWED_DELIVERY_STATUSES)}"
            )
        self._in_delivery_validation = True
        try:
            self.telegram_delivery_status = status
            self.sent_telegram = (status == "sent")
            self.telegram_error = error
            self.telegram_next_retry_at = next_retry
            if status != "claimed":
                self.telegram_claim_token = None
                self.telegram_claimed_at = None
        finally:
            self._in_delivery_validation = False
