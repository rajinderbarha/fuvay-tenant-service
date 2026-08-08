"""Widen usage_credit_ledger.deduction_source so job completion stops 500ing.

Real, live defect. `resolve_commission_credits` labels a percentage-commission
deduction with a PREFIXED identifier -- `category_commission:<uuid>` (56 chars)
or `monetization_policy:<uuid>` (56 chars) -- but the column is VARCHAR(50). So
every attempt to complete a Home Services job under a published
PERCENTAGE_COMMISSION policy died on
`StringDataRightTruncationError: value too long for type character varying(50)`,
rolled the whole completion back and returned HTTP 500. Only the legacy
flat-credit branch fit, because it stores a bare uuid (36 chars) -- which is why
this survived: the commission path was never exercised end to end.

100 chars leaves room for the longest prefix currently emitted plus a uuid,
without pretending the column is free-form text.

Revision ID: 235
Revises: 234
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "235"
down_revision = "234"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "usage_credit_ledger", "deduction_source",
        existing_type=sa.String(50), type_=sa.String(100), existing_nullable=True,
    )


def downgrade() -> None:
    # Truncating would silently corrupt the prefixed labels this widening was
    # added for, so the values are cleared rather than mangled.
    op.execute(sa.text(
        "UPDATE usage_credit_ledger SET deduction_source = NULL "
        "WHERE length(deduction_source) > 50"
    ))
    op.alter_column(
        "usage_credit_ledger", "deduction_source",
        existing_type=sa.String(100), type_=sa.String(50), existing_nullable=True,
    )
