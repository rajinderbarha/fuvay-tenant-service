"""TENANT-ADMIN-LIFECYCLE-CLOSURE: widen tenant_vertical_enrollments.status
from varchar(20) to varchar(40). The new canonical activation-lifecycle
states ("approved_pending_activation" = 28 chars, "activation_requirements_pending"
= 32 chars) didn't fit the original 20-char column -- discovered via a real
StringDataRightTruncationError while live-testing the activation orchestrator.

Revision ID: 196
Revises: 195
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "196"
down_revision = "195"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "tenant_vertical_enrollments", "status",
        existing_type=sa.String(20), type_=sa.String(40), existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "tenant_vertical_enrollments", "status",
        existing_type=sa.String(40), type_=sa.String(20), existing_nullable=False,
    )
