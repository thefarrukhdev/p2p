"""WebSocket connection manager with Redis pub/sub fan-out.

Keeps a per-slot set of local connections and bridges cross-instance events
through Redis so multiple API workers stay in sync.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict

from fastapi import WebSocket

from app.db.base import AsyncSessionLocal
from app.db.models.user import User
from app.services.cache import redis_client

logger = logging.getLogger(__name__)


def _channel(slot_id: str) -> str:
    return f"slot:{slot_id}"


class ConnectionManager:
    def __init__(self, revalidation_interval: float = 30.0) -> None:
        # Maps slot_id -> dict of {WebSocket: user_id}
        self._connections: dict[str, dict[WebSocket, uuid.UUID | None]] = defaultdict(dict)
        # Maps user_id -> set of (slot_id, WebSocket)
        self._user_sockets: dict[uuid.UUID, set[tuple[str, WebSocket]]] = defaultdict(set)
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._global_listener_task: asyncio.Task | None = None
        self._revalidation_task: asyncio.Task | None = None
        self.revalidation_interval = revalidation_interval

    async def start(self) -> None:
        """Start global background listener and periodic reconciliation task."""
        if self._global_listener_task is None or self._global_listener_task.done():
            self._global_listener_task = asyncio.create_task(self._listen_revocations())
        if self._revalidation_task is None or self._revalidation_task.done():
            self._revalidation_task = asyncio.create_task(self._periodic_revalidation_loop())

    async def stop(self) -> None:
        """Cancel global listener, revalidator, and all active slot subscription tasks."""
        if self._revalidation_task:
            self._revalidation_task.cancel()
            try:
                await self._revalidation_task
            except (asyncio.CancelledError, Exception):
                pass
            self._revalidation_task = None

        if self._global_listener_task:
            self._global_listener_task.cancel()
            try:
                await self._global_listener_task
            except (asyncio.CancelledError, Exception):
                pass
            self._global_listener_task = None

        async with self._lock:
            for task in self._tasks.values():
                task.cancel()
            self._tasks.clear()

    async def revalidate_all_connected_users(self) -> int:
        """Periodic/catch-up reconciliation loop:
        Inspects all locally connected users against PostgreSQL authoritative state.
        If any user is logged out (is_logged_in=False) or deactivated (is_active=False),
        immediately closes their local WebSockets with code 4401.
        Guarantees eventual revocation consistency (within revalidation_interval)
        even during total Redis pub/sub network partitions or missed messages.
        """
        async with self._lock:
            active_user_ids = list(self._user_sockets.keys())

        if not active_user_ids:
            return 0

        revoked_count = 0
        try:
            async with AsyncSessionLocal() as db:
                for uid in active_user_ids:
                    user = await db.get(User, uid)
                    if not user or not user.is_active or not user.is_logged_in:
                        await self._close_local_user_sockets(uid)
                        revoked_count += 1
        except Exception as exc:
            logger.error("DB error during periodic user revalidation: %s", exc)
        return revoked_count

    async def _periodic_revalidation_loop(self) -> None:
        """Runs background reconciliation loop at configured interval."""
        while True:
            try:
                await asyncio.sleep(self.revalidation_interval)
                await self.revalidate_all_connected_users()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2.0)

    async def _listen_revocations(self) -> None:
        """Listen on Redis for revocation events broadcast by any application replica/worker."""
        while True:
            pubsub = None
            try:
                pubsub = redis_client.pubsub()
                await pubsub.subscribe("system:revoke_user")
                # On initial connect or reconnect after connection loss,
                # perform authoritative reconciliation to catch any events missed during downtime:
                await self.revalidate_all_connected_users()
                async for message in pubsub.listen():
                    if message.get("type") == "message":
                        raw_uid = message.get("data")
                        if isinstance(raw_uid, bytes):
                            raw_uid = raw_uid.decode("utf-8")
                        try:
                            uid = uuid.UUID(str(raw_uid))
                            await self._close_local_user_sockets(uid)
                        except Exception:
                            pass
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1.0)
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe("system:revoke_user")
                        await pubsub.aclose()
                    except Exception:
                        pass

    async def _close_local_user_sockets(self, user_id: uuid.UUID) -> None:
        """Close local WebSockets for a given user on this process instance."""
        async with self._lock:
            sockets = list(self._user_sockets.pop(user_id, set()))
            for slot_id, ws in sockets:
                conns = self._connections.get(slot_id)
                if conns:
                    conns.pop(ws, None)
                    if not conns:
                        self._connections.pop(slot_id, None)
                        task = self._tasks.pop(slot_id, None)
                        if task:
                            task.cancel()
                try:
                    await ws.close(code=4401)
                except Exception:
                    pass

    async def connect(
        self, slot_id: str, websocket: WebSocket, user_id: uuid.UUID | None = None
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[slot_id][websocket] = user_id
            if user_id:
                self._user_sockets[user_id].add((slot_id, websocket))
            if slot_id not in self._tasks:
                self._tasks[slot_id] = asyncio.create_task(
                    self._subscribe(slot_id)
                )

    async def disconnect(self, slot_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(slot_id)
            if conns and websocket in conns:
                user_id = conns.pop(websocket)
                if user_id and user_id in self._user_sockets:
                    self._user_sockets[user_id].discard((slot_id, websocket))
                    if not self._user_sockets[user_id]:
                        self._user_sockets.pop(user_id, None)
                if not conns:
                    self._connections.pop(slot_id, None)
                    task = self._tasks.pop(slot_id, None)
                    if task:
                        task.cancel()

    async def revoke_user(self, user_id: uuid.UUID) -> None:
        """Immediately disconnect all WebSockets belonging to a revoked or logged-out user across all replicas."""
        # 1. Close local sockets immediately on this worker
        await self._close_local_user_sockets(user_id)

        # 2. Publish to Redis so all other application workers close their local sockets too
        try:
            await redis_client.publish("system:revoke_user", str(user_id))
        except Exception:
            pass

    async def publish(self, slot_id: str, event: dict) -> None:
        """Publish an event to all instances via Redis."""
        await redis_client.publish(_channel(slot_id), json.dumps(event))

    async def _broadcast_local(self, slot_id: str, message: str) -> None:
        """Deliver outbound message, re-validating user authorization for protected events."""
        async with self._lock:
            active_sockets = list(self._connections.get(slot_id, {}).items())

        if not active_sockets:
            return

        try:
            async with AsyncSessionLocal() as db:
                for ws, user_id in active_sockets:
                    if user_id:
                        # Revalidate authorization before outbound protected event delivery
                        try:
                            user = await db.get(User, user_id)
                        except Exception as db_exc:
                            # FAIL CLOSED: When DB cannot verify authorization, deny protected delivery!
                            logger.error(
                                "Database unavailable during outbound auth verification for user %s: %s. Dropping message (fail closed).",
                                user_id,
                                db_exc,
                            )
                            continue

                        if not user or not user.is_active or not user.is_logged_in:
                            try:
                                await ws.close(code=4401)
                            except Exception:
                                pass
                            await self.disconnect(slot_id, ws)
                            continue

                    try:
                        await ws.send_text(message)
                    except Exception:
                        await self.disconnect(slot_id, ws)
        except Exception as exc:
            logger.error("Error in _broadcast_local for slot %s: %s", slot_id, exc)

    async def _subscribe(self, slot_id: str) -> None:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(_channel(slot_id))
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    await self._broadcast_local(slot_id, message["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(_channel(slot_id))
            await pubsub.aclose()


manager = ConnectionManager()
