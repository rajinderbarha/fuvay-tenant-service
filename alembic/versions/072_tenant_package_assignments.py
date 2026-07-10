"""072 — tenant_package_assignments: package lifecycle starts only after admin approval.

Creates tenant_package_assignments table.
Adds selected_package_id to public_registration sessions (no schema column — stored in Redis).

Revision ID: 072
Revises: 071
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None

STATUSES = "selected|pending_review|pending_payment|paid_pending_approval|active|expired|cancelled|refunded|rejected"


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, name)


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"), {"n": name}
    ).scalar()
    return result is not None


def upgrade() -> None:
    if not _table_exists("tenant_package_assignments"):
        op.create_table(
            "tenant_package_assignments",
            sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                       server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id",   postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("package_id",  postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("package_type", sa.String(30), nullable=False),

            # Lifecycle status
            # selected | pending_review | pending_payment | paid_pending_approval
            # active | expired | cancelled | refunded | rejected
            sa.Column("status", sa.String(30), nullable=False, server_default="selected"),

            # Timestamps — starts_at / expires_at MUST remain NULL until admin approval
            sa.Column("selected_at",  sa.DateTime(timezone=True), nullable=True),
            sa.Column("paid_at",      sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_at",  sa.DateTime(timezone=True), nullable=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("starts_at",    sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at",   sa.DateTime(timezone=True), nullable=True),

            # Package snapshot at time of selection
            sa.Column("validity_days",               sa.Integer,          nullable=True),
            sa.Column("billing_cycle",               sa.String(20),       nullable=True),
            sa.Column("price_amount",                sa.Numeric(12, 2),   nullable=False, server_default="0"),
            sa.Column("security_deposit_amount",     sa.Numeric(12, 2),   nullable=True),
            sa.Column("included_spendable_credits",  sa.Numeric(12, 2),   nullable=True),
            sa.Column("lead_credits",                sa.Integer,          nullable=True),

            # Payment linkage
            sa.Column("payment_reference_id", sa.String(200), nullable=True),

            # Audit metadata
            sa.Column("metadata_json", postgresql.JSONB,                 nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

            sa.ForeignKeyConstraint(["tenant_id"],  ["tenants.id"],          ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["package_id"], ["service_packages.id"], ondelete="SET NULL"),
        )

    for idx_name, col in [
        ("ix_tpa_tenant_id",  "tenant_id"),
        ("ix_tpa_package_id", "package_id"),
        ("ix_tpa_status",     "status"),
    ]:
        if not _index_exists(idx_name):
            op.create_index(idx_name, "tenant_package_assignments", [col])


def downgrade() -> None:
    pass  # additive — no destructive downgrade
