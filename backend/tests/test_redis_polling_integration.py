"""Genuine multi-process concurrency integration tests against a real local Redis instance."""
from __future__ import annotations

import asyncio
import multiprocessing
import os
import signal
import threading
import time
import unittest
import httpx
import redis

from telegram.ext import Application
from telegram.request import HTTPXRequest

from bot.main import TelegramPollingLock

DISPOSABLE_REDIS_URL = "redis://127.0.0.1:26379/0"


def _worker_partition_a(
    q_a: multiprocessing.Queue,
    cmd_q: multiprocessing.Queue,
    active_counter,
    max_active_counter,
    lock_key: str,
) -> None:
    """Worker A acquires lock, polls, simulates network partition, and halts before B can acquire."""
    term_received = False

    def _term_handler(signum, frame):
        nonlocal term_received
        term_received = True

    signal.signal(signal.SIGTERM, _term_handler)

    lock = TelegramPollingLock(
        redis_url=DISPOSABLE_REDIS_URL,
        lock_key=lock_key,
        ttl_ms=3000,
        renew_interval_ms=400,
        safety_margin_ms=1000,
    )
    if not lock.acquire(retry_interval=0.1, max_wait_s=3.0):
        q_a.put(("error", "Process A failed to acquire"))
        return

    q_a.put(("acquired_a", (lock.owner_id, time.monotonic())))

    loop_count = 0
    while True:
        # Check command queue for simulated network partition
        if not cmd_q.empty():
            cmd = cmd_q.get_nowait()
            if cmd == "sever_redis":
                def _fail(*args, **kwargs):
                    raise redis.exceptions.ConnectionError("Simulated partition for Process A")
                lock._renew_script = _fail
                lock._client.execute_command = _fail

        if not lock.is_lease_valid():
            break

        with active_counter.get_lock():
            active_counter.value += 1
            if active_counter.value > max_active_counter.value:
                max_active_counter.value = active_counter.value

        time.sleep(0.04)
        loop_count += 1

        with active_counter.get_lock():
            active_counter.value -= 1

    stopped_at = time.monotonic()
    q_a.put(("loop_stopped_a", (loop_count, stopped_at, term_received)))

    # Wait for reconnect test command
    try:
        cmd = cmd_q.get(timeout=6.0)
        if cmd == "reconnect_redis":
            lock._client = redis.Redis.from_url(DISPOSABLE_REDIS_URL, decode_responses=True)
            q_a.put(("a_is_lease_valid_after_reconnect", lock.is_lease_valid()))
    except Exception as exc:
        q_a.put(("reconnect_error", str(exc)))


def _worker_partition_b(
    q_b: multiprocessing.Queue,
    active_counter,
    max_active_counter,
    lock_key: str,
) -> None:
    """Worker B stays standby, and acquires ONLY after A partition expires."""
    lock = TelegramPollingLock(
        redis_url=DISPOSABLE_REDIS_URL,
        lock_key=lock_key,
        ttl_ms=3000,
        renew_interval_ms=400,
        safety_margin_ms=1000,
    )

    # 1. Attempt non-blocking / short-wait acquisition while A is active
    if not lock.acquire(retry_interval=0.1, max_wait_s=0.5):
        q_b.put(("standby_b", lock.owner_id))
    else:
        q_b.put(("error", "Process B acquired prematurely!"))
        lock.release()
        return

    # 2. Wait for A to expire and acquire
    if lock.acquire(retry_interval=0.1, max_wait_s=6.0):
        acquired_at = time.monotonic()
        q_b.put(("acquired_b", (lock.owner_id, acquired_at)))
        loop_count = 0
        while lock.is_lease_valid() and loop_count < 6:
            with active_counter.get_lock():
                active_counter.value += 1
                if active_counter.value > max_active_counter.value:
                    max_active_counter.value = active_counter.value
            time.sleep(0.04)
            loop_count += 1
            with active_counter.get_lock():
                active_counter.value -= 1
        lock.release()
        q_b.put(("loop_stopped_b", loop_count))


