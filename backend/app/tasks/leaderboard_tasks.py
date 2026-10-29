"""Monthly leaderboard snapshot task."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import delete, text
from sqlalchemy.exc import IntegrityError

from app.db.base import AsyncSessionLocal
from app.db.models.leaderboard_snapshot import LeaderboardSnapshot
from app.services import leaderboard_service
from app.tasks.async_utils import run_async
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _previous_month_start() -> date:
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    if month == 1:
        return date(year - 1, 12, 1)
    return date(year, month - 1, 1)


@celery_app.task(name="app.tasks.leaderboard_tasks.monthly_snapshot")
def monthly_snapshot() -> int:
    return run_async(_monthly_snapshot())


async def _monthly_snapshot() -> int:
    """Persist the previous month's rankings into LeaderboardSnapshot."""
    month = _previous_month_start()
    written = 0
    async with AsyncSessionLocal() as db:
        # Atomic concurrency guard: attempt transaction-level advisory lock in PostgreSQL (key: 849202611028).
        # Transaction-scoped lock is held continuously across all DELETEs, computations, and INSERTs
        # until the single final db.commit() or db.rollback().
        try:
            lock_res = await db.execute(
                text("SELECT pg_try_advisory_xact_lock(849202611028)")
            )
            acquired = lock_res.scalar()
            if acquired is False:
                logger.info("Leaderboard monthly snapshot is already running in another worker. Skipping.")
                return 0
        except Exception:
            # Not PostgreSQL (e.g. SQLite / Test mocks) or advisory locks not supported; proceed
            pass

        categories = {
            leaderboard_service.CATEGORY_MOST_TAUGHT: leaderboard_service.most_taught,
            leaderboard_service.CATEGORY_MOST_LEARNED: leaderboard_service.most_learned,
            leaderboard_service.CATEGORY_MOST_XP: leaderboard_service.most_xp,
        }
        try:
            for category, fn in categories.items():
                # Clear existing snapshot for this month & category to prevent duplicate records
                await db.execute(
                    delete(LeaderboardSnapshot).where(
                        LeaderboardSnapshot.month == month,
                        LeaderboardSnapshot.category == category,
                    )
                )
                entries = await fn(db)
                for entry in entries:
                    db.add(
                        LeaderboardSnapshot(
                            user_id=entry["user_id"],
                            month=month,
                            category=category,
                            rank=entry["rank"],
                            value=entry["value"],
                        )
                    )
                    written += 1
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            logger.warning(
                "Concurrent leaderboard snapshot conflict detected: %s. Rolled back safely.", exc
            )
            return 0
        except Exception:
            await db.rollback()
            raise
    return written
