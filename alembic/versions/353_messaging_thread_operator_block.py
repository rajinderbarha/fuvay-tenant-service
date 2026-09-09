"""Operator-set block on a messaging thread.

`opted_out` is /stop and any /fuvay clears it; `human_handoff` is /human.
Both are customer-initiated, so before this there was no way to silence a
spammer from our side -- the only recourse was blocking them in the Meta
inbox, outside the product and invisible to our own logs.

Revision ID: 353
Revises: 352
"""
from alembic import op
import sqlalchemy as sa


revision = "353"
down_revision = "352"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messaging_threads",
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "messaging_threads",
        sa.Column("blocked_reason", sa.String(200), nullable=True),
    )
    # Partial: only blocked threads are ever looked up by this column, and
    # blocked threads are a rounding error next to the whole table.
    op.create_index(
        "ix_msg_thread_blocked_until", "messaging_threads", ["blocked_until"],
        postgresql_where=sa.text("blocked_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_msg_thread_blocked_until", table_name="messaging_threads")
    op.drop_column("messaging_threads", "blocked_reason")
    op.drop_column("messaging_threads", "blocked_until")
