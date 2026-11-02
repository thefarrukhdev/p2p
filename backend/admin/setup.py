"""SQLAdmin panel — JWT-based authentication.

Faqat is_admin=True bo'lgan foydalanuvchilar admin panelga kira oladi.
"""
from __future__ import annotations

import secrets

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.core.security import create_access_token, decode_token
from app.db.base import AsyncSessionLocal, engine
from app.db.models.leaderboard_snapshot import LeaderboardSnapshot
from app.db.models.notification import Notification
from app.db.models.review import Review
from app.db.models.slot import Slot
from app.db.models.user import User
from app.db.models.xp_log import XpLog
from app.db.models.bot_settings import BotSettings
from app.db.models.required_channel import RequiredChannel


class AdminAuth(AuthenticationBackend):
    """SQLAdmin auth backend — admin JWT token asosida."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        login = str(form.get("username", "") or "").strip()
        password = str(form.get("password", "") or "").strip()

        if not login or not password:
            return False

        # Insecure default credentials MUST be rejected unconditionally
        if login.lower() == "admin" and password == "admin123":
            return False

        # 1. Break-glass admin credential ONLY if explicitly configured with high entropy
        configured_admin_user = (getattr(settings, "ADMIN_USERNAME", "") or "").strip()
        configured_admin_pass = (getattr(settings, "ADMIN_PASSWORD", "") or "").strip()

        INSECURE_CREDS = {
            ("admin", "admin123"),
            ("admin", "admin"),
            ("superadmin", "superadmin"),
            ("root", "root"),
        }

        if (
            configured_admin_user
            and configured_admin_pass
            and (configured_admin_user.lower(), configured_admin_pass) not in INSECURE_CREDS
            and len(configured_admin_pass) >= 12
        ):
            if secrets.compare_digest(login, configured_admin_user) and secrets.compare_digest(password, configured_admin_pass):
                token = create_access_token("superadmin", {"admin": True, "sub": "superadmin"})
                request.session.update({"admin_token": token})
                return True

        # 2. Database administrator authentication via School21
        from app.services.school21_client import school21_client
        import httpx

        try:
            await school21_client.start()
            await school21_client.login(login, password)
        except (httpx.HTTPStatusError, Exception):
            return False

        # DB dan is_active va is_admin tekshirish
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            user = (
                await db.execute(select(User).where(User.school21_login == login))
            ).scalar_one_or_none()
            if user is None or not user.is_active or not user.is_admin:
                return False

        # Session da JWT token saqlash
        token = create_access_token(str(user.id), {"admin": True, "sub": str(user.id)})
        request.session.update({"admin_token": token})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | bool:
        token = request.session.get("admin_token")
        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        payload = decode_token(token)
        if payload is None or not payload.get("admin"):
            request.session.clear()
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        sub = payload.get("sub")
        if not sub:
            request.session.clear()
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        # Enforce active-user and admin authorization check
        if sub == "superadmin":
            configured_admin_user = (getattr(settings, "ADMIN_USERNAME", "") or "").strip()
            configured_admin_pass = (getattr(settings, "ADMIN_PASSWORD", "") or "").strip()
            if not configured_admin_user or not configured_admin_pass or len(configured_admin_pass) < 12:
                request.session.clear()
                return RedirectResponse(request.url_for("admin:login"), status_code=302)
        else:
            try:
                import uuid
                user_uuid = uuid.UUID(sub)
                async with AsyncSessionLocal() as db:
                    user = await db.get(User, user_uuid)
                    if user is None or not user.is_active or not user.is_admin:
                        request.session.clear()
                        return RedirectResponse(request.url_for("admin:login"), status_code=302)
            except Exception:
                request.session.clear()
                return RedirectResponse(request.url_for("admin:login"), status_code=302)

        return True


# ── ModelView lar ────────────────────────────────────────────────────────────

class UserAdmin(ModelView, model=User):
    column_list = [
        User.id, User.school21_login, User.telegram_username,
        User.campus, User.level, User.xp, User.peer_points,
        User.peer_coins, User.is_active, User.is_admin, User.is_logged_in,
    ]
    # school21_token_enc form da ko'rinmasin (xavfsizlik)
    form_excluded_columns = [User.school21_token_enc]
    column_searchable_list = [User.school21_login, User.telegram_username]
    column_sortable_list = [User.xp, User.level, User.created_at]
    name = "User"
    name_plural = "Users"


class SlotAdmin(ModelView, model=Slot):
    column_list = [
        Slot.id, Slot.reviewer_id, Slot.reviewee_id,
        Slot.reviewer_project, Slot.status, Slot.campus,
        Slot.is_online, Slot.start_time,
    ]
    column_sortable_list = [Slot.start_time, Slot.status]


class ReviewAdmin(ModelView, model=Review):
    column_list = [Review.id, Review.slot_id, Review.author_id, Review.is_positive]


class NotificationAdmin(ModelView, model=Notification):
    column_list = [
        Notification.id, Notification.user_id, Notification.type,
        Notification.is_read, Notification.sent_telegram,
        Notification.telegram_delivery_status,
        Notification.telegram_claim_attempts, Notification.telegram_attempts,
        Notification.telegram_next_retry_at, Notification.telegram_error,
    ]


class XpLogAdmin(ModelView, model=XpLog):
    column_list = [XpLog.id, XpLog.user_id, XpLog.amount, XpLog.reason, XpLog.created_at]


class LeaderboardSnapshotAdmin(ModelView, model=LeaderboardSnapshot):
    column_list = [
        LeaderboardSnapshot.id, LeaderboardSnapshot.month,
        LeaderboardSnapshot.category, LeaderboardSnapshot.rank,
        LeaderboardSnapshot.value,
    ]


class BotSettingsAdmin(ModelView, model=BotSettings):
    column_list = [
        BotSettings.id, BotSettings.subscription_enabled,
        BotSettings.webapp_url, BotSettings.maintenance_mode,
    ]
    name = "Bot Settings"
    name_plural = "Bot Settings"


class RequiredChannelAdmin(ModelView, model=RequiredChannel):
    column_list = [
        RequiredChannel.id, RequiredChannel.channel_id, RequiredChannel.title,
        RequiredChannel.is_active, RequiredChannel.invite_link,
    ]
    column_searchable_list = [RequiredChannel.title, RequiredChannel.channel_id]
    name = "Required Channel"
    name_plural = "Required Channels"


def init_admin(app: FastAPI) -> Admin:
    auth_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app, engine,
        title="P2P Admin",
        authentication_backend=auth_backend,
    )
    admin.add_view(UserAdmin)
    admin.add_view(SlotAdmin)
    admin.add_view(ReviewAdmin)
    admin.add_view(NotificationAdmin)
    admin.add_view(XpLogAdmin)
    admin.add_view(LeaderboardSnapshotAdmin)
    admin.add_view(BotSettingsAdmin)
    admin.add_view(RequiredChannelAdmin)
    return admin
