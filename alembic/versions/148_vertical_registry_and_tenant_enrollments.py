"""Multi-vertical platform refactor — Phase 1: canonical vertical registry
extensions + per-tenant-per-vertical enrollment lifecycle + vertical audit log.

USER REQ: platform admin must be able to enable/disable a whole business
vertical, and a tenant must be able to hold independent lifecycle status
per vertical it operates in (e.g. Home Services active, Coaching suspended)
rather than one generic tenant.vertical string / tenant.status pair.

This migration is purely additive:
  - Extends the existing `verticals` table (app.engines.vertical_catalog) with
    slug/lifecycle/registration/capabilities/audit-trail columns instead of
    creating a duplicate registry table.
  - Adds `tenant_vertical_enrollments` — the new per-tenant-per-vertical
    lifecycle table (draft/submitted/under_review/changes_requested/approved/
    active/suspended/rejected), independent per vertical.
  - Adds `vertical_audit_logs` — platform-level audit trail for vertical
    enable/disable/capability changes and enrollment lifecycle transitions
    (separate from the existing tenant-scoped `tenant_audit_logs`, since
    vertical-level events are not always tied to one tenant).
  - Backfills one `tenant_vertical_enrollments` row per existing tenant from
    `tenants.vertical` + `tenants.status`, where `tenants.vertical` matches a
    real `verticals.key`. Tenants whose `vertical` does not match any known
    vertical key are intentionally NOT backfilled (left for a separate,
    explicit reconciliation report/script — fail closed, do not guess).

Revision ID: 148
Revises: 147
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "148"
down_revision = "147"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extend `verticals` (additive only) ──────────────────────────────────
    op.add_column("verticals", sa.Column("slug", sa.String(80), nullable=True))
    op.add_column("verticals", sa.Column("lifecycle_status", sa.String(20),
                  server_default="active", nullable=False))
    op.add_column("verticals", sa.Column("registration_allowed", sa.Boolean(),
                  server_default=sa.text("true"), nullable=False))
    op.add_column("verticals", sa.Column("capabilities", sa.dialects.postgresql.JSONB(),
                  nullable=True))
    op.add_column("verticals", sa.Column("onboarding_requirements", sa.dialects.postgresql.JSONB(),
                  nullable=True))
    op.add_column("verticals", sa.Column("enabled_by", sa.dialects.postgresql.UUID(as_uuid=True),
                  nullable=True))
    op.add_column("verticals", sa.Column("disabled_by", sa.dialects.postgresql.UUID(as_uuid=True),
                  nullable=True))
    op.add_column("verticals", sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("verticals", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("verticals", sa.Column("disable_reason", sa.String(500), nullable=True))

    op.execute("UPDATE verticals SET slug = key WHERE slug IS NULL")
    op.create_unique_constraint("uq_verticals_slug", "verticals", ["slug"])

    # ── tenant_vertical_enrollments ──────────────────────────────────────────
    op.create_table(
        "tenant_vertical_enrollments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspend_reason", sa.String(500), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("changes_requested_note", sa.String(1000), nullable=True),
        sa.Column("admin_notes", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "vertical_id", name="uq_tve_tenant_vertical"),
    )
    op.create_index("ix_tve_tenant_id", "tenant_vertical_enrollments", ["tenant_id"])
    op.create_index("ix_tve_vertical_id", "tenant_vertical_enrollments", ["vertical_id"])
    op.create_index("ix_tve_status", "tenant_vertical_enrollments", ["status"])

    # ── vertical_audit_logs ──────────────────────────────────────────────────
    op.create_table(
        "vertical_audit_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(60), nullable=False),
        sa.Column("before_state", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("after_state", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_val_vertical_id", "vertical_audit_logs", ["vertical_id"])
    op.create_index("ix_val_tenant_id", "vertical_audit_logs", ["tenant_id"])

    # ── Backfill: one enrollment per tenant whose `vertical` matches a real
    # vertical key. Ambiguous/unmatched tenants are intentionally skipped. ──
    op.execute("""
        INSERT INTO tenant_vertical_enrollments
            (tenant_id, vertical_id, status, requested_at, activated_at, suspended_at, suspend_reason)
        SELECT
            t.id,
            v.id,
            CASE t.status
                WHEN 'active'    THEN 'active'
                WHEN 'suspended' THEN 'suspended'
                WHEN 'trial'     THEN 'active'
                ELSE 'submitted'
            END,
            t.created_at,
            CASE WHEN t.status IN ('active', 'trial') THEN COALESCE(t.activated_at, t.created_at) ELSE NULL END,
            CASE WHEN t.status = 'suspended' THEN COALESCE(t.suspended_at, t.created_at) ELSE NULL END,
            CASE WHEN t.status = 'suspended' THEN t.suspension_reason ELSE NULL END
        FROM tenants t
        JOIN verticals v ON v.key = t.vertical
        ON CONFLICT (tenant_id, vertical_id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_val_tenant_id", table_name="vertical_audit_logs")
    op.drop_index("ix_val_vertical_id", table_name="vertical_audit_logs")
    op.drop_table("vertical_audit_logs")

    op.drop_index("ix_tve_status", table_name="tenant_vertical_enrollments")
    op.drop_index("ix_tve_vertical_id", table_name="tenant_vertical_enrollments")
    op.drop_index("ix_tve_tenant_id", table_name="tenant_vertical_enrollments")
    op.drop_table("tenant_vertical_enrollments")

    op.drop_constraint("uq_verticals_slug", "verticals", type_="unique")
    op.drop_column("verticals", "disable_reason")
    op.drop_column("verticals", "disabled_at")
    op.drop_column("verticals", "enabled_at")
    op.drop_column("verticals", "disabled_by")
    op.drop_column("verticals", "enabled_by")
    op.drop_column("verticals", "onboarding_requirements")
    op.drop_column("verticals", "capabilities")
    op.drop_column("verticals", "registration_allowed")
    op.drop_column("verticals", "lifecycle_status")
    op.drop_column("verticals", "slug")