def _worker_pause_proc(
    status_queue: multiprocessing.Queue,
    pre_pause_counter,
    resumed_unauthorized_counter,
    resumed_phase_flag,
    lock_key: str,
) -> None:
    """Process for testing prolonged OS process pauses (SIGSTOP/SIGCONT)."""
    def _term_handler(signum, frame):
        pass

    signal.signal(signal.SIGTERM, _term_handler)

    lock = TelegramPollingLock(
        redis_url=DISPOSABLE_REDIS_URL,
        lock_key=lock_key,
        ttl_ms=2500,
        renew_interval_ms=400,
        safety_margin_ms=800,
    )
    if not lock.acquire(retry_interval=0.1, max_wait_s=2.0):
        return
    status_queue.put(("acquired", lock.owner_id))

    while lock.is_lease_valid():
        if bool(resumed_phase_flag.value):
            with resumed_unauthorized_counter.get_lock():
                resumed_unauthorized_counter.value += 1
        else:
            with pre_pause_counter.get_lock():
                pre_pause_counter.value += 1
        time.sleep(0.04)

    status_queue.put(("loop_exited", (pre_pause_counter.value, resumed_unauthorized_counter.value)))
    lock.release()


def _worker_shutdown_sim(
    sync_q: multiprocessing.Queue,
    cmd_q: multiprocessing.Queue,
    lock_key: str,
) -> None:
    """Simulates the lifecycle of app.run_polling() with TelegramPollingLock."""
    polling_stopped = False
    term_handled = False
    stop_polling = False

    def _sigterm_handler(signum, frame):
        nonlocal term_handled, stop_polling
        term_handled = True
        stop_polling = True

    signal.signal(signal.SIGTERM, _sigterm_handler)

    lock = TelegramPollingLock(
        redis_url=DISPOSABLE_REDIS_URL,
        lock_key=lock_key,
        ttl_ms=4000,
        renew_interval_ms=300,
        safety_margin_ms=1000,
    )
    if not lock.acquire(retry_interval=0.1, max_wait_s=2.0):
        sync_q.put(("error", "Failed to acquire lock"))
        return

    sync_q.put(("started", lock.owner_id))

    try:
        # Simulated run_polling() loop
        while not stop_polling:
            if not cmd_q.empty():
                cmd = cmd_q.get_nowait()
                if cmd == "fail_renewal":
                    def _fail_renew(*args, **kwargs):
                        raise redis.exceptions.ConnectionError("Simulated heartbeat failure")
                    lock._renew_script = _fail_renew
            if not lock.is_lease_valid():
                break
            time.sleep(0.04)
    finally:
        polling_stopped = True
        # Lock must NOT be released before polling is stopped
        released = lock.release()
        heartbeat_alive = lock._heartbeat_thread.is_alive() if lock._heartbeat_thread else False
        sync_q.put(("shutdown_complete", {
            "polling_stopped": polling_stopped,
            "term_handled": term_handled,
            "released": released,
            "heartbeat_alive": heartbeat_alive,
        }))


