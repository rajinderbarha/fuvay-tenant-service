"""TECHNICIAN-HOME: add self-settable availability_state to provider_team_members.

The Technician Home screen's availability selector (available/busy/offline)
needs a real, technician-writable presence state -- audited and confirmed
genuinely MISSING (can_receive_assignment exists but is tenant-admin-only
and boolean, not a 3-state presence value; there is no availability-state
column anywhere in the schema). This adds the one real field rather than
faking presence client-side. `can_receive_assignment` remains the
tenant-controlled eligibility flag and is left untouched -- a technician
setting themselves "offline" narrows scheduling for NEW work on top of
whatever the tenant already allows, it never widens it.

Revision ID: 209
Revises: 208
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "209"
down_revision = "208"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_team_members",
        sa.Column("availability_state", sa.String(20), nullable=False, server_default="available"),
    )
    op.add_column(
        "provider_team_members",
        sa.Column("availability_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("provider_team_members", "availability_updated_at")
    op.drop_column("provider_team_members", "availability_state")
