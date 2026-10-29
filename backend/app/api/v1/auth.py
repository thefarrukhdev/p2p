"""Auth endpoints.

Oqim:
1. POST /login — S21 login/parol. Agar telegram bog'langan → JWT.
   Agar telegram yo'q → 202 {need_telegram: true, temp_token}
2. POST /verify-code — OTP code + temp_token → telegram tasdiqlash → JWT
3. POST /refresh — JWT refresh
4. POST /logout — is_logged_in = False
5. GET /me — joriy foydalanuvchi
"""
from __future__ import annotations

import logging
import secrets
import uuid

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_token,
)
from app.db.models.user import User
from app.schemas.auth import RefreshRequest, TokenResponse
from app.schemas.user import UserMe
from app.services.cache import redis_client
from app.services.school21_client import detect_main_track, school21_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

OTP_TTL = 300  # 5 daqiqa
OTP_PREFIX = "otp:"
TEMP_TOKEN_PREFIX = "temp:"
TEMP_TOKEN_TTL = 600  # 10 daqiqa


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    login: str
    password: str


class VerifyCodeRequest(BaseModel):
    temp_token: str
    code: str


class LoginResponse(BaseModel):
    status: str  # "ok" | "need_telegram"
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    onboarding_done: bool = False
    temp_token: str | None = None  # need_telegram bo'lganda
    bot_url: str | None = None  # botga o'tish havolasi


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/15minutes")
async def login(request: Request, payload: LoginRequest, db: DbSession):
    """School21 login. Telegram bog'langan bo'lsa → JWT. Aks holda → need_telegram."""

    # 1. School21 autentifikatsiya
    try:
        token_data = await school21_client.login(payload.login, payload.password)
    except httpx.HTTPStatusError as exc:
        logger.warning("S21 auth %s: %s", exc.response.status_code, exc.response.text[:100])
        if exc.response.status_code in (400, 401):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login yoki parol noto'g'ri")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"School21 xatosi: {exc.response.status_code}")
    except Exception as exc:
        logger.error("S21 error: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "School21 ga ulanib bo'lmadi")

    s21_token = token_data.get("access_token", "")
    if not s21_token:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Token topilmadi")

    # 2. DB dan foydalanuvchini qidirish
    user = (await db.execute(
        select(User).where(User.school21_login == payload.login)
    )).scalar_one_or_none()

    # 3. Yangi foydalanuvchi — yaratamiz (telegram_id yo'q)
    if user is None:
        profile = await school21_client.get_profile(s21_token, payload.login)
        user = User(school21_login=payload.login, peer_points=5)
        db.add(user)
        user.school21_token_enc = encrypt_token(s21_token)
        campus_raw = profile.get("campus")
        if isinstance(campus_raw, dict):
            user.campus = campus_raw.get("shortName")
        elif isinstance(campus_raw, str):
            user.campus = campus_raw
        if profile.get("className"):
            user.core_program = profile["className"]
        try:
            finished = await school21_client.get_projects(s21_token, login=payload.login)
            user.main_track = detect_main_track(finished)
        except Exception:
            pass
        try:
            c = await school21_client.get_coalition(s21_token, payload.login)
            user.coalition_name = c.get("name")
        except Exception:
            pass
        await db.commit()
        await db.refresh(user)

    # 4. Token yangilash (har loginida fresh token saqlaymiz)
    user.school21_token_enc = encrypt_token(s21_token)

    # 5. Har loginida profil ma'lumotlarini yangilash
    try:
        profile = await school21_client.get_profile(s21_token, payload.login)
        campus_raw = profile.get("campus")
        if isinstance(campus_raw, dict):
            user.campus = campus_raw.get("shortName") or user.campus
        elif isinstance(campus_raw, str) and campus_raw:
            user.campus = campus_raw
        if profile.get("className"):
            user.core_program = profile["className"]
    except Exception:
        pass
    try:
        all_projects = await school21_client.get_projects(s21_token, login=payload.login)
        track = detect_main_track(all_projects)
        if track:
            user.main_track = track
    except Exception:
        pass
    try:
        c = await school21_client.get_coalition(s21_token, payload.login)
        if c.get("name"):
            user.coalition_name = c["name"]
    except Exception:
        pass
    try:
        w = await school21_client.get_location(s21_token, payload.login)
        if w.get("formatted"):
            user.current_location = w["formatted"]
    except Exception:
        pass

    # 5. Telegram bog'langanmi tekshirish
    if user.telegram_id:
        # Telegram bor → to'g'ridan-to'g'ri JWT
        user.is_logged_in = True
        await db.commit()
        tokens = _issue_tokens(user)
        return LoginResponse(
            status="ok",
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            onboarding_done=user.onboarding_done,
        )
    else:
        # Telegram yo'q → temp_token berish, frontend botga yo'naltiradi
        await db.commit()
        temp_token = secrets.token_urlsafe(32)
        await redis_client.setex(
            f"{TEMP_TOKEN_PREFIX}{temp_token}",
            TEMP_TOKEN_TTL,
            str(user.id),
        )
        from app.core.config import settings
        bot_token = settings.TELEGRAM_BOT_TOKEN
        bot_username = ""
        if bot_token:
            # Bot username olish (cached)
            cached = await redis_client.get("bot:username")
            if cached:
                bot_username = cached
            else:
                try:
                    import httpx as hx
                    async with hx.AsyncClient() as c:
                        r = await c.get(f"https://api.telegram.org/bot{bot_token}/getMe")
                        bot_username = r.json().get("result", {}).get("username", "")
                        if bot_username:
                            await redis_client.setex("bot:username", 3600, bot_username)
                except Exception:
                    pass

        return LoginResponse(
            status="need_telegram",
            temp_token=temp_token,
            bot_url=f"https://t.me/{bot_username}?start={temp_token}" if bot_username else None,
            onboarding_done=user.onboarding_done,
        )


@router.post("/verify-code", response_model=TokenResponse)
@limiter.limit("10/minute")
async def verify_code(request: Request, payload: VerifyCodeRequest, db: DbSession):
    """OTP kodni tekshirish — telegram_id ulash va JWT berish."""

    # 1. temp_token dan user_id olish
    user_id_str = await redis_client.get(f"{TEMP_TOKEN_PREFIX}{payload.temp_token}")
    if not user_id_str:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Temp token yaroqsiz yoki muddati o'tgan")

    # 2. OTP kodni tekshirish
    otp_key = f"{OTP_PREFIX}{user_id_str}"
    stored = await redis_client.get(otp_key)
    if not stored:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kod topilmadi. Botdan yangi kod oling.")

    # stored format: "code:telegram_id"
    parts = stored.split(":")
    if len(parts) != 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Xato format")

    expected_code, telegram_id_str = parts
    if payload.code != expected_code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kod noto'g'ri")

    # 3. telegram_id ni user ga ulash
    user = await db.get(User, uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")

    # Tekshirish: bu telegram_id boshqa userga bog'langanmi?
    telegram_id = int(telegram_id_str)
    existing = (await db.execute(
        select(User).where(User.telegram_id == telegram_id, User.id != user.id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Bu Telegram akkaunt allaqachon '{existing.school21_login}' ga bog'langan"
        )

    user.telegram_id = telegram_id
    user.is_logged_in = True
    await db.commit()

    # 4. Redis tozalash
    await redis_client.delete(otp_key)
    await redis_client.delete(f"{TEMP_TOKEN_PREFIX}{payload.temp_token}")

    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession):
    data = decode_token(payload.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = await db.get(User, uuid.UUID(data["sub"]))
    if user is None or not user.is_active or not user.is_logged_in:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found, inactive or logged out")
    return _issue_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser, db: DbSession):
    user.is_logged_in = False
    await db.commit()
    from app.ws.manager import manager
    await manager.revoke_user(user.id)
    return None


class RelinkTelegramRequest(BaseModel):
    password: str  # S21 parolni tasdiqlash kerak


@router.post("/unlink-telegram", status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def unlink_telegram(request: Request, payload: RelinkTelegramRequest, user: CurrentUser, db: DbSession):
    """Telegram akkauntni uzish (qayta bog'lash uchun).

    S21 parolni tasdiqlash talab qilinadi — xavfsizlik uchun.
    Unlink qilgandan keyin foydalanuvchi yangi Telegram bilan /login → bot oqimini o'taydi.
    """
    # S21 parolni tekshirish
    try:
        await school21_client.login(user.school21_login, payload.password)
    except httpx.HTTPStatusError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Parol noto'g'ri")
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "School21 ga ulanib bo'lmadi")

    # Telegram uzish
    user.telegram_id = None
    user.telegram_username = None
    user.is_logged_in = False
    await db.commit()

    return {"status": "ok", "message": "Telegram akkaunt uzildi. Yangi Telegram bilan login qiling."}


@router.get("/me", response_model=UserMe)
async def me(user: CurrentUser):
    return user


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue_tokens(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject, {"admin": user.is_admin}),
        refresh_token=create_refresh_token(subject),
        onboarding_done=user.onboarding_done,
    )