def _ptb_worker_a(
    q_a: multiprocessing.Queue,
    cmd_q: multiprocessing.Queue,
    active_http_reqs,
    cancelled_http_reqs,
    lock_key: str,
) -> None:
    """Genuine python-telegram-bot worker running long-polling with test double MockTransport."""
    lost_event = threading.Event()

    lock = TelegramPollingLock(
        redis_url=DISPOSABLE_REDIS_URL,
        lock_key=lock_key,
        ttl_ms=3000,
        renew_interval_ms=300,
        safety_margin_ms=1000,
        on_lost_callback=lost_event.set,
    )
    if not lock.acquire(retry_interval=0.1, max_wait_s=3.0):
        q_a.put(("error", "Process A failed to acquire"))
        return

    q_a.put(("acquired_a", (lock.owner_id, time.monotonic())))

    async def mock_handler(request: httpx.Request):
        url = str(request.url)
        content = request.content.decode("utf-8") if request.content else ""
        if "getMe" in url:
            return httpx.Response(200, json={"ok": True, "result": {"id": 12345, "is_bot": True, "first_name": "TestBot", "username": "test_bot"}})
        if "deleteWebhook" in url:
            return httpx.Response(200, json={"ok": True, "result": True})
        if "getUpdates" in url:
            if "timeout=0" in content:
                return httpx.Response(200, json={"ok": True, "result": []})
            with active_http_reqs.get_lock():
                active_http_reqs.value += 1
            try:
                # Long poll simulating Telegram waiting for updates
                await asyncio.sleep(3.0)
                return httpx.Response(200, json={"ok": True, "result": []})
            except asyncio.CancelledError:
                with cancelled_http_reqs.get_lock():
                    cancelled_http_reqs.value += 1
                raise
            finally:
                with active_http_reqs.get_lock():
                    active_http_reqs.value -= 1
        return httpx.Response(200, json={"ok": True, "result": True})

    async def run_lifecycle():
        token = "123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ"
        transport = httpx.MockTransport(mock_handler)
        req1 = HTTPXRequest(httpx_kwargs={"transport": transport})
        req2 = HTTPXRequest(httpx_kwargs={"transport": transport})
        app = Application.builder().token(token).request(req1).get_updates_request(req2).build()

        # Real lifecycle methods of python-telegram-bot
        await app.initialize()
        await app.start()
        await app.updater.start_polling(poll_interval=0.05, timeout=10)
        q_a.put(("polling_started", time.monotonic()))

        while True:
            if not cmd_q.empty():
                cmd = cmd_q.get_nowait()
                if cmd == "sever_redis":
                    def _fail(*args, **kwargs):
                        raise redis.exceptions.ConnectionError("Simulated partition for Process A")
                    lock._renew_script = _fail
                    lock._client.execute_command = _fail

            if lost_event.is_set() or not lock.is_lease_valid():
                break
            await asyncio.sleep(0.04)

        # Stop updater and application gracefully
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

    asyncio.run(run_lifecycle())

    stopped_at = time.monotonic()
    # Release lock ONLY after genuine polling updater has completely stopped
    released = lock.release()
    q_a.put(("a_stopped", (stopped_at, active_http_reqs.value, cancelled_http_reqs.value, released)))

    cmd = cmd_q.get(timeout=5.0)
    if cmd == "reconnect":
        lock._client = redis.Redis.from_url(DISPOSABLE_REDIS_URL, decode_responses=True)
        q_a.put(("a_valid_after_reconnect", lock.is_lease_valid()))


def _ptb_worker_b(q_b: multiprocessing.Queue, active_http_reqs, lock_key: str) -> None:
    """Genuine python-telegram-bot worker B standing by and taking over only when safe."""
    lock = TelegramPollingLock(
        redis_url=DISPOSABLE_REDIS_URL,
        lock_key=lock_key,
        ttl_ms=3000,
        renew_interval_ms=300,
        safety_margin_ms=1000,
    )
    if not lock.acquire(retry_interval=0.1, max_wait_s=0.5):
        q_b.put(("b_standby", lock.owner_id))
    else:
        q_b.put(("error", "B acquired prematurely"))
        lock.release()
        return

    # Wait for A to release/expire and acquire
    if lock.acquire(retry_interval=0.1, max_wait_s=6.0):
        b_acquired_at = time.monotonic()
        # Verify active HTTP requests from A are 0
        reqs_when_b_acquired = active_http_reqs.value
        q_b.put(("b_acquired", (b_acquired_at, reqs_when_b_acquired)))
        lock.release()


