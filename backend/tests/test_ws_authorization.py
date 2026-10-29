"""Regression tests for BUG-01: WebSocket Slot Authorization & IDOR Protection."""
from __future__ import annotations

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.db.models.slot import Slot, SlotStatus
from app.db.models.user import User
from app.ws.slot_ws import slot_websocket, _handle_client_event


class TestWebSocketAuthorization(unittest.IsolatedAsyncioTestCase):
    async def test_non_participant_rejected_on_websocket_connect(self):
        """User who is neither reviewer nor reviewee must be rejected with 4403."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        intruder_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="libft",
            status=SlotStatus.BOOKED.value,
        )
        intruder = User(
            id=intruder_id,
            school21_login="intruder",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )

        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("app.ws.slot_ws._authenticate", return_value=intruder), \
             patch("app.ws.slot_ws.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.ws.slot_ws.manager") as mock_manager:

            mock_db = AsyncMock()
            mock_db.get.return_value = slot
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await slot_websocket(mock_ws, str(slot_id), token="dummy-token")

            # Must close with 4403 (Forbidden)
            mock_ws.close.assert_awaited_with(code=4403)
            # Must NOT connect to manager
            mock_manager.connect.assert_not_called()

    async def test_participant_allowed_on_websocket_connect(self):
        """User who is reviewer or reviewee must be allowed to connect."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="libft",
            status=SlotStatus.BOOKED.value,
        )
        reviewer = User(
            id=reviewer_id,
            school21_login="reviewer",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )

        mock_ws = AsyncMock()
        mock_ws.receive_json.side_effect = Exception("disconnect test")

        with patch("app.ws.slot_ws._authenticate", return_value=reviewer), \
             patch("app.ws.slot_ws.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.ws.slot_ws.manager") as mock_manager:

            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            mock_db = AsyncMock()
            mock_db.get.return_value = slot
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await slot_websocket(mock_ws, str(slot_id), token="valid-token")

            # Must connect to manager with user_id
            mock_manager.connect.assert_awaited_with(str(slot_id), mock_ws, reviewer.id)

    async def test_non_participant_cannot_send_events(self):
        """Even if an event is processed, non-participant events must be dropped."""
        reviewer_id = uuid.uuid4()
        reviewee_id = uuid.uuid4()
        intruder_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            reviewer_project="libft",
            status=SlotStatus.BOOKED.value,
        )
        intruder = User(
            id=intruder_id,
            school21_login="intruder",
            is_active=True,
            is_logged_in=True,
            is_admin=False,
        )

        with patch("app.ws.slot_ws.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.ws.slot_ws.slot_service") as mock_slot_service, \
             patch("app.ws.slot_ws.manager") as mock_manager:

            mock_db = AsyncMock()
            mock_db.get.return_value = slot
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await _handle_client_event(str(slot_id), intruder, {"event": "client.start"})

            # slot_service.start_slot must NOT be called for an intruder
            mock_slot_service.start_slot.assert_not_called()
            mock_manager.publish.assert_not_called()

    async def test_manager_revoke_user_immediately_closes_sockets(self):
        """manager.revoke_user must immediately close connected sockets with 4401 on logout."""
        from app.ws.manager import ConnectionManager
        mgr = ConnectionManager()
        slot_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        # Connect user
        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        # Trigger immediate revocation (e.g. from POST /auth/logout)
        with patch("app.ws.manager.redis_client.publish", new_callable=AsyncMock):
            await mgr.revoke_user(user_id)

        # Must immediately close with 4401 without client interaction
        mock_ws.close.assert_awaited_with(code=4401)
        # Socket must be removed from manager connections
        self.assertNotIn(mock_ws, mgr._connections.get(slot_id, {}))

    async def test_broadcast_local_drops_message_for_logged_out_user(self):
        """Idle connected socket must not receive protected outbound events if user logged out."""
        from app.ws.manager import ConnectionManager
        mgr = ConnectionManager()
        slot_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()

        # Connect socket with user_id
        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        # User is logged out in DB when broadcast happens
        logged_out_user = User(
            id=user_id,
            school21_login="charlie",
            is_active=True,
            is_logged_in=False,
        )

        with patch("app.db.base.AsyncSessionLocal") as mock_session_ctx:
            mock_db = AsyncMock()
            mock_db.get.return_value = logged_out_user
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await mgr._broadcast_local(slot_id, '{"event": "slot.both_started", "secret": "link"}')

            # Message must NOT be sent to the revoked user
            mock_ws.send_text.assert_not_called()
            # Socket must be closed with 4401
            mock_ws.close.assert_awaited_with(code=4401)

    async def test_distributed_revocation_across_replicas(self):
        """Revocation initiated on Replica 1 must reach Replica 2 via Redis and close Replica 2 sockets."""
        from app.ws.manager import ConnectionManager
        mgr1 = ConnectionManager()  # Replica 1
        mgr2 = ConnectionManager()  # Replica 2

        user_id = uuid.uuid4()
        slot_id = str(uuid.uuid4())

        # Socket connected to Replica 2
        ws_replica2 = AsyncMock()
        ws_replica2.accept = AsyncMock()
        ws_replica2.close = AsyncMock()

        with patch.object(mgr2, "_subscribe", return_value=None):
            await mgr2.connect(slot_id, ws_replica2, user_id=user_id)

        # 1. User logs out on Replica 1 -> calls revoke_user
        published_messages = []
        async def mock_publish(channel, data):
            published_messages.append((channel, data))

        with patch("app.ws.manager.redis_client.publish", side_effect=mock_publish):
            await mgr1.revoke_user(user_id)

        # Verify Replica 1 published to Redis channel system:revoke_user
        self.assertEqual(len(published_messages), 1)
        self.assertEqual(published_messages[0][0], "system:revoke_user")
        self.assertEqual(published_messages[0][1], str(user_id))

        # 2. Replica 2 processes the Redis broadcast event
        revoked_uid = uuid.UUID(published_messages[0][1])
        await mgr2._close_local_user_sockets(revoked_uid)

        # Socket on Replica 2 must be closed with 4401 and removed from Replica 2
        ws_replica2.close.assert_awaited_with(code=4401)
        self.assertNotIn(ws_replica2, mgr2._connections.get(slot_id, {}))
        self.assertNotIn(user_id, mgr2._user_sockets)

    async def test_established_websocket_closed_when_user_logs_out(self):
        """An already established WebSocket must close with 4401 when the user logs out."""
        reviewer_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        slot = Slot(
            id=slot_id,
            reviewer_id=reviewer_id,
            reviewer_project="libft",
            status=SlotStatus.BOOKED.value,
        )
        # Initially user is authenticated
        logged_in_user = User(
            id=reviewer_id,
            school21_login="reviewer",
            is_active=True,
            is_logged_in=True,
        )
        # Subsequently user logs out in DB
        logged_out_user = User(
            id=reviewer_id,
            school21_login="reviewer",
            is_active=True,
            is_logged_in=False,
        )

        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        # Client sends a message
        mock_ws.receive_json.return_value = {"event": "client.start"}

        with patch("app.ws.slot_ws._authenticate", return_value=logged_in_user), \
             patch("app.ws.slot_ws.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.ws.slot_ws.manager") as mock_manager:

            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            mock_db = AsyncMock()
            # 1. Connection check: db.get(Slot, sid) -> slot
            # 2. Loop check: db.get(User, user.id) -> logged_out_user
            mock_db.get.side_effect = [slot, logged_out_user]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await slot_websocket(mock_ws, str(slot_id), token="valid-token")

            # Must close socket with 4401 (Unauthorized)
            mock_ws.close.assert_awaited_with(code=4401)
            # Must disconnect from manager
            mock_manager.disconnect.assert_awaited_with(str(slot_id), mock_ws)

    async def test_handle_client_event_drops_events_for_logged_out_user(self):
        """_handle_client_event must drop events if user is logged out."""
        reviewer_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        logged_out_user = User(
            id=reviewer_id,
            school21_login="reviewer",
            is_active=True,
            is_logged_in=False,
        )

        with patch("app.ws.slot_ws.AsyncSessionLocal") as mock_session_ctx, \
             patch("app.ws.slot_ws.slot_service") as mock_slot_service, \
             patch("app.ws.slot_ws.manager") as mock_manager:

            mock_db = AsyncMock()
            mock_db.get.return_value = logged_out_user
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await _handle_client_event(str(slot_id), logged_out_user, {"event": "client.start"})

            mock_slot_service.start_slot.assert_not_called()
            mock_manager.publish.assert_not_called()

    async def test_manager_revoke_user_immediately_closes_sockets(self):
        """manager.revoke_user must immediately close connected sockets with 4401 on logout."""
        from app.ws.manager import ConnectionManager
        mgr = ConnectionManager()
        slot_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        # Connect user
        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        # Trigger immediate revocation (e.g. from POST /auth/logout)
        with patch("app.ws.manager.redis_client.publish", new_callable=AsyncMock):
            await mgr.revoke_user(user_id)

        # Must immediately close with 4401 without client interaction
        mock_ws.close.assert_awaited_with(code=4401)
        # Socket must be removed from manager connections
        self.assertNotIn(mock_ws, mgr._connections.get(slot_id, {}))

    async def test_broadcast_local_drops_message_for_logged_out_user(self):
        """Idle connected socket must not receive protected outbound events if user logged out."""
        from app.ws.manager import ConnectionManager
        mgr = ConnectionManager()
        slot_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()

        # Connect socket with user_id
        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        # User is logged out in DB when broadcast happens
        logged_out_user = User(
            id=user_id,
            school21_login="charlie",
            is_active=True,
            is_logged_in=False,
        )

        with patch("app.db.base.AsyncSessionLocal") as mock_session_ctx:
            mock_db = AsyncMock()
            mock_db.get.return_value = logged_out_user
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await mgr._broadcast_local(slot_id, '{"event": "slot.both_started", "secret": "link"}')

            # Message must NOT be sent to the revoked user
            mock_ws.send_text.assert_not_called()
            # Socket must be closed with 4401
            mock_ws.close.assert_awaited_with(code=4401)

    async def test_distributed_revocation_across_replicas(self):
        """Revocation initiated on Replica 1 must reach Replica 2 via Redis and close Replica 2 sockets."""
        from app.ws.manager import ConnectionManager
        mgr1 = ConnectionManager()  # Replica 1
        mgr2 = ConnectionManager()  # Replica 2

        user_id = uuid.uuid4()
        slot_id = str(uuid.uuid4())

        # Socket connected to Replica 2
        ws_replica2 = AsyncMock()
        ws_replica2.accept = AsyncMock()
        ws_replica2.close = AsyncMock()

        with patch.object(mgr2, "_subscribe", return_value=None):
            await mgr2.connect(slot_id, ws_replica2, user_id=user_id)

        # 1. User logs out on Replica 1 -> calls revoke_user
        published_messages = []
        async def mock_publish(channel, data):
            published_messages.append((channel, data))

        with patch("app.ws.manager.redis_client.publish", side_effect=mock_publish):
            await mgr1.revoke_user(user_id)

        # Verify Replica 1 published to Redis channel system:revoke_user
        self.assertEqual(len(published_messages), 1)
        self.assertEqual(published_messages[0][0], "system:revoke_user")
        self.assertEqual(published_messages[0][1], str(user_id))

        # 2. Replica 2 processes the Redis broadcast event
        revoked_uid = uuid.UUID(published_messages[0][1])
        await mgr2._close_local_user_sockets(revoked_uid)

        # Socket on Replica 2 must be closed with 4401 and removed from Replica 2
        ws_replica2.close.assert_awaited_with(code=4401)
        self.assertNotIn(ws_replica2, mgr2._connections.get(slot_id, {}))
        self.assertNotIn(user_id, mgr2._user_sockets)

    async def test_inactive_user_rejected_on_connect(self):
        """User whose account is blocked (is_active=False) must be rejected on connect."""
        user_id = uuid.uuid4()
        slot_id = uuid.uuid4()

        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("app.ws.slot_ws._authenticate", return_value=None):
            await slot_websocket(mock_ws, str(slot_id), token="invalid-or-blocked-token")

            # Must close with 4401 (Unauthorized)
            mock_ws.close.assert_awaited_with(code=4401)

    async def test_missed_pubsub_revocation_closed_by_periodic_revalidation(self):
        """If a Redis Pub/Sub revocation broadcast is lost/missed, periodic revalidation closes idle sockets."""
        from app.ws.manager import ConnectionManager

        mgr = ConnectionManager()
        user_id = uuid.uuid4()
        slot_id = str(uuid.uuid4())

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        self.assertIn(user_id, mgr._user_sockets)
        self.assertIn(mock_ws, mgr._connections[slot_id])

        # DB state: user is logged out (e.g. logged out on another node while Pub/Sub was partitioned)
        logged_out_user = User(
            id=user_id,
            school21_login="alice",
            is_active=True,
            is_logged_in=False,  # Logged out!
        )

        mock_db = AsyncMock()
        mock_db.get.return_value = logged_out_user

        with patch("app.ws.manager.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # Periodic reconciliation runs:
            revoked_count = await mgr.revalidate_all_connected_users()

            self.assertEqual(revoked_count, 1)
            # Idle socket was terminated with 4401:
            mock_ws.close.assert_awaited_with(code=4401)
            # Socket removed from local manager state:
            self.assertNotIn(user_id, mgr._user_sockets)
            self.assertNotIn(slot_id, mgr._connections)

    async def test_subscriber_reconnect_triggers_immediate_revalidation(self):
        """When Redis subscriber starts or reconnects, it immediately reconciles all connected sockets."""
        from app.ws.manager import ConnectionManager

        mgr = ConnectionManager()
        revalidation_called = False

        async def mock_revalidate():
            nonlocal revalidation_called
            revalidation_called = True
            return 0

        mgr.revalidate_all_connected_users = mock_revalidate

        # Simulate pubsub generator that yields one dummy message and then raises CancelledError
        mock_pubsub = AsyncMock()
        async def mock_listen():
            yield {"type": "subscribe"}
            raise asyncio.CancelledError()

        mock_pubsub.listen = mock_listen
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.aclose = AsyncMock()

        with patch("app.ws.manager.redis_client.pubsub", return_value=mock_pubsub):
            task = asyncio.create_task(mgr._listen_revocations())
            # Yield control so task connects, subscribes, and executes catch-up revalidation
            await asyncio.sleep(0.01)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_pubsub.subscribe.assert_awaited_with("system:revoke_user")
            self.assertTrue(revalidation_called, "Reconnection must trigger immediate reconciliation")

    async def test_manager_start_and_stop_lifecycle_clean_without_leaks(self):
        """manager.start() and manager.stop() properly create and terminate all background tasks without leaking."""
        from app.ws.manager import ConnectionManager

        mgr = ConnectionManager(revalidation_interval=100.0)

        # Mock out the inner infinite loops so they just sleep
        async def mock_loop():
            try:
                while True:
                    await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                pass

        with patch.object(mgr, "_listen_revocations", side_effect=mock_loop), \
             patch.object(mgr, "_periodic_revalidation_loop", side_effect=mock_loop):

            await mgr.start()
            self.assertIsNotNone(mgr._global_listener_task)
            self.assertIsNotNone(mgr._revalidation_task)
            self.assertFalse(mgr._global_listener_task.done())
            self.assertFalse(mgr._revalidation_task.done())

            await mgr.stop()
            self.assertIsNone(mgr._global_listener_task)
            self.assertIsNone(mgr._revalidation_task)
            self.assertEqual(len(mgr._tasks), 0)

    async def test_db_commit_failure_during_logout_does_not_publish_revocation(self):
        """If db.commit() fails during logout, revocation must NOT be published (fail closed)."""
        from app.api.v1.auth import logout

        user = User(
            id=uuid.uuid4(),
            school21_login="alice",
            is_active=True,
            is_logged_in=True,
        )

        mock_db = AsyncMock()
        mock_db.commit.side_effect = RuntimeError("Database write failure during logout")

        with patch("app.ws.manager.manager.revoke_user", new_callable=AsyncMock) as mock_revoke:
            with self.assertRaises(RuntimeError):
                await logout(user=user, db=mock_db)

            # Because commit failed, manager.revoke_user must not be called
            mock_revoke.assert_not_called()

    async def test_db_unavailability_during_outbound_auth_fails_closed(self):
        """When DB is unavailable during outbound auth verification, message delivery is dropped (fail closed)."""
        from app.ws.manager import ConnectionManager

        mgr = ConnectionManager()
        slot_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        mock_db = AsyncMock()
        mock_db.get.side_effect = RuntimeError("PostgreSQL connection lost during broadcast")

        with patch("app.ws.manager.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await mgr._broadcast_local(slot_id, "sensitive message")

            # Must FAIL CLOSED: protected message must NOT be delivered when authorization is unverified!
            mock_ws.send_text.assert_not_called()

    async def test_periodic_revalidation_handles_db_error_gracefully(self):
        """Periodic revalidation catches DB errors, logs warning, and does not crash the background task."""
        from app.ws.manager import ConnectionManager

        mgr = ConnectionManager()
        user_id = uuid.uuid4()
        slot_id = str(uuid.uuid4())

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        with patch.object(mgr, "_subscribe", return_value=None):
            await mgr.connect(slot_id, mock_ws, user_id=user_id)

        with patch("app.ws.manager.AsyncSessionLocal") as mock_session_ctx:
            mock_session_ctx.side_effect = RuntimeError("Database unreachable")

            # Must not raise an exception
            revoked = await mgr.revalidate_all_connected_users()
            self.assertEqual(revoked, 0)


if __name__ == "__main__":
    unittest.main()
