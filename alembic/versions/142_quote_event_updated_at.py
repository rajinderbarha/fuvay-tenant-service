"""MODULE-L5-16 — add the missing updated_at column to service_job_quote_events.

The ServiceJobQuoteEvent model inherits ServiceOSBase, which declares both
created_at AND updated_at, but the table was created with only created_at. Every
quote-event insert therefore failed with UndefinedColumnError, which meant a
customer could not approve, reject, or request a revision of a quote (and the
provider-side quote transitions log events too). The bug had been dormant only
because no quote had ever been driven end-to-end. This aligns the table with the
model.

Revision ID: 142
Revises: 141
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "142"
down_revision = "141"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_job_quote_events",
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("service_job_quote_events", "updated_at")