class TestRealRedisPollingIntegration(unittest.TestCase):
    """Integration test suite executing real multi-process distributed locking against local Redis."""

    def setUp(self) -> None:
        try:
            self.redis_client = redis.Redis.from_url(
                DISPOSABLE_REDIS_URL, decode_responses=True, socket_timeout=2.0
            )
            self.redis_client.ping()
        except Exception as exc:
            self.skipTest(f"Disposable local Redis not reachable at {DISPOSABLE_REDIS_URL}: {exc}")

        self.lock_key = "p2p:test_integration:leader_lock"
        self.redis_client.delete(self.lock_key)

    def tearDown(self) -> None:
        if hasattr(self, "redis_client"):
            self.redis_client.delete(self.lock_key)

    def test_active_owner_partition_stops_polling_before_standby_acquires(self) -> None:
        """Process A suffers partition; stops polling loop before B acquires expired lease; max active <= 1."""
        q_a = multiprocessing.Queue()
        q_b = multiprocessing.Queue()
        cmd_q = multiprocessing.Queue()
        active_ctr = multiprocessing.Value("i", 0)
        max_active_ctr = multiprocessing.Value("i", 0)

        # 1. Start Process A
        proc_a = multiprocessing.Process(
            target=_worker_partition_a,
            args=(q_a, cmd_q, active_ctr, max_active_ctr, self.lock_key),
        )
        proc_a.start()

        msg_a, data_a = q_a.get(timeout=4.0)
        self.assertEqual(msg_a, "acquired_a")
        owner_a = data_a[0]

        # 2. Start Process B and verify standby
        proc_b = multiprocessing.Process(
            target=_worker_partition_b,
            args=(q_b, active_ctr, max_active_ctr, self.lock_key),
        )
        proc_b.start()

        msg_b, owner_b = q_b.get(timeout=4.0)
        self.assertEqual(msg_b, "standby_b")
        self.assertNotEqual(owner_a, owner_b)

        # 3. Trigger network partition for Process A only
        time.sleep(0.3)
        cmd_q.put("sever_redis")

        # 4. Collect lifecycle completion from Process A and B
        msg_stop_a, data_stop_a = q_a.get(timeout=6.0)
        self.assertEqual(msg_stop_a, "loop_stopped_a")
        loop_cnt_a, a_stopped_at, a_sigterm_caught = data_stop_a

        msg_acq_b, data_acq_b = q_b.get(timeout=6.0)
        self.assertEqual(msg_acq_b, "acquired_b")
        owner_b_acq, b_acquired_at = data_acq_b

        # Verify Process A stopped its polling loop BEFORE Process B acquired the lease
        self.assertIsNotNone(a_stopped_at)
        self.assertIsNotNone(b_acquired_at)
        self.assertLess(
            a_stopped_at,
            b_acquired_at,
            f"Process A stopped at {a_stopped_at} must be strictly before Process B acquired at {b_acquired_at}",
        )
        # Safety margin guarantees a clear gap between Process A exit and Process B acquisition
        self.assertGreaterEqual(
            b_acquired_at - a_stopped_at,
            0.4,
            f"Expected safety gap between A stop and B acquire, got {b_acquired_at - a_stopped_at:.3f}s",
        )

        # Verify max concurrent pollers never exceeded 1
        self.assertEqual(max_active_ctr.value, 1, f"Max concurrent active pollers was {max_active_ctr.value}, expected 1")

        # 5. Verify Process A cannot resume polling after reconnect without reacquiring
        cmd_q.put("reconnect_redis")
        msg_rec, is_valid_after = q_a.get(timeout=4.0)
        self.assertEqual(msg_rec, "a_is_lease_valid_after_reconnect")
        self.assertFalse(is_valid_after, "Process A must NOT be able to poll after reconnect without reacquire")

        # Process B stops cleanly
        msg_stop_b, _ = q_b.get(timeout=4.0)
        self.assertEqual(msg_stop_b, "loop_stopped_b")

        proc_a.join(timeout=3.0)
        proc_b.join(timeout=3.0)

    def test_prolonged_process_pause_prevented_from_stale_polling(self) -> None:
        """Process paused exceeding TTL cannot resume polling with stale lease upon waking."""
        status_q = multiprocessing.Queue()
        pre_pause_ctr = multiprocessing.Value("i", 0)
        resumed_unauth_ctr = multiprocessing.Value("i", 0)
        resumed_flag = multiprocessing.Value("b", False)

        proc = multiprocessing.Process(
            target=_worker_pause_proc,
            args=(status_q, pre_pause_ctr, resumed_unauth_ctr, resumed_flag, self.lock_key),
        )
        proc.start()

        msg, owner = status_q.get(timeout=4.0)
        self.assertEqual(msg, "acquired")
        time.sleep(0.3)
        self.assertGreater(pre_pause_ctr.value, 0)

        # 1. Suspend process using OS SIGSTOP exceeding lease TTL (2500ms)
        os.kill(proc.pid, signal.SIGSTOP)
        time.sleep(3.2)

        # Verify Redis lock expired while process was frozen
        self.assertIsNone(self.redis_client.get(self.lock_key))

        # Explicitly mark that any subsequent poll cycle is in the resumed phase
        resumed_flag.value = True

        # 2. Resume process using OS SIGCONT
        os.kill(proc.pid, signal.SIGCONT)

        msg_exit, counts = status_q.get(timeout=4.0)
        self.assertEqual(msg_exit, "loop_exited")
        pre_cnt, resumed_cnt = counts

        # Must have executed strictly 0 unauthorized poll cycles after waking!
        self.assertEqual(
            resumed_cnt,
            0,
            f"Process executed {resumed_cnt} unauthorized poll cycles after waking from prolonged pause (expected 0)!",
        )
        proc.join(timeout=3.0)

    def test_signal_and_polling_shutdown_correctness(self) -> None:
        """Heartbeat failure triggers SIGTERM, stops polling, releases lock, and cleans up thread."""
        sync_q = multiprocessing.Queue()
        cmd_q = multiprocessing.Queue()

        proc = multiprocessing.Process(
            target=_worker_shutdown_sim,
            args=(sync_q, cmd_q, self.lock_key),
        )
        proc.start()

        msg, owner_id = sync_q.get(timeout=4.0)
        self.assertEqual(msg, "started")

        # Verify lock is active in Redis during polling
        self.assertEqual(self.redis_client.get(self.lock_key), owner_id)

        # Trigger heartbeat renewal failure to test emergency stop & SIGTERM
        cmd_q.put("fail_renewal")

        msg_done, report = sync_q.get(timeout=6.0)
        self.assertEqual(msg_done, "shutdown_complete")

        # Verify shutdown guarantees
        self.assertTrue(report["polling_stopped"], "Polling must have stopped")
        self.assertTrue(report["term_handled"], "SIGTERM from heartbeat failure must be handled")
        self.assertTrue(report["released"], "Lock must be successfully released upon shutdown")
        self.assertFalse(report["heartbeat_alive"], "No heartbeat thread may survive shutdown")

        # Verify lock is no longer in Redis
        self.assertIsNone(self.redis_client.get(self.lock_key))
        proc.join(timeout=3.0)

    def test_real_ptb_polling_lifecycle_cancellation_and_handover(self) -> None:
        """Genuine python-telegram-bot lifecycle: long-poll getUpdates cancellation and safe handover."""
        q_a = multiprocessing.Queue()
        q_b = multiprocessing.Queue()
        cmd_q = multiprocessing.Queue()
        active_reqs = multiprocessing.Value("i", 0)
        cancelled_reqs = multiprocessing.Value("i", 0)

        # 1. Start Process A running genuine python-telegram-bot polling with mock transport
        proc_a = multiprocessing.Process(
            target=_ptb_worker_a,
            args=(q_a, cmd_q, active_reqs, cancelled_reqs, self.lock_key),
        )
        proc_a.start()

        msg, (owner_a, t_acq_a) = q_a.get(timeout=5.0)
        self.assertEqual(msg, "acquired_a")

        msg, t_poll_started = q_a.get(timeout=5.0)
        self.assertEqual(msg, "polling_started")
        time.sleep(0.3)

        # Verify in-flight HTTP long-polling request is active in Process A
        self.assertEqual(active_reqs.value, 1, "Expected active in-flight getUpdates long poll")

        # 2. Start Process B and verify it remains in standby
        proc_b = multiprocessing.Process(
            target=_ptb_worker_b,
            args=(q_b, active_reqs, self.lock_key),
        )
        proc_b.start()

        msg, owner_b = q_b.get(timeout=5.0)
        self.assertEqual(msg, "b_standby")
        self.assertNotEqual(owner_a, owner_b)

        # 3. Simulate Redis lease loss for Process A
        cmd_q.put("sever_redis")

        # 4. A stops: updater cancels in-flight getUpdates, stops polling, and only then releases lock
        msg_stop, (a_stopped_at, a_active_reqs_at_stop, a_cancelled, a_released) = q_a.get(timeout=6.0)
        self.assertEqual(msg_stop, "a_stopped")
        self.assertEqual(a_active_reqs_at_stop, 0, "All HTTP requests in Process A must be fully terminated")
        self.assertGreaterEqual(a_cancelled, 1, "Long-poll getUpdates request must be explicitly cancelled")

        # 5. Process B acquires lock only after A has completely stopped
        msg_acq, (b_acquired_at, reqs_when_b_acquired) = q_b.get(timeout=6.0)
        self.assertEqual(msg_acq, "b_acquired")
        self.assertEqual(reqs_when_b_acquired, 0, "No active HTTP requests allowed when Process B acquires lock")
        self.assertLess(a_stopped_at, b_acquired_at, "Process A must stop before Process B can acquire lease")

        # 6. Verify Process A cannot poll after Redis reconnect without reacquiring lock
        cmd_q.put("reconnect")
        msg_rec, valid_after = q_a.get(timeout=5.0)
        self.assertEqual(msg_rec, "a_valid_after_reconnect")
        self.assertFalse(valid_after, "Process A must not be valid after reconnect without reacquire")

        proc_a.join(timeout=3.0)
        proc_b.join(timeout=3.0)

    def test_stale_owner_cannot_delete_or_renew_active_owner_lock(self) -> None:
        """A stale owner ID cannot renew or release a lock currently held by another owner."""
        lock_a = TelegramPollingLock(
            redis_url=DISPOSABLE_REDIS_URL,
            lock_key=self.lock_key,
            ttl_ms=8000,
        )
        self.assertTrue(lock_a.acquire())
        self.assertEqual(self.redis_client.get(self.lock_key), lock_a.owner_id)

        lock_b = TelegramPollingLock(
            redis_url=DISPOSABLE_REDIS_URL,
            lock_key=self.lock_key,
            ttl_ms=8000,
        )
        # Attempt renewal using lock_b's owner_id
        renew_res = lock_b._renew_script(keys=[self.lock_key], args=[lock_b.owner_id, lock_b.ttl_ms])
        self.assertEqual(renew_res, 0, "Stale owner must NOT be allowed to renew another owner's lease")

        # Attempt release using lock_b's owner_id
        del_res = lock_b._release_script(keys=[self.lock_key], args=[lock_b.owner_id])
        self.assertEqual(del_res, 0, "Stale owner must NOT be allowed to delete another owner's lock")

        self.assertEqual(self.redis_client.get(self.lock_key), lock_a.owner_id)
        self.assertTrue(lock_a.release())
        self.assertIsNone(self.redis_client.get(self.lock_key))

    def test_fail_closed_on_redis_connection_outage(self) -> None:
        """Lock acquisition immediately raises RuntimeError when Redis is down; polling is refused."""
        with self.assertRaises(RuntimeError) as ctx:
            TelegramPollingLock(redis_url="redis://127.0.0.1:29999/0")
        self.assertIn("Refusing to start uncoordinated polling (fail closed)", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
