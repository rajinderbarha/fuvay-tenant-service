"""P0 Tenant 360 fix — bookability_audit_logs table.

The admin Bookability tab (frontend/super-admin tenants/[id] detail page,
"bookability" tab) and provider_portal/admin_router.py
GET /v1/admin/bookability/providers/{tenant_id}/audit-logs both already
query this table, but it was never created by a migration — causing a
500 on every load of that tab. This adds the table with the columns the
existing query already selects.

Revision ID: 130
Revises: 129
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "130"
down_revision = "129"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # provider_visibility_statuses exists (Sprint 12) but is missing the
    # override reason columns the admin Bookability tab already reads/writes
    # (ProviderVisibilityStatus.override_visible_reason / override_bookable_reason).
    pvs_cols = {c["name"] for c in inspector.get_columns("provider_visibility_statuses")} \
        if "provider_visibility_statuses" in inspector.get_table_names() else set()
    if pvs_cols and "override_visible_reason" not in pvs_cols:
        op.add_column("provider_visibility_statuses", sa.Column("override_visible_reason", sa.Text(), nullable=True))
    if pvs_cols and "override_bookable_reason" not in pvs_cols:
        op.add_column("provider_visibility_statuses", sa.Column("override_bookable_reason", sa.Text(), nullable=True))

    if "bookability_audit_logs" not in inspector.get_table_names():
        op.create_table(
            "bookability_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("trigger_source", sa.String(50), nullable=True),
            sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("actor_type", sa.String(30), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_bookability_audit_logs_tenant_id", "bookability_audit_logs", ["tenant_id"])
        op.create_index("ix_bookability_audit_logs_created_at", "bookability_audit_logs", ["created_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "bookability_audit_logs" in inspector.get_table_names():
        op.drop_table("bookability_audit_logs")
