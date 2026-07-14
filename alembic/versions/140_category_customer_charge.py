"""MODULE-L5-10 — per-category customer charge (platform fee shown to the customer).

The platform earns from BOTH sides of a job: a commission from the provider
(migration 139) AND a charge added to what the CUSTOMER pays, shown to them as an
included platform fee. e.g. a Rs.500 service with a 10% customer charge is
displayed to the customer as Rs.550 ("Rs.50 platform fee included"). Set per
category, like the commission.

Adds a nullable customer_charge_pct to service_categories. NULL means "no
customer charge" (0%), so existing categories are unchanged until an admin sets
one.

Revision ID: 140
Revises: 139
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "140"
down_revision = "139"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("service_categories")]
    if "customer_charge_pct" not in cols:
        op.add_column(
            "service_categories",
            sa.Column("customer_charge_pct", sa.Numeric(5, 2), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("service_categories")]
    if "customer_charge_pct" in cols:
        op.drop_column("service_categories", "customer_charge_pct")
