"""Notification persistence + Telegram dispatch trigger."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification
from app.db.models.slot import Slot
from app.db.models.user import User

MAX_REMINDER_LATENESS_MINUTES = 5

ELIGIBLE_TELEGRAM_TYPES = (
    "slot_reminder",
    "slot_revealed",
    "slot_cancelled",
    "absent_given",
    "slot_booked",
)


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type_: str,
    title: str | None = None,
    body: str | None = None,
    slot_id: uuid.UUID | None = None,
) -> Notification:
    """Persist a notification row. Telegram delivery is handled by Celery.
    Non-Telegram types (system announcements, reviews) are initialized as 'not_eligible'.
    """
    initial_status = (
        "pending" if type_ in ELIGIBLE_TELEGRAM_TYPES else "not_eligible"
    )
    initial_error = (
        None if type_ in ELIGIBLE_TELEGRAM_TYPES else "type_not_configured_for_telegram"
    )
    notif = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        slot_id=slot_id,
        sent_telegram=False,
        telegram_delivery_status=initial_status,
        telegram_error=initial_error,
    )
    db.add(notif)
    await db.flush()
    return notif


async def requeue_quarantined_notification(
    db: AsyncSession,
    notification_id: uuid.UUID,
) -> tuple[Notification | None, str | None]:
    """Reset a quarantined notification back to 'pending' with 0 claim attempts for manual operator re-dispatch.

    Safety validations:
    1. Row-level locking (with_for_update) to prevent concurrent retry race conditions.
    2. Existence and quarantine-state check (only 'quarantined_claim_exhausted' can be retried).
    3. Recipient eligibility check (user must exist and have a valid telegram_id).
    4. Lateness check (expired slot reminders past 5 minutes are marked failed_permanent and rejected).
    5. Preserves telegram_attempts counter and records an audit note in telegram_error.

    Returns:
        tuple[Notification | None, str | None]: (notif, error_code)
    """
    stmt = (
        select(Notification)
        .where(Notification.id == notification_id)
        .with_for_update()
    )
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if notif is None:
        return None, "not_found"

    if notif.telegram_delivery_status != "quarantined_claim_exhausted":
        return None, f"invalid_state:{notif.telegram_delivery_status}"

    # Recipient eligibility check
    user = await db.get(User, notif.user_id)
    if user is None or not user.telegram_id:
        notif.telegram_delivery_status = "failed_permanent"
        notif.sent_telegram = False
        notif.telegram_error = "retry_rejected: recipient has no linked Telegram account"
        notif.telegram_next_retry_at = None
        notif.telegram_claim_token = None
        notif.telegram_claimed_at = None
        await db.flush()
        return None, "missing_telegram_id"

    # Time-sensitive reminder expiration check
    now = datetime.now(timezone.utc)
    if notif.type in ("slot_reminder", "slot_revealed") and notif.slot_id:
        slot = await db.get(Slot, notif.slot_id)
        if slot and slot.start_time:
            lateness_deadline = slot.start_time + timedelta(minutes=MAX_REMINDER_LATENESS_MINUTES)
            if now > lateness_deadline:
                notif.telegram_delivery_status = "failed_permanent"
                notif.sent_telegram = False
                notif.telegram_error = "retry_rejected: reminder expired past lateness deadline"
                notif.telegram_next_retry_at = None
                notif.telegram_claim_token = None
                notif.telegram_claimed_at = None
                await db.flush()
                return None, "expired_past_lateness_deadline"

    # Reset transient claim fields while preserving attempts and recording audit note
    prev_error = notif.telegram_error or "none"
    notif.telegram_delivery_status = "pending"
    notif.sent_telegram = False
    notif.telegram_claim_attempts = 0
    notif.telegram_error = f"requeued_by_admin (previous_diagnostic: {prev_error})"
    notif.telegram_next_retry_at = None
    notif.telegram_claim_token = None
    notif.telegram_claimed_at = None
    await db.flush()
    return notif, None
