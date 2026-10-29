"""Admin REST endpoints (separate from SQLAdmin UI). Requires is_admin."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.dependencies import CurrentAdmin, DbSession
from app.db.models.notification import Notification
from app.db.models.review import Review
from app.db.models.slot import Slot, SlotStatus
from app.db.models.user import User
from app.schemas.slot import SlotOut
from app.schemas.user import UserMe
from app.services import points_service, xp_service
from app.services.notification_service import (
    create_notification,
    requeue_quarantined_notification,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class AdjustXp(BaseModel):
    user_id: uuid.UUID
    amount: int


class AdjustPoints(BaseModel):
    user_id: uuid.UUID
    points: int = 0
    coins: int = 0


class NotifyRequest(BaseModel):
    user_id: uuid.UUID | None = None  # None => broadcast
    title: str
    body: str


async def _get_user_or_404(db: DbSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/users", response_model=list[UserMe])
async def list_users(
    admin: CurrentAdmin,
    db: DbSession,
    q: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(User)
    if q:
        stmt = stmt.where(User.school21_login.ilike(f"%{q}%"))
    stmt = stmt.limit(limit).offset(offset)
    return (await db.execute(stmt)).scalars().all()


@router.get("/users/{user_id}", response_model=UserMe)
async def get_user(user_id: uuid.UUID, admin: CurrentAdmin, db: DbSession):
    return await _get_user_or_404(db, user_id)


@router.post("/users/{user_id}/block", response_model=UserMe)
async def block_user(user_id: uuid.UUID, admin: CurrentAdmin, db: DbSession):
    user = await _get_user_or_404(db, user_id)
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    if not user.is_active:
        from app.ws.manager import manager
        await manager.revoke_user(user.id)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, admin: CurrentAdmin, db: DbSession):
    user = await _get_user_or_404(db, user_id)
    from app.ws.manager import manager
    await manager.revoke_user(user.id)
    # Check if user has relational dependencies to prevent Foreign Key Constraint errors
    # (Slot, Review, XpLog, Notification, LeaderboardSnapshot)
    from sqlalchemy import or_
    from app.db.models.review import Review
    from app.db.models.xp_log import XpLog
    from app.db.models.notification import Notification
    from app.db.models.leaderboard_snapshot import LeaderboardSnapshot

    has_slots = (await db.execute(
        select(Slot.id).where(or_(Slot.reviewer_id == user.id, Slot.reviewee_id == user.id))
    )).scalars().first()
    has_reviews = (await db.execute(
        select(Review.id).where(or_(Review.author_id == user.id, Review.target_id == user.id))
    )).scalars().first()
    has_xp = (await db.execute(
        select(XpLog.id).where(XpLog.user_id == user.id)
    )).scalars().first()
    has_notifs = (await db.execute(
        select(Notification.id).where(Notification.user_id == user.id)
    )).scalars().first()
    has_snaps = (await db.execute(
        select(LeaderboardSnapshot.id).where(LeaderboardSnapshot.user_id == user.id)
    )).scalars().first()

    if has_slots or has_reviews or has_xp or has_notifs or has_snaps:
        # User has historical dependencies; deactivate instead of hard delete to preserve FK integrity
        user.is_active = False
        user.is_logged_in = False
        await db.commit()
        return None

    await db.delete(user)
    await db.commit()
    return None


@router.get("/slots", response_model=list[SlotOut])
async def list_slots(
    admin: CurrentAdmin,
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Slot)
    if status_filter:
        stmt = stmt.where(Slot.status == status_filter)
    stmt = stmt.order_by(Slot.start_time.desc()).limit(limit).offset(offset)
    return (await db.execute(stmt)).scalars().all()


@router.post("/slots/{slot_id}/resolve", response_model=SlotOut)
async def resolve_slot(slot_id: uuid.UUID, admin: CurrentAdmin, db: DbSession):
    """Resolve a dispute: refund booking point to the reviewee atomically with row locking."""
    # 1. Lock slot row in DB to prevent concurrent resolution races
    slot_stmt = (
        select(Slot)
        .where(Slot.id == slot_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    slot = (await db.execute(slot_stmt)).scalar_one_or_none()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found"
        )
    if slot.status in (SlotStatus.COMPLETED.value, SlotStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slot cannot be resolved in its current state ({slot.status})",
        )

    try:
        if slot.reviewee_id:
            # 2. Lock reviewee row to prevent concurrent balance mutations
            user_stmt = (
                select(User)
                .where(User.id == slot.reviewee_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            reviewee = (await db.execute(user_stmt)).scalar_one_or_none()
            if reviewee:
                points_service.add_peer_points(reviewee, 1)

        slot.status = SlotStatus.CANCELLED.value
        await db.commit()
        await db.refresh(slot)
        return slot
    except Exception:
        await db.rollback()
        raise


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: uuid.UUID, admin: CurrentAdmin, db: DbSession):
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    await db.delete(review)
    await db.commit()
    return None


@router.post("/adjust-xp", response_model=UserMe)
async def adjust_xp(payload: AdjustXp, admin: CurrentAdmin, db: DbSession):
    user = await _get_user_or_404(db, payload.user_id)
    await xp_service.apply_xp(db, user, payload.amount, "admin_adjust")
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/adjust-points", response_model=UserMe)
async def adjust_points(payload: AdjustPoints, admin: CurrentAdmin, db: DbSession):
    user = await _get_user_or_404(db, payload.user_id)
    if payload.points:
        points_service.add_peer_points(user, payload.points)
    if payload.coins:
        points_service.add_peer_coins(user, payload.coins)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/notify", status_code=status.HTTP_202_ACCEPTED)
async def notify(payload: NotifyRequest, admin: CurrentAdmin, db: DbSession):
    if payload.user_id:
        await create_notification(
            db, payload.user_id, "system", payload.title, payload.body
        )
    else:
        users = (await db.execute(select(User.id))).scalars().all()
        for uid in users:
            await create_notification(db, uid, "system", payload.title, payload.body)
    await db.commit()
    return {"status": "queued"}


@router.get("/stats")
async def stats(admin: CurrentAdmin, db: DbSession):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_slots = (await db.execute(select(func.count(Slot.id)))).scalar_one()
    completed = (
        await db.execute(
            select(func.count(Slot.id)).where(
                Slot.status == SlotStatus.COMPLETED.value
            )
        )
    ).scalar_one()
    avg_duration = (
        await db.execute(
            select(func.avg(Slot.duration_minutes)).where(
                Slot.duration_minutes.isnot(None)
            )
        )
    ).scalar_one()
    return {
        "total_users": total_users,
        "total_slots": total_slots,
        "completed_slots": completed,
        "avg_duration_minutes": float(avg_duration) if avg_duration else 0.0,
    }


@router.get("/quarantined-notifications")
async def list_quarantined_notifications(
    admin: CurrentAdmin,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
):
    stmt = (
        select(Notification)
        .where(Notification.telegram_delivery_status == "quarantined_claim_exhausted")
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    items = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(notif.id),
            "user_id": str(notif.user_id),
            "type": notif.type,
            "title": notif.title,
            "claim_attempts": notif.telegram_claim_attempts,
            "attempts": notif.telegram_attempts,
            "error": notif.telegram_error,
            "created_at": notif.created_at.isoformat() if notif.created_at else None,
        }
        for notif in items
    ]


@router.post("/quarantined-notifications/{notification_id}/retry")
async def retry_quarantined_notification(
    notification_id: uuid.UUID,
    admin: CurrentAdmin,
    db: DbSession,
):
    notif, err_code = await requeue_quarantined_notification(db, notification_id)
    if notif is None:
        if err_code == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        elif err_code and err_code.startswith("invalid_state:"):
            current_st = err_code.split(":", 1)[1]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Notification is in '{current_st}' status, only 'quarantined_claim_exhausted' can be retried",
            )
        elif err_code == "missing_telegram_id":
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient user does not have a linked Telegram account",
            )
        elif err_code == "expired_past_lateness_deadline":
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot retry time-sensitive reminder past its 5-minute lateness deadline",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot retry quarantined notification: {err_code}",
            )
    await db.commit()
    return {
        "status": "requeued",
        "notification_id": str(notif.id),
        "delivery_status": notif.telegram_delivery_status,
        "claim_attempts": notif.telegram_claim_attempts,
        "attempts": notif.telegram_attempts,
        "audit_note": notif.telegram_error,
    }
