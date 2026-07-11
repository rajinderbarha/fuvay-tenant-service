"""FINAL-L5-04B — Tenant Module and Category Entitlement Architecture.

Replaces the always-NULL tenant.category_id single-value field with a real
many-to-many entitlement model:

- tenant_module_entitlements: which platform modules (verticals) a tenant
  can access, with status/effective-date lifecycle and audit fields.
- tenant_category_entitlements: which categories (service_groups) within
  an entitled module a tenant can access, FK'd to the parent module
  entitlement so a category can never outlive/bypass its module.
- entitlement_audit_log: append-only record of every entitlement mutation.

tenant.category_id is left in place (not dropped) — historical rows and
any external readers of it are unaffected; it simply stops being consumed
by new code as of this migration's companion service-layer changes.

Revision ID: 132
Revises: 131
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "132"
down_revision = "131"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenant_module_entitlements ──────────────────────────────────────────
    op.create_table(
        "tenant_module_entitlements",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id",        UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id",        UUID(as_uuid=True), sa.ForeignKey("verticals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status",           sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("source",           sa.String(40), nullable=False, server_default="admin_manual"),
        sa.Column("configuration",    JSONB, nullable=True),
        sa.Column("enabled_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by",       UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by",       UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",       sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("version",          sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE','SUSPENDED','EXPIRED','PENDING','ARCHIVED')",
            name="ck_tme_status_valid",
        ),
    )
    op.create_index("ix_tme_tenant_status", "tenant_module_entitlements", ["tenant_id", "status"])
    op.create_index("ix_tme_module_status", "tenant_module_entitlements", ["module_id", "status"])
    op.create_index("ix_tme_tenant_module", "tenant_module_entitlements", ["tenant_id", "module_id"])
    # Only one ACTIVE entitlement per (tenant, module) — disabled/expired/archived
    # rows are kept for history and do not block a fresh assignment.
    op.execute("""
        CREATE UNIQUE INDEX uq_tme_tenant_module_active
        ON tenant_module_entitlements (tenant_id, module_id)
        WHERE status = 'ACTIVE'
    """)

    # ── tenant_category_entitlements ────────────────────────────────────────
    op.create_table(
        "tenant_category_entitlements",
        sa.Column("id",                    UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id",             UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id",           UUID(as_uuid=True), sa.ForeignKey("service_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_entitlement_id", UUID(as_uuid=True), sa.ForeignKey("tenant_module_entitlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status",                sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("source",                sa.String(40), nullable=False, server_default="admin_manual"),
        sa.Column("configuration",         JSONB, nullable=True),
        sa.Column("enabled_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by",            UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by",            UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",            sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("version",               sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE','SUSPENDED','EXPIRED','PENDING','ARCHIVED')",
            name="ck_tce_status_valid",
        ),
    )
    op.create_index("ix_tce_tenant_status", "tenant_category_entitlements", ["tenant_id", "status"])
    op.create_index("ix_tce_category_status", "tenant_category_entitlements", ["category_id", "status"])
    op.create_index("ix_tce_module_entitlement", "tenant_category_entitlements", ["module_entitlement_id"])
    op.create_index("ix_tce_tenant_category", "tenant_category_entitlements", ["tenant_id", "category_id"])
    op.execute("""
        CREATE UNIQUE INDEX uq_tce_tenant_category_active
        ON tenant_category_entitlements (tenant_id, category_id)
        WHERE status = 'ACTIVE'
    """)

    # ── entitlement_audit_log ───────────────────────────────────────────────
    op.create_table(
        "entitlement_audit_log",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id",       UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type",     sa.String(20), nullable=False),   # module|category
        sa.Column("entity_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("event",           sa.String(60), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status",      sa.String(20), nullable=True),
        sa.Column("actor_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",      sa.String(40), nullable=True),
        sa.Column("reason",          sa.Text, nullable=True),
        sa.Column("source",          sa.String(40), nullable=True),
        sa.Column("request_id",      sa.String(80), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_eal_tenant_id", "entitlement_audit_log", ["tenant_id"])
    op.create_index("ix_eal_entity", "entitlement_audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_eal_created_at", "entitlement_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("entitlement_audit_log")
    op.drop_table("tenant_category_entitlements")
    op.drop_table("tenant_module_entitlements")
