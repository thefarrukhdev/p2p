"""add_unique_constraints_reviews_leaderboard

Revision ID: 7a8f9b0c1d2e
Revises: 2a06e370e5a4
Create Date: 2026-10-28 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8f9b0c1d2e'
down_revision: Union[str, None] = '2a06e370e5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Preflight Check 1: Detect duplicate review groups on (slot_id, author_id).
    # NEVER delete user reviews automatically or pick arbitrary UUIDs with MIN(id).
    review_dupes = bind.execute(sa.text("""
        SELECT slot_id, author_id, COUNT(*) AS count
        FROM reviews
        GROUP BY slot_id, author_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    # Preflight Check 2: Detect duplicate snapshot groups on (month, category, user_id).
    snapshot_dupes = bind.execute(sa.text("""
        SELECT month, category, user_id, COUNT(*) AS count
        FROM leaderboard_snapshots
        GROUP BY month, category, user_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    if review_dupes or snapshot_dupes:
        error_details = []
        if review_dupes:
            error_details.append(
                f"[reviews] Found {len(review_dupes)} duplicate group(s) on (slot_id, author_id). "
                f"Sample conflicting groups: {review_dupes[:5]}.\n"
                "Manual resolution required. Run the following read-only SQL to inspect duplicates:\n"
                "SELECT * FROM reviews WHERE (slot_id, author_id) IN (\n"
                "    SELECT slot_id, author_id FROM reviews GROUP BY slot_id, author_id HAVING COUNT(*) > 1\n"
                ") ORDER BY slot_id, created_at;"
            )
        if snapshot_dupes:
            error_details.append(
                f"[leaderboard_snapshots] Found {len(snapshot_dupes)} duplicate group(s) on (month, category, user_id). "
                f"Sample conflicting groups: {snapshot_dupes[:5]}.\n"
                "Manual resolution required. Run the following read-only SQL to inspect duplicates:\n"
                "SELECT * FROM leaderboard_snapshots WHERE (month, category, user_id) IN (\n"
                "    SELECT month, category, user_id FROM leaderboard_snapshots GROUP BY month, category, user_id HAVING COUNT(*) > 1\n"
                ") ORDER BY month, user_id, created_at;"
            )
        raise RuntimeError(
            "ABORTING MIGRATION 7a8f9b0c1d2e: Preflight duplicate check failed.\n"
            + "\n\n".join(error_details)
        )

    # 1. Unique constraint on reviews (each user can review a slot only once)
    op.create_unique_constraint(
        'uq_reviews_slot_author',
        'reviews',
        ['slot_id', 'author_id']
    )
    # 2. Unique constraint on leaderboard_snapshots (one entry per user per month and category)
    op.create_unique_constraint(
        'uq_leaderboard_month_cat_user',
        'leaderboard_snapshots',
        ['month', 'category', 'user_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_leaderboard_month_cat_user', 'leaderboard_snapshots', type_='unique')
    op.drop_constraint('uq_reviews_slot_author', 'reviews', type_='unique')
