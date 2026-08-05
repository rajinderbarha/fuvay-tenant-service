"""TEAM-DIRECTORY: add max_concurrent_jobs to provider_team_members.

The Staff & Technicians design shows a real per-staff capacity ratio
(e.g. "2/4 jobs", 50%, "At risk" once near/at the limit) -- confirmed by
the earlier audit as a genuinely MISSING field (only an aggregate busy
count existed anywhere in the schema). Rather than fabricate a percentage
client-side against no real denominator, this adds the actual field.
Default 4 matches the design reference and is a safe, tenant-editable
starting point, not a hardcoded runtime constant.

Revision ID: 200
Revises: 199
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "200"
down_revision = "199"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_team_members",
        sa.Column("max_concurrent_jobs", sa.Integer(), nullable=False, server_default="4"),
    )


def downgrade() -> None:
    op.drop_column("provider_team_members", "max_concurrent_jobs")
