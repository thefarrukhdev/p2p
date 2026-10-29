"""Aggregate all v1 routers under /api/v1."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    dashboard,
    diagnostics,
    leaderboard,
    notifications,
    onboarding,
    profile,
    reviews,
    settings,
    slots,
    webhooks,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(dashboard.router)
api_router.include_router(slots.router)
api_router.include_router(reviews.router)
api_router.include_router(leaderboard.router)
api_router.include_router(profile.router)
api_router.include_router(settings.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(webhooks.router)
api_router.include_router(diagnostics.router)
