"""HS8 fix — add missing updated_at column to service_job_media_uploads.

Same systemic gap as migrations 122-126. Blocks completion-proof photo
upload (before/after photos), a required HS8 acceptance item.

Revision ID: 127
Revises: 126
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "127"
down_revision = "126"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("service_job_media_uploads")]
    if "updated_at" not in columns:
        op.add_column(
            "service_job_media_uploads",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("service_job_media_uploads")]
    if "updated_at" in columns:
        op.drop_column("service_job_media_uploads", "updated_at")
