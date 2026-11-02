"""Unit tests for Telegram bot fail-closed distributed lock."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from bot.main import TelegramPollingLock


class TestTelegramPollingLockUnit(unittest.TestCase):
    """Verify unit-level fail-closed behavior and Lua script coordination."""

    def test_missing_redis_url_fails_closed(self) -> None:
        """Lock must reject initialization with RuntimeError if REDIS_URL is missing."""
        with self.assertRaises(RuntimeError) as ctx:
            TelegramPollingLock(redis_url=None)
        self.assertIn("REDIS_URL is required", str(ctx.exception))

        with self.assertRaises(RuntimeError) as ctx:
            TelegramPollingLock(redis_url="")
        self.assertIn("REDIS_URL is required", str(ctx.exception))

    def test_unreachable_redis_fails_closed(self) -> None:
        """Lock must reject initialization with RuntimeError if Redis connection fails."""
        with self.assertRaises(RuntimeError) as ctx:
            TelegramPollingLock(redis_url="redis://127.0.0.1:29999/0")
        self.assertIn("Redis connection failed", str(ctx.exception))

    @patch("redis.Redis.from_url")
    def test_successful_acquisition_and_release_lua(self, mock_from_url: MagicMock) -> None:
        """Lock acquires via SET NX PX, runs heartbeat, and releases via owner-checked Lua script."""
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = True

        mock_renew = MagicMock(return_value=1)
        mock_release = MagicMock(return_value=1)
        mock_redis.register_script.side_effect = [mock_renew, mock_release]

        lock = TelegramPollingLock(
            redis_url="redis://127.0.0.1:6379/0",
            lock_key="test:lock",
            ttl_ms=5000,
            renew_interval_ms=1000,
        )

        acquired = lock.acquire()
        self.assertTrue(acquired)
        mock_redis.set.assert_called_once_with(
            "test:lock",
            lock.owner_id,
            nx=True,
            px=5000,
        )
        self.assertTrue(lock._running)

        # Release must invoke registered Lua release script
        released = lock.release()
        self.assertTrue(released)
        self.assertFalse(lock._running)
        mock_release.assert_called_once_with(
            keys=["test:lock"],
            args=[lock.owner_id],
        )


if __name__ == "__main__":
    unittest.main()
