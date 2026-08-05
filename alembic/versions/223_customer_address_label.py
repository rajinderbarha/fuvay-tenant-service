"""ADD-EDIT-ADDRESS-CONTRACT (2026-08-01) -- additive `label` column on
customer_addresses. The approved Add/Edit Address design has a distinct
Home/Work/Other segmented control AND a separate "Full name" field, but the
model previously had only one free-text `name` column -- reused for both
concepts in the prior Saved Addresses phase (label -> `name`, recipient name
left null). This migration adds a dedicated nullable `label` column so
`name` can hold the recipient's full name and `label` the Home/Work/Other
selection, without a parallel address model.

Revision ID: 223
Revises: 222
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "223"
down_revision = "222"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_addresses",
        sa.Column("label", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_addresses", "label")
