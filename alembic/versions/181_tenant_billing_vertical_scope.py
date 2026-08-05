"""CREDITS-TOPUPS-MERGE: canonical Home Services credit account uniqueness.

Data-integrity requirement: one canonical credit account per
Tenant + Business Vertical. Today `tenant_billing` already has
UNIQUE(tenant_id) and `Tenant.vertical` is a single, non-nullable column
per tenant (a tenant cannot belong to two verticals in the current schema),
so UNIQUE(tenant_id) already IS equivalent to UNIQUE(tenant_id, vertical) --
no duplicate balance is possible today.

This migration makes that equivalence explicit and forward-compatible with
a future multi-vertical-per-tenant model (TenantVerticalEnrollment,
migration 179): it adds a denormalized, backfilled `vertical_key` snapshot
column and a composite unique constraint UNIQUE(tenant_id, vertical_key),
so that if a tenant is ever enrolled in a second vertical with its own
credit policy, that vertical's credit account is guaranteed to be a
*separate* row rather than silently sharing/overwriting Home Services'
balance. Disabling Home Services therefore structurally cannot affect
another vertical's balance -- there is no shared row to affect.

Purely additive; no existing balance is moved, split, or renamed.

Revision ID: 181
Revises: 180
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "181"
down_revision = "180"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant_billing", sa.Column("vertical_key", sa.String(50), nullable=True))
    op.execute("""
        UPDATE tenant_billing tb
        SET vertical_key = t.vertical
        FROM tenants t
        WHERE t.id = tb.tenant_id AND tb.vertical_key IS NULL
    """)
    # One canonical credit account per Tenant + Business Vertical. The
    # existing uq_tbl_tenant (tenant_id alone) is left in place -- it is a
    # strict subset of this constraint under today's one-vertical-per-tenant
    # schema and removing it is out of scope for this additive migration.
    op.create_unique_constraint(
        "uq_tenant_billing_tenant_vertical", "tenant_billing", ["tenant_id", "vertical_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tenant_billing_tenant_vertical", "tenant_billing", type_="unique")
    op.drop_column("tenant_billing", "vertical_key")
