"""Repair quote-event timestamp drift.

Revision 142 added ``service_job_quote_events.updated_at``, but databases that
were stamped or restored from an older schema can report the latest Alembic
revision while still missing the column. Quote decision events inherit
``ServiceOSBase`` and therefore cannot be inserted without it.

Revision ID: 244
Revises: 243
"""
from alembic import op
import sqlalchemy as sa

revision = "244"
down_revision = "243"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='service_job_quote_events' "
        "AND column_name='updated_at'"
    )).fetchone()
    if not exists:
        op.add_column(
            "service_job_quote_events",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    # This is a repair migration. Revision 142 owns the column, so downgrading
    # 244 must not remove a column that correctly exists because of 142.
    pass
