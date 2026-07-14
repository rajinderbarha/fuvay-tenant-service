"""MODULE-L5-10 — per-category commission rate.

Commission on every service invoice was a hardcoded flat 10%
(ServiceCommissionService._resolve_rate returned DEFAULT_COMMISSION_RATE and the
docstring literally said "Override with category/offering config in future").
So the platform charged the same commission on a Rs.200 salon visit and a
Rs.50,000 real-estate deal — no way to set it per category.

Adds a nullable commission_pct to service_categories. NULL means "use the
platform default (10%)", so existing categories are unchanged until an admin
sets a rate.

Revision ID: 139
Revises: 138
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "139"
down_revision = "138"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("service_categories")]
    if "commission_pct" not in cols:
        op.add_column(
            "service_categories",
            sa.Column("commission_pct", sa.Numeric(5, 2), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("service_categories")]
    if "commission_pct" in cols:
        op.drop_column("service_categories", "commission_pct")
