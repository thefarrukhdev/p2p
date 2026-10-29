"""add_notification_delivery_status

Revision ID: 8c9d0e1f2a3b
Revises: 7a8f9b0c1d2e
Create Date: 2026-10-28 22:30:00.000000

Conservative, non-destructive migration adding explicit outbox delivery status,
fencing claim tokens, attempt tracking, and backoff scheduling.

Backfill business rules:
1. Historical success: sent_telegram=true -> 'sent'
2. Non-Telegram types (system, review_received): sent_telegram=false -> 'not_eligible'
3. Stale/historical records (>1h old): sent_telegram=false -> 'abandoned_historical'
4. Known permanent failure (missing telegram_id): sent_telegram=false -> 'failed_permanent'
5. Recent genuine pending (<=1h old with telegram_id): sent_telegram=false -> 'pending'
"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = '8c9d0e1f2a3b'
down_revision: Union[str, None] = '7a8f9b0c1d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ELIGIBLE_TYPES = ("slot_reminder", "slot_revealed", "slot_cancelled", "absent_given", "slot_booked")
KNOWN_TYPES = {"slot_reminder", "slot_revealed", "slot_cancelled", "absent_given", "slot_booked", "system", "review_received"}


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Preflight Validation & Inspection
    total_rows = bind.execute(sa.text("SELECT COUNT(*) FROM notifications;")).scalar() or 0

    # 1a. Integrity Checks: Check for NULL sent_telegram, NULL created_at, and unknown types
    null_sent_count = bind.execute(sa.text(
        "SELECT COUNT(*) FROM notifications WHERE sent_telegram IS NULL;"
    )).scalar() or 0
    if null_sent_count > 0:
        raise ValueError(
            f"Preflight migration aborted: Detected {null_sent_count} notifications with NULL sent_telegram! "
            f"Resolve NULL sent_telegram records before applying migration."
        )

    null_created_at_count = bind.execute(sa.text(
        "SELECT COUNT(*) FROM notifications WHERE created_at IS NULL;"
    )).scalar() or 0
    if null_created_at_count > 0:
        raise ValueError(
            f"Preflight migration aborted: Detected {null_created_at_count} notifications with NULL created_at! "
            f"Valid timestamps are required for historical partitioning."
        )

    distinct_types_res = bind.execute(sa.text("SELECT DISTINCT type FROM notifications;")).fetchall()
    found_types = {row[0] for row in distinct_types_res}
    unknown_types = found_types - KNOWN_TYPES
    if unknown_types:
        raise ValueError(
            f"Preflight migration aborted: Detected unknown notification types {sorted(unknown_types)} in database! "
            f"Add them explicitly to migration mapping rules before proceeding."
        )

    # 1b. Diagnostic preflight partition counts using exact predicates
    diagnostic_counts = bind.execute(sa.text("""
        SELECT
            COUNT(CASE WHEN sent_telegram = true THEN 1 END) AS count_sent,
            COUNT(CASE WHEN sent_telegram = false AND type NOT IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked') THEN 1 END) AS count_not_eligible,
            COUNT(CASE WHEN sent_telegram = false AND type IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked') AND created_at < NOW() - INTERVAL '1 hour' THEN 1 END) AS count_abandoned_historical,
            COUNT(CASE WHEN sent_telegram = false AND type IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked') AND created_at >= NOW() - INTERVAL '1 hour' AND (user_id IS NULL OR user_id IN (SELECT id FROM users WHERE telegram_id IS NULL) OR user_id NOT IN (SELECT id FROM users)) THEN 1 END) AS count_failed_permanent_missing_tg,
            COUNT(CASE WHEN sent_telegram = false AND type IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked') AND created_at >= NOW() - INTERVAL '1 hour' AND user_id IN (SELECT id FROM users WHERE telegram_id IS NOT NULL) THEN 1 END) AS count_pending
        FROM notifications;
    """)).fetchone()

    c_sent = diagnostic_counts[0] if diagnostic_counts else 0
    c_not_eligible = diagnostic_counts[1] if diagnostic_counts else 0
    c_abandoned = diagnostic_counts[2] if diagnostic_counts else 0
    c_failed_perm = diagnostic_counts[3] if diagnostic_counts else 0
    c_pending = diagnostic_counts[4] if diagnostic_counts else 0
    classified_total = c_sent + c_not_eligible + c_abandoned + c_failed_perm + c_pending
    unclassified_count = total_rows - classified_total

    logger.info("=== PREFLIGHT NOTIFICATION PARTITION AUDIT ===")
    logger.info("Total notifications:              %d", total_rows)
    logger.info("1. sent:                          %d", c_sent)
    logger.info("2. not_eligible:                  %d", c_not_eligible)
    logger.info("3. abandoned_historical:          %d", c_abandoned)
    logger.info("4. failed_permanent_missing_tg:   %d", c_failed_perm)
    logger.info("5. pending:                       %d", c_pending)
    logger.info("Total classified:                 %d", classified_total)
    logger.info("Unclassified rows:                %d", unclassified_count)

    if unclassified_count != 0:
        raise ValueError(
            f"Preflight migration aborted: {unclassified_count} rows in notifications could not be partitioned! "
            f"Total: {total_rows}, Classified: {classified_total}. All rows must belong to exactly one backfill category."
        )

    preflight_stats = bind.execute(sa.text("""
        SELECT type, sent_telegram, COUNT(*) AS count
        FROM notifications
        GROUP BY type, sent_telegram
        ORDER BY type, sent_telegram;
    """)).fetchall()

    logger.info("=== PREFLIGHT NOTIFICATION RAW DISTRIBUTION ===")
    for row in preflight_stats:
        logger.info("Type: %-18s | sent_telegram: %-5s | Count: %d", row[0], str(row[1]), row[2])

    # 2. Add new columns for truthful delivery tracking, fencing tokens, claim/dispatch attempts, and backoff scheduling
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_delivery_status',
            sa.String(length=30),
            server_default='pending',
            nullable=False,
        ),
    )
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_claim_token',
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_claimed_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_claim_attempts',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
    )
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_attempts',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
    )
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_next_retry_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        'notifications',
        sa.Column(
            'telegram_error',
            sa.Text(),
            nullable=True,
        ),
    )

    # 3. Conservative, business-grounded backfill

    # Rule 1: Preserve historical successful delivery
    bind.execute(sa.text("""
        UPDATE notifications
        SET telegram_delivery_status = 'sent',
            telegram_error = NULL,
            telegram_next_retry_at = NULL
        WHERE sent_telegram = true;
    """))

    # Rule 2: Non-Telegram notification types (system announcements, reviews) -> 'not_eligible'
    bind.execute(sa.text("""
        UPDATE notifications
        SET telegram_delivery_status = 'not_eligible',
            telegram_error = 'type_not_configured_for_telegram',
            telegram_next_retry_at = NULL
        WHERE sent_telegram = false
          AND type NOT IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked');
    """))

    # Rule 3: Stale/expired historical notifications (> 1 hour old) -> 'abandoned_historical'
    # Prevents notification storms or sending expired reminders from days/weeks ago
    bind.execute(sa.text("""
        UPDATE notifications
        SET telegram_delivery_status = 'abandoned_historical',
            telegram_error = 'historical_backfill_expired',
            telegram_next_retry_at = NULL
        WHERE sent_telegram = false
          AND type IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked')
          AND created_at < NOW() - INTERVAL '1 hour';
    """))

    # Rule 4: Recent notifications where recipient has no Telegram account or user missing -> 'failed_permanent'
    bind.execute(sa.text("""
        UPDATE notifications
        SET telegram_delivery_status = 'failed_permanent',
            telegram_error = 'missing_telegram_id',
            telegram_next_retry_at = NULL
        WHERE sent_telegram = false
          AND type IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked')
          AND created_at >= NOW() - INTERVAL '1 hour'
          AND (user_id IS NULL OR user_id IN (SELECT id FROM users WHERE telegram_id IS NULL) OR user_id NOT IN (SELECT id FROM users));
    """))

    # Rule 5: Recent notifications with valid Telegram recipient -> 'pending'
    bind.execute(sa.text("""
        UPDATE notifications
        SET telegram_delivery_status = 'pending',
            telegram_error = NULL,
            telegram_next_retry_at = NULL
        WHERE sent_telegram = false
          AND type IN ('slot_reminder', 'slot_revealed', 'slot_cancelled', 'absent_given', 'slot_booked')
          AND created_at >= NOW() - INTERVAL '1 hour'
          AND user_id IN (SELECT id FROM users WHERE telegram_id IS NOT NULL);
    """))

    # 4. Create composite index for efficient atomic claim queries with lease expiration and retry backoff
    op.create_index(
        'ix_notifications_delivery_status',
        'notifications',
        ['telegram_delivery_status', 'telegram_next_retry_at', 'telegram_claimed_at'],
        unique=False,
    )

    # 5. Enforce database-level delivery invariant (strictly NULL-safe):
    # Both columns must be NOT NULL, and sent_telegram is true IF AND ONLY IF telegram_delivery_status == 'sent'
    op.create_check_constraint(
        'ck_notifications_sent_telegram_invariant',
        'notifications',
        "sent_telegram IS NOT NULL AND telegram_delivery_status IS NOT NULL AND "
        "((sent_telegram = true AND telegram_delivery_status = 'sent') OR "
        "(sent_telegram = false AND telegram_delivery_status != 'sent'))",
    )

    # 6. Enforce allowed delivery status domain at the database level:
    op.create_check_constraint(
        'ck_notifications_delivery_status_allowed',
        'notifications',
        "telegram_delivery_status IN ("
        "'pending', 'claimed', 'sent', 'failed_transient', 'failed_permanent', "
        "'quarantined_claim_exhausted', 'abandoned_historical', 'not_eligible')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_notifications_delivery_status_allowed', 'notifications', type_='check')
    op.drop_constraint('ck_notifications_sent_telegram_invariant', 'notifications', type_='check')
    op.drop_index('ix_notifications_delivery_status', table_name='notifications')
    op.drop_column('notifications', 'telegram_error')
    op.drop_column('notifications', 'telegram_next_retry_at')
    op.drop_column('notifications', 'telegram_attempts')
    op.drop_column('notifications', 'telegram_claim_attempts')
    op.drop_column('notifications', 'telegram_claimed_at')
    op.drop_column('notifications', 'telegram_claim_token')
    op.drop_column('notifications', 'telegram_delivery_status')
