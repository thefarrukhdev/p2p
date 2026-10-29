"""Celery instance + Beat schedule."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "peer_learn",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.slot_tasks", "app.tasks.leaderboard_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Slot reminders: check every minute for slots starting in ~15 minutes.
    "slot-reminders": {
        "task": "app.tasks.slot_tasks.send_slot_reminders",
        "schedule": 60.0,
    },
    # Telegram outbox retry dispatcher: processes pending notifications every minute.
    "telegram-outbox-dispatch": {
        "task": "app.tasks.slot_tasks.dispatch_telegram_notifications",
        "schedule": 60.0,
    },
    # Absent check: every minute look for stale booked/in-progress slots.
    "absent-check": {
        "task": "app.tasks.slot_tasks.check_absences",
        "schedule": 60.0,
    },
    # Monthly leaderboard snapshot + reset on the 1st at 00:05 UTC.
    "monthly-leaderboard-snapshot": {
        "task": "app.tasks.leaderboard_tasks.monthly_snapshot",
        "schedule": crontab(day_of_month="1", hour=0, minute=5),
    },
}
