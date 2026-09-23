"""User / profile schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    """Public-facing profile (other users)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school21_login: str
    telegram_username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    campus: str | None = None
    core_program: str | None = None
    main_track: str | None = None
    coalition_name: str | None = None
    level: int
    xp: int


class UserMe(UserPublic):
    """Full profile for the authenticated user."""

    email: str | None = None
    current_location: str | None = None
    peer_points: int
    peer_coins: int
    languages: list[str]
    is_admin: bool
    onboarding_done: bool


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
