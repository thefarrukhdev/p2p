"""Slot schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SlotCreate(BaseModel):
    reviewer_project: str
    start_time: datetime
    end_time: datetime
    is_online: bool = False


class SlotBook(BaseModel):
    reviewee_project: str | None = None


class SlotCancel(BaseModel):
    reason: str | None = None


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewee_id: uuid.UUID | None = None
    reviewer_project: str
    reviewee_project: str | None = None
    start_time: datetime
    end_time: datetime
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    reviewer_started: bool = False
    reviewee_started: bool = False
    duration_minutes: int | None = None
    status: str
    is_online: bool
    campus: str


class SlotSearchResult(BaseModel):
    """Anonymous search result — owner identity hidden until reveal."""

    id: uuid.UUID
    start_time: datetime
    end_time: datetime
    campus: str
    is_online: bool
