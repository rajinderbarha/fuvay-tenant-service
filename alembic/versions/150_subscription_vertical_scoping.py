"""Phase 2 — fix Subscription's `UNIQUE(tenant_id)` constraint, the critical
gap flagged during the Phase 1 vertical-registry audit: a tenant operating in
two verticals (e.g. Home Services + Coaching) could not hold two independent
subscriptions, because `subscriptions` allowed only ONE row per tenant,
period. This makes the table vertical-aware:

  - Adds nullable `vertical_id` to subscriptions / subscription_periods /
    subscription_events (additive).
  - Backfills every existing subscription's vertical_id from the owning
    tenant's `tenants.vertical` -> `verticals.key` (same resolution rule as
    migration 148's tenant_vertical_enrollments backfill, for consistency).
  - Replaces `uq_sub_tenant` (tenant_id only) with `uq_sub_tenant_vertical`
    (tenant_id, vertical_id) so a tenant may hold one subscription PER
    vertical, while a tenant with a single vertical keeps exactly the same
    one-subscription behavior as before (existing behavior unchanged for the
    common case; net-new behavior only unlocked when a second vertical_id is
    explicitly used).
  - Existing rows that could not be resolved to a real vertical (ambiguous
    `tenants.vertical` string) are left with vertical_id = NULL rather than
    guessed -- fail closed per the reconciliation policy from migration 148's
    audit. NULL is unique per row in Postgres, so this cannot silently merge
    two ambiguous tenants' subscriptions together.

Revision ID: 150
Revises: 149
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "150"
down_revision = "149"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column(
        "vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("subscription_periods", sa.Column(
        "vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("subscription_events", sa.Column(
        "vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))

    op.execute("""
        UPDATE subscriptions s
        SET vertical_id = v.id
        FROM tenants t JOIN verticals v ON v.key = t.vertical
        WHERE s.tenant_id = t.id
    """)
    op.execute("""
        UPDATE subscription_periods sp
        SET vertical_id = s.vertical_id
        FROM subscriptions s
        WHERE sp.subscription_id = s.id
    """)
    op.execute("""
        UPDATE subscription_events se
        SET vertical_id = s.vertical_id
        FROM subscriptions s
        WHERE se.subscription_id = s.id
    """)

    op.drop_constraint("uq_sub_tenant", "subscriptions", type_="unique")
    op.create_unique_constraint(
        "uq_sub_tenant_vertical", "subscriptions", ["tenant_id", "vertical_id"])
    op.create_index("ix_sub_vertical_id", "subscriptions", ["vertical_id"])
    op.create_index("ix_sp_vertical_id", "subscription_periods", ["vertical_id"])
    op.create_index("ix_se_vertical_id", "subscription_events", ["vertical_id"])


def downgrade() -> None:
    op.drop_index("ix_se_vertical_id", table_name="subscription_events")
    op.drop_index("ix_sp_vertical_id", table_name="subscription_periods")
    op.drop_index("ix_sub_vertical_id", table_name="subscriptions")
    op.drop_constraint("uq_sub_tenant_vertical", "subscriptions", type_="unique")
    op.create_unique_constraint("uq_sub_tenant", "subscriptions", ["tenant_id"])
    op.drop_column("subscription_events", "vertical_id")
    op.drop_column("subscription_periods", "vertical_id")
    op.drop_column("subscriptions", "vertical_id")
