"""Indexes for the current badge-holder directory.

Revision ID: 282
Revises: 281
"""

from alembic import op


revision = "282"
down_revision = "281"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ba_active_earned "
            "ON badge_assignments (earned_at DESC, id DESC) WHERE status = 'active'"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ba_active_type_earned "
            "ON badge_assignments (target_type, earned_at DESC, id DESC) WHERE status = 'active'"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ba_active_badge_earned "
            "ON badge_assignments (badge_id, earned_at DESC, id DESC) WHERE status = 'active'"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in (
            "ix_ba_active_badge_earned",
            "ix_ba_active_type_earned",
            "ix_ba_active_earned",
        ):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
