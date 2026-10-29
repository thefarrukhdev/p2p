"""WebSocket endpoint for live slot sessions."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.db.base import AsyncSessionLocal
from app.db.models.slot import Slot
from app.db.models.user import User
from app.services import slot_service
from app.services.cache import redis_client
from app.ws.manager import manager

router = APIRouter()


async def _authenticate(token: str | None) -> User | None:
    if not token:
        return None
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        return user if user and user.is_active and user.is_logged_in else None


@router.websocket("/ws/slots")
async def slots_feed_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """Global real-time feed — foydalanuvchi kanaliga (`user:{id}`) ulanadi.

    Slot yangilanishlari / bildirishnomalar shu kanalga publish qilinsa,
    frontend darhol qabul qiladi. Hozircha ulanish ochiq turadi (xatosiz).
    """
    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    channel = f"user:{user.id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    async def _forward() -> None:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                await websocket.send_text(message["data"])

    forward_task = asyncio.create_task(_forward())
    try:
        # Klient odatda hech narsa yubormaydi; bu disconnect'ni aniqlaydi.
        while True:
            await websocket.receive_text()
            async with AsyncSessionLocal() as db:
                current_user = await db.get(User, user.id)
                if not current_user or not current_user.is_active or not current_user.is_logged_in:
                    await websocket.close(code=4401)
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        forward_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass


@router.websocket("/ws/slot/{slot_id}")
async def slot_websocket(
    websocket: WebSocket,
    slot_id: str,
    token: str | None = Query(None),
):
    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=4401)
        return

    try:
        sid = uuid.UUID(slot_id)
    except (ValueError, TypeError):
        await websocket.close(code=4404)
        return

    async with AsyncSessionLocal() as db:
        slot = await db.get(Slot, sid)
        if slot is None:
            await websocket.close(code=4404)
            return
        if user.id != slot.reviewer_id and user.id != slot.reviewee_id and not user.is_admin:
            await websocket.close(code=4403)
            return

    await manager.connect(slot_id, websocket, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            # Session revocation check: verify user has not logged out or been deactivated
            async with AsyncSessionLocal() as db:
                current_user = await db.get(User, user.id)
                if not current_user or not current_user.is_active or not current_user.is_logged_in:
                    await websocket.close(code=4401)
                    await manager.disconnect(slot_id, websocket)
                    return
            await _handle_client_event(slot_id, current_user, data)
    except WebSocketDisconnect:
        await manager.disconnect(slot_id, websocket)
    except Exception:
        await manager.disconnect(slot_id, websocket)


async def _handle_client_event(slot_id: str, user: User, data: dict) -> None:
    # Session revocation check: drop any event from an inactive or logged-out user
    if not user.is_active or not user.is_logged_in:
        return

    event = data.get("event")
    try:
        sid = uuid.UUID(slot_id)
    except (ValueError, TypeError):
        return

    async with AsyncSessionLocal() as db:
        slot = await db.get(Slot, sid)
        if slot is None:
            return
        if user.id != slot.reviewer_id and user.id != slot.reviewee_id and not user.is_admin:
            return

        if event == "client.start":
            slot = await slot_service.start_slot(db, slot, user)
            await db.commit()
            who = "reviewer" if user.id == slot.reviewer_id else "reviewee"
            await manager.publish(slot_id, {"event": "slot.start", "who": who})
            if slot.reviewer_started and slot.reviewee_started:
                await manager.publish(
                    slot_id,
                    {
                        "event": "slot.both_started",
                        "reviewer_link": _tg_link(slot.reviewee),
                        "reviewee_link": _tg_link(slot.reviewer),
                    },
                )
        elif event == "client.finish":
            slot = await slot_service.finish_slot(db, slot, user)
            await db.commit()
            who = "reviewer" if user.id == slot.reviewer_id else "reviewee"
            await manager.publish(slot_id, {"event": "slot.finish", "who": who})
            if slot.status == "completed":
                await manager.publish(
                    slot_id,
                    {
                        "event": "slot.both_finished",
                        "duration_minutes": slot.duration_minutes,
                    },
                )
        elif event == "client.absent":
            slot = await slot_service.mark_absent(db, slot, user)
            await db.commit()
            await manager.publish(
                slot_id, {"event": "slot.absent", "by": str(user.id)}
            )


def _tg_link(other: User | None) -> str | None:
    if other and other.telegram_username:
        return f"https://t.me/{other.telegram_username}"
    return None
