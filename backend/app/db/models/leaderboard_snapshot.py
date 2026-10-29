"""LeaderboardSnapshot model — monthly historical ranks."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class LeaderboardSnapshot(Base, TimestampMixin):
    __tablename__ = "leaderboard_snapshots"
    __table_args__ = (
        Index("ix_leaderboard_month_category", "month", "category"),
        UniqueConstraint("month", "category", "user_id", name="uq_leaderboard_month_cat_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
