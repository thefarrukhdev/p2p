"""Slot endpoints."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, select

from app.core.dependencies import CurrentUser, DbSession
from app.db.models.slot import Slot
from app.schemas.slot import (
    SlotBook,
    SlotCancel,
    SlotCreate,
    SlotOut,
    SlotSearchResult,
)
from app.services import slot_service
from app.services.matching_service import find_matching_slots

router = APIRouter(prefix="/slots", tags=["slots"])


async def _get_slot_or_404(db: DbSession, slot_id: uuid.UUID) -> Slot:
    slot = await db.get(Slot, slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found"
        )
    return slot


@router.post("/", response_model=SlotOut, status_code=status.HTTP_201_CREATED)
async def create_slot(payload: SlotCreate, user: CurrentUser, db: DbSession):
    if user.campus is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User campus unknown"
        )
    slot = await slot_service.create_slot(
        db,
        user,
        reviewer_project=payload.reviewer_project,
        start_time=payload.start_time,
        end_time=payload.end_time,
        campus=user.campus,
        is_online=payload.is_online,
    )
    await db.commit()
    await db.refresh(slot)
    return slot


@router.get("/", response_model=list[SlotOut])
async def list_slots(
    user: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    on_date: date | None = Query(None, alias="date"),
):
    from sqlalchemy import or_

    stmt = select(Slot).where(
        or_(Slot.reviewer_id == user.id, Slot.reviewee_id == user.id)
    )
    if status_filter:
        stmt = stmt.where(Slot.status == status_filter)
    if on_date:
        day_start = datetime.combine(on_date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(on_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(
            and_(Slot.start_time >= day_start, Slot.start_time <= day_end)
        )
    stmt = stmt.order_by(Slot.start_time.asc())
    return (await db.execute(stmt)).scalars().all()


@router.get("/search", response_model=list[SlotSearchResult])
async def search_slots(
    user: CurrentUser,
    db: DbSession,
    project: str = Query(...),
):
    if user.campus is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User campus unknown"
        )
    slots = await find_matching_slots(
        db,
        selected_project=project,
        user_campus=user.campus,
        user_languages=user.languages or [],
    )
    return [SlotSearchResult.model_validate(s, from_attributes=True) for s in slots]


@router.get("/{slot_id}", response_model=SlotOut)
async def get_slot(slot_id: uuid.UUID, user: CurrentUser, db: DbSession):
    slot = await _get_slot_or_404(db, slot_id)
    if not (slot.reviewer_id == user.id or slot.reviewee_id == user.id or user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this slot",
        )
    return slot


@router.delete("/{slot_id}", response_model=SlotOut)
async def cancel_slot(
    slot_id: uuid.UUID, payload: SlotCancel, user: CurrentUser, db: DbSession
):
    slot = await _get_slot_or_404(db, slot_id)
    slot = await slot_service.cancel_slot(db, slot, user, payload.reason)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.post("/{slot_id}/book", response_model=SlotOut)
async def book_slot(
    slot_id: uuid.UUID, payload: SlotBook, user: CurrentUser, db: DbSession
):
    slot = await _get_slot_or_404(db, slot_id)
    slot = await slot_service.book_slot(db, slot, user, payload.reviewee_project)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.post("/{slot_id}/start", response_model=SlotOut)
async def start_slot(slot_id: uuid.UUID, user: CurrentUser, db: DbSession):
    slot = await _get_slot_or_404(db, slot_id)
    slot = await slot_service.start_slot(db, slot, user)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.post("/{slot_id}/finish", response_model=SlotOut)
async def finish_slot(slot_id: uuid.UUID, user: CurrentUser, db: DbSession):
    slot = await _get_slot_or_404(db, slot_id)
    slot = await slot_service.finish_slot(db, slot, user)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.post("/{slot_id}/absent", response_model=SlotOut)
async def absent_slot(slot_id: uuid.UUID, user: CurrentUser, db: DbSession):
    slot = await _get_slot_or_404(db, slot_id)
    slot = await slot_service.mark_absent(db, slot, user)
    await db.commit()
    await db.refresh(slot)
    return slot


# ── School21 loyihalar (slot yaratish/qidirish uchun) ─────────────────────────

@router.get("/my/teachable-projects")
async def teachable_projects(user: CurrentUser):
    """O'rgatish mumkin bo'lgan loyihalar — faqat tugatilganlar (ACCEPTED).

    Slot yaratishda foydalanuvchi shu ro'yxatdan tanlaydi.
    """
    from app.core.security import decrypt_token
    from app.services.school21_client import school21_client

    if not user.school21_token_enc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "School21 token yo'q")
    token = decrypt_token(user.school21_token_enc)
    projects = await school21_client.get_projects(token, login=user.school21_login)
    # Faqat ACCEPTED (tugatilgan) loyihalar
    accepted = [
        {"title": p["title"], "id": p.get("id")}
        for p in projects
        if p.get("status") == "ACCEPTED" and p.get("title")
    ]
    return {"projects": accepted}


@router.get("/my/in-progress-projects")
async def in_progress_projects(user: CurrentUser):
    """O'rganuvchining hozir davom etayotgan loyihalari (IN_PROGRESS).

    Slot qidirishda foydalanuvchi shu ro'yxatdan tanlaydi.
    """
    from app.core.security import decrypt_token
    from app.services.school21_client import school21_client

    if not user.school21_token_enc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "School21 token yo'q")
    token = decrypt_token(user.school21_token_enc)
    projects = await school21_client.get_projects(token, login=user.school21_login)
    # IN_PROGRESS loyihalar
    in_progress = [
        {"title": p["title"], "id": p.get("id")}
        for p in projects
        if p.get("status") == "IN_PROGRESS" and p.get("title")
    ]
    return {"projects": in_progress}
