"""Telegram bot entry point with fail-closed distributed polling lock coordination."""
from __future__ import annotations

import logging
import os
import signal
import socket
import threading
import time
import uuid

from telegram.ext import Application, CommandHandler

from app.core.config import settings
from app.core.logging import configure_secure_logging
from bot.handlers.start import get_start_handler, help_cmd, webapp_cmd
from bot.handlers.admin import get_admin_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
configure_secure_logging()
logger = logging.getLogger(__name__)


class TelegramPollingLock:
    """Fail-closed distributed lease lock using Redis to enforce single-poller execution."""

    RENEW_LUA = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("pexpire", KEYS[1], ARGV[2])
    else
        return 0
    end
    """

    RELEASE_LUA = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    def __init__(
        self,
        redis_url: str | None,
        lock_key: str = "p2p:telegram_bot:leader_lock",
        ttl_ms: int = 10000,
        renew_interval_ms: int = 2500,
        safety_margin_ms: int = 3500,
        on_lost_callback=None,
    ) -> None:
        if not redis_url or not str(redis_url).strip():
            logger.critical(
                "REDIS_URL is not configured. Polling cannot start in a multi-instance or zero-downtime deployment (fail closed)."
            )
            raise RuntimeError(
                "REDIS_URL is required for Telegram bot polling lock coordination. Polling will not start (fail closed)."
            )

        self.redis_url = redis_url
        self.lock_key = lock_key
        self.ttl_ms = ttl_ms
        self.renew_interval_s = renew_interval_ms / 1000.0
        self.safety_margin_s = safety_margin_ms / 1000.0
        self.owner_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
        self._running = False
        self._stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._on_lost_callback = on_lost_callback
        self.lease_deadline: float = 0.0

        try:
            import redis
            # 1.0s timeout ensures blocked network calls cannot silently exceed safety margin
            self._client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            self._client.ping()
        except Exception as exc:
            safe_url = self._safe_redis_url(self.redis_url)
            logger.critical(
                "Failed to connect to Redis at %s (%s). Polling refused (fail closed).",
                safe_url,
                exc,
            )
            raise RuntimeError(
                f"Redis connection failed for leader lock: {exc}. Refusing to start uncoordinated polling (fail closed)."
            ) from exc

        self._renew_script = self._client.register_script(self.RENEW_LUA)
        self._release_script = self._client.register_script(self.RELEASE_LUA)

    @staticmethod
    def _safe_redis_url(url: str) -> str:
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            netloc = p.hostname or "localhost"
            if p.port:
                netloc += f":{p.port}"
            return f"{p.scheme}://{netloc}{p.path}"
        except Exception:
            return "redis://[REDACTED]"

    def is_lease_valid(self) -> bool:
        """Fencing check: return True only if lock is active AND local monotonic time is strictly before deadline."""
        return self._running and not self._stop_event.is_set() and (time.monotonic() < self.lease_deadline)

    def acquire(
        self,
        retry_interval: float = 1.0,
        max_wait_s: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> bool:
        """Acquire the distributed lock atomically. Stays in standby until acquired or stopped."""
        logger.info("Requesting Telegram polling leader lock for %s...", self.owner_id)
        start_time = time.monotonic()

        while not self._stop_event.is_set():
            if stop_event and stop_event.is_set():
                logger.info("Stop event received during lock standby. Exiting without acquiring lock.")
                return False

            try:
                # Atomic acquisition with SET NX PX
                acquired = self._client.set(self.lock_key, self.owner_id, nx=True, px=self.ttl_ms)
                if acquired:
                    self._running = True
                    # Local monotonic deadline calculated with safety margin deducted
                    self.lease_deadline = time.monotonic() + ((self.ttl_ms / 1000.0) - self.safety_margin_s)
                    logger.info(
                        "Leader lock acquired (%s). Single-instance polling established (lease deadline +%.2fs).",
                        self.owner_id,
                        (self.ttl_ms / 1000.0) - self.safety_margin_s,
                    )
                    self._heartbeat_thread = threading.Thread(
                        target=self._heartbeat_loop,
                        daemon=True,
                        name="TelegramLockHeartbeat",
                    )
                    self._heartbeat_thread.start()
                    return True

                holder = self._client.get(self.lock_key)
                logger.info(
                    "Lock currently held by %s. Standing by to avoid HTTP 409 conflict...",
                    holder or "unknown",
                )
            except Exception as exc:
                logger.error(
                    "Redis error while checking leader lock: %s. Remaining in standby (fail closed).",
                    exc,
                )

            if max_wait_s is not None and (time.monotonic() - start_time) >= max_wait_s:
                logger.warning("Max wait time (%.1fs) exceeded while waiting for leader lock.", max_wait_s)
                return False

            time.sleep(retry_interval)
        return False

    def _heartbeat_loop(self) -> None:
        """Continuously renew lease while active. Trigger emergency stop if lease is lost or expired."""
        consecutive_failures = 0
        max_consecutive_failures = 2

        while self._running and not self._stop_event.is_set():
            time.sleep(self.renew_interval_s)
            if not self._running or self._stop_event.is_set():
                break

            # If local deadline has passed (e.g. prolonged pause), stop immediately
            if time.monotonic() >= self.lease_deadline:
                logger.critical(
                    "Local lease deadline expired (monotonic=%.2f >= deadline=%.2f). Terminating polling!",
                    time.monotonic(),
                    self.lease_deadline,
                )
                self._trigger_emergency_stop()
                break

            try:
                # Owner-checked renewal via Lua script
                res = self._renew_script(keys=[self.lock_key], args=[self.owner_id, self.ttl_ms])
                if res == 1:
                    consecutive_failures = 0
                    # Update local lease deadline
                    self.lease_deadline = time.monotonic() + ((self.ttl_ms / 1000.0) - self.safety_margin_s)
                else:
                    logger.critical(
                        "Leader lock was lost or expired (%s, res=%s). Terminating polling immediately!",
                        self.owner_id,
                        res,
                    )
                    self._trigger_emergency_stop()
                    break
            except Exception as exc:
                consecutive_failures += 1
                logger.error(
                    "Redis communication error during lease renewal (%d/%d): %s",
                    consecutive_failures,
                    max_consecutive_failures,
                    exc,
                )
                if time.monotonic() >= self.lease_deadline or consecutive_failures >= max_consecutive_failures:
                    logger.critical(
                        "Lease deadline reached without successful renewal. Terminating polling to prevent dual pollers!"
                    )
                    self._trigger_emergency_stop()
                    break

    def _trigger_emergency_stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if callable(self._on_lost_callback):
            try:
                self._on_lost_callback()
            except Exception as exc:
                logger.error("Error in on_lost_callback: %s", exc)
        else:
            logger.critical("Sending SIGTERM to process %d to safely stop polling.", os.getpid())
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception as exc:
                logger.error("Failed to send SIGTERM: %s", exc)

    def release(self) -> bool:
        """Owner-checked atomic lock release. Called only after polling has completely stopped."""
        self._running = False
        self._stop_event.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.5)

        if not self._client or not self._release_script:
            return False
        try:
            res = self._release_script(keys=[self.lock_key], args=[self.owner_id])
            if res == 1:
                logger.info("Successfully released leader lock (%s).", self.owner_id)
                return True
            else:
                logger.warning(
                    "Lock was not held or already expired/owned by another instance when releasing (%s).",
                    self.owner_id,
                )
                return False
        except Exception as exc:
            logger.error("Failed to release leader lock in Redis: %s", exc)
            return False
        finally:
            try:
                self._client.close()
            except Exception:
                pass


def build_application() -> Application:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(get_start_handler())
    app.add_handler(get_admin_handler())
    app.add_handler(CommandHandler("webapp", webapp_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    return app


def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    app = build_application()

    # Fail closed if REDIS_URL is missing or Redis is unreachable
    lock = TelegramPollingLock(
        redis_url=settings.REDIS_URL,
        on_lost_callback=lambda: os.kill(os.getpid(), signal.SIGTERM),
    )

    acquired = lock.acquire()
    if not acquired:
        logger.warning("Could not acquire leader lock. Bot exiting without polling.")
        return

    try:
        logger.info("Starting bot in polling mode as coordinated leader")
        app.run_polling(drop_pending_updates=True)
    finally:
        # Polling has completely stopped before lock is released
        lock.release()


if __name__ == "__main__":
    main()
