"""Slot-related background tasks: reminders, reveal, absence checks."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select, update

from app.db.base import AsyncSessionLocal
from app.db.models.slot import Slot, SlotStatus
from app.services.notification_service import create_notification
from app.tasks.async_utils import run_async
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

REMINDER_LEAD_MINUTES = 15
MAX_REMINDER_LATENESS_MINUTES = 5
ABSENT_GRACE_MINUTES = 15

MAX_TELEGRAM_ATTEMPTS = 5
TELEGRAM_CLAIM_BATCH_SIZE = 10
TELEGRAM_LEASE_MINUTES = 5


@celery_app.task(name="app.tasks.slot_tasks.send_slot_reminders")
def send_slot_reminders() -> int:
    return run_async(_send_slot_reminders())


async def _send_slot_reminders() -> int:
    """Two-stage durable reminder delivery (Transactional Outbox Pattern):
    1. Enqueue reminder Notification records atomically in DB with row-locking.
    2. Dispatch pending notifications to Telegram post-commit without holding DB locks.
    """
    now = datetime.now(timezone.utc)
    lead_cutoff = now + timedelta(minutes=REMINDER_LEAD_MINUTES)
    # Lateness rule: pre-session reminders expire 5 minutes after scheduled start time
    expiration_cutoff = now - timedelta(minutes=MAX_REMINDER_LATENESS_MINUTES)
    sent = 0
    from app.db.models.notification import Notification

    # Exclude slots for which a reminder has already been created/committed.
    # This prevents duplicate notifications while ensuring that if a previous worker
    # locked a row and crashed/rolled back before committing, the slot remains eligible for retry!
    reminder_exists = (
        select(Notification.id)
        .where(
            Notification.slot_id == Slot.id,
            Notification.user_id == Slot.reviewer_id,
            Notification.type == "slot_reminder",
        )
        .exists()
    )

    async with AsyncSessionLocal() as db:
        # with_for_update(skip_locked=True) ensures that concurrent workers skip slots
        # currently being processed by another worker without blocking.
        stmt = (
            select(Slot)
            .where(
                Slot.status == SlotStatus.BOOKED.value,
                Slot.start_time <= lead_cutoff,
                Slot.start_time >= expiration_cutoff,
                ~reminder_exists,
            )
            .with_for_update(skip_locked=True)
        )
        slots = (await db.execute(stmt)).scalars().all()
        for slot in slots:
            # Secondary check within transaction
            existing_notif = (await db.execute(
                select(Notification.id).where(
                    Notification.slot_id == slot.id,
                    Notification.user_id == slot.reviewer_id,
                    Notification.type == "slot_reminder",
                )
            )).scalar_one_or_none()
            if existing_notif:
                continue

            try:
                await create_notification(
                    db, slot.reviewer_id, "slot_reminder",
                    "Slot yaqinda boshlanadi", slot_id=slot.id,
                )
                # Reveal the reviewee identity to the reviewer.
                await create_notification(
                    db, slot.reviewer_id, "slot_revealed",
                    "O'rganuvchi ma'lumoti", slot_id=slot.id,
                )
                if slot.reviewee_id:
                    await create_notification(
                        db, slot.reviewee_id, "slot_reminder",
                        "Slot yaqinda boshlanadi", slot_id=slot.id,
                    )
                sent += 1
            except Exception:
                pass
        await db.commit()

    # Stage 2: Dispatch pending Telegram notifications post-commit (Outbox Dispatch)
    # Does NOT hold any Slot row locks during external network calls!
    await _dispatch_pending_telegram_notifications()
    return sent


async def _dispatch_pending_telegram_notifications() -> int:
    """Outbox dispatcher: Deliver pending notifications to Telegram with fencing tokens and bounded retry backoff.

    Guarantees & Architecture:
    1. Phase 1 (Atomic Claiming & Lease Recovery with Fencing Token):
       - Atomically selects up to TELEGRAM_CLAIM_BATCH_SIZE (10) eligible rows using `with_for_update(skip_locked=True)`.
       - Eligible rows:
         * 'pending'
         * 'failed_transient' where telegram_next_retry_at is NULL or <= now
         * 'claimed' where telegram_claimed_at < now - TELEGRAM_LEASE_MINUTES (5m lease expired)
       - Generates a unique batch_claim_token (UUIDv4) acting as a fencing token.
       - Updates telegram_delivery_status='claimed', telegram_claimed_at=now, telegram_claim_token=batch_claim_token,
         and increments telegram_attempts.
       - Validates lateness deadline for time-sensitive notifications (e.g. slot_reminder, slot_revealed):
         if slot.start_time + 5m < now, marks expired locally so stale messages are never sent to Telegram.
       - Commits Phase 1 immediately, releasing all database row locks before any network I/O.
    2. Phase 2 (External HTTP Dispatch):
       - Executes Telegram Bot API HTTP calls outside database transactions without holding locks.
       - Parses response status, permanent failure (400, 403), and rate limit retry_after (429).
    3. Phase 3 (Conditional Atomic Final State Persistence):
       - Uses atomic UPDATE WHERE id = notif_id AND telegram_claim_token = batch_claim_token.
       - If a worker's lease expired and another worker reclaimed the row, telegram_claim_token no longer matches:
         the update matches 0 rows, completely preventing the stale worker from overwriting the newer state!
       - On success: marks telegram_delivery_status='sent' and sent_telegram=True.
       - On permanent failure (no telegram_id, 400, 403, or attempts >= MAX_TELEGRAM_ATTEMPTS):
         marks telegram_delivery_status='failed_permanent', sent_telegram=False (truthful), clearing next_retry.
       - On transient failure (500, timeouts, 429):
         marks telegram_delivery_status='failed_transient', sent_telegram=False (truthful),
         calculates exponential backoff (min(300, 10 * 2^(attempts-1))), respects retry_after if larger,
         and sets telegram_next_retry_at.
    """
    from app.db.models.notification import Notification
    from app.db.models.slot import Slot
    from app.db.models.user import User
    from app.services.telegram_dispatcher import dispatch_notification

    now = datetime.now(timezone.utc)
    lease_cutoff = now - timedelta(minutes=TELEGRAM_LEASE_MINUTES)
    batch_claim_token = uuid.uuid4()

    # Phase 1: Atomic Claim with Fencing Token & Lease Expiration Recovery
    claimed_items: list[dict] = []
    async with AsyncSessionLocal() as db:
        claim_stmt = (
            select(Notification)
            .where(
                or_(
                    Notification.telegram_delivery_status == "pending",
                    and_(
                        Notification.telegram_delivery_status == "failed_transient",
                        or_(
                            Notification.telegram_next_retry_at.is_(None),
                            Notification.telegram_next_retry_at <= now,
                        ),
                    ),
                    and_(
                        Notification.telegram_delivery_status == "claimed",
                        Notification.telegram_claimed_at < lease_cutoff,
                    ),
                ),
                Notification.type.in_([
                    "slot_reminder", "slot_revealed", "slot_cancelled",
                    "absent_given", "slot_booked",
                ]),
            )
            .order_by(Notification.created_at)
            .limit(TELEGRAM_CLAIM_BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        rows = (await db.execute(claim_stmt)).scalars().all()
        if not rows:
            return 0

        for notif in rows:
            claim_attempts = (notif.telegram_claim_attempts or 0) + 1
            notif.telegram_claim_attempts = claim_attempts

            # Claim-exhaustion Quarantine Policy:
            # If a notification has been claimed repeatedly (>= 10 times) without completion,
            # quarantine it explicitly to 'quarantined_claim_exhausted'.
            # A high claim count indicates worker crashes, infrastructure instability, or a
            # poison pill payload, NOT an authoritative delivery rejection from Telegram.
            # Quarantining keeps items observable in admin, prevents infinite worker crash loops,
            # and allows manual operator inspection and re-queueing.
            if claim_attempts >= 10:
                notif.telegram_delivery_status = "quarantined_claim_exhausted"
                notif.sent_telegram = False
                notif.telegram_error = (
                    "claim_attempts_exhausted_quarantine: notification claimed 10 times "
                    "without completion; quarantined for operator review to prevent worker crash loops"
                )
                notif.telegram_claim_token = None
                notif.telegram_claimed_at = None
                notif.telegram_next_retry_at = None
                continue

            notif.telegram_delivery_status = "claimed"
            notif.telegram_claimed_at = now
            notif.telegram_claim_token = batch_claim_token
            # Note: notif.telegram_attempts is NOT incremented here.
            # telegram_attempts strictly records actual HTTP dispatch attempts.

            user = await db.get(User, notif.user_id)
            slot = await db.get(Slot, notif.slot_id) if notif.slot_id else None

            # Preflight check: Lateness deadline check for time-sensitive notifications
            is_expired = False
            if notif.type in ("slot_reminder", "slot_revealed") and slot and slot.start_time:
                # If slot started more than 5 minutes ago, it has passed the lateness deadline
                if now > (slot.start_time + timedelta(minutes=MAX_REMINDER_LATENESS_MINUTES)):
                    is_expired = True

            claimed_items.append({
                "notif_id": notif.id,
                "telegram_id": user.telegram_id if user else None,
                "title": notif.title,
                "body": notif.body,
                "current_attempts": notif.telegram_attempts or 0,
                "is_expired": is_expired,
            })
        await db.commit()

    # Phase 2: External HTTP calls (ZERO database transactions or row locks held)
    results: list[dict] = []
    for item in claimed_items:
        notif_id = item["notif_id"]
        current_attempts = item["current_attempts"]
        if item["is_expired"]:
            results.append({
                "notif_id": notif_id,
                "success": False,
                "permanent_fail": True,
                "error": "expired_past_lateness_deadline",
                "retry_after": None,
                "http_attempted": False,
                "current_attempts": current_attempts,
            })
            continue

        telegram_id = item["telegram_id"]
        if not telegram_id:
            results.append({
                "notif_id": notif_id,
                "success": False,
                "permanent_fail": True,
                "error": "missing_telegram_id",
                "retry_after": None,
                "http_attempted": False,
                "current_attempts": current_attempts,
            })
            continue

        dispatch_res = await dispatch_notification(
            telegram_id=telegram_id,
            title=item["title"],
            body=item["body"],
        )
        if len(dispatch_res) >= 4:
            success, permanent_fail, err_msg, retry_after = dispatch_res[:4]
        else:
            success, permanent_fail = dispatch_res[:2]
            err_msg = None if success else ("blocked_or_rejected" if permanent_fail else "transient_network_error")
            retry_after = None

        results.append({
            "notif_id": notif_id,
            "success": success,
            "permanent_fail": permanent_fail,
            "error": err_msg,
            "retry_after": retry_after,
            "http_attempted": True,
            "current_attempts": current_attempts,
        })

    # Phase 3: Final state persistence with Fencing Token (Conditional Atomic Update)
    dispatched = 0
    async with AsyncSessionLocal() as db:
        for res in results:
            notif_id = res["notif_id"]
            success = res["success"]
            perm_fail = res["permanent_fail"]
            err = res["error"]
            retry_after = res["retry_after"]
            http_attempted = res["http_attempted"]
            current_attempts = res["current_attempts"]

            new_attempts = current_attempts + 1 if http_attempted else current_attempts

            if success:
                final_status = "sent"
                is_sent = True
                final_err = None
                next_retry = None
                dispatched += 1
            elif perm_fail or new_attempts >= MAX_TELEGRAM_ATTEMPTS:
                final_status = "failed_permanent"
                is_sent = False
                final_err = (
                    f"max_attempts_exceeded ({new_attempts}/{MAX_TELEGRAM_ATTEMPTS}): {err}"
                    if new_attempts >= MAX_TELEGRAM_ATTEMPTS and not perm_fail
                    else err
                )
                next_retry = None
            else:
                # Transient error: calculate exponential backoff with retry_after respect
                final_status = "failed_transient"
                is_sent = False
                final_err = err or "transient_network_error"
                # Backoff: 10 * 2^(new_attempts-1), capped at 300s (5 min)
                backoff_secs = min(300, 10 * (2 ** max(0, new_attempts - 1)))
                if retry_after:
                    backoff_secs = max(backoff_secs, retry_after)
                next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff_secs)

            # Atomic conditional update using claim_token fencing:
            # If lease expired and another worker reclaimed this row,
            # telegram_claim_token will no longer match batch_claim_token.
            # In that case, this update affects 0 rows, preventing state stomping!
            stmt = (
                update(Notification)
                .where(
                    Notification.id == notif_id,
                    Notification.telegram_claim_token == batch_claim_token,
                )
                .values(
                    telegram_delivery_status=final_status,
                    sent_telegram=is_sent,
                    telegram_attempts=new_attempts,
                    telegram_error=final_err,
                    telegram_next_retry_at=next_retry,
                    telegram_claim_token=None,
                    telegram_claimed_at=None,
                )
            )
            update_res = await db.execute(stmt)
            # Update in-memory object if present in session for testing/introspection parity
            local_notif = await db.get(Notification, notif_id)
            if local_notif and getattr(update_res, "rowcount", 1) != 0:
                local_notif.telegram_delivery_status = final_status
                local_notif.sent_telegram = is_sent
                local_notif.telegram_attempts = new_attempts
                local_notif.telegram_error = final_err
                local_notif.telegram_next_retry_at = next_retry
                local_notif.telegram_claim_token = None
                local_notif.telegram_claimed_at = None

        await db.commit()

    return dispatched


@celery_app.task(name="app.tasks.slot_tasks.dispatch_telegram_notifications")
def dispatch_telegram_notifications() -> int:
    return run_async(_dispatch_pending_telegram_notifications())


@celery_app.task(name="app.tasks.slot_tasks.check_absences")
def check_absences() -> int:
    return run_async(_check_absences())


async def _check_absences() -> int:
    """Placeholder hook: absences are user-driven, this surfaces stale slots."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=ABSENT_GRACE_MINUTES)
    async with AsyncSessionLocal() as db:
        stmt = select(Slot).where(
            Slot.status == SlotStatus.BOOKED.value,
            Slot.start_time < threshold,
        )
        slots = (await db.execute(stmt)).scalars().all()
        return len(slots)
