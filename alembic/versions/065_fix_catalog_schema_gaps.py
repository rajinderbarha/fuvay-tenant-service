"""Fix catalog schema gaps — missing columns in master_services, pricing_tiers, service_types,
   service_pricing_rules, and tenant_services that exist in ORM models but not the DB.

Revision ID: 065
Revises: 064
Create Date: 2026-07-04
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── master_services ───────────────────────────────────────────────────────
    if not _col_exists(conn, "master_services", "icon_url"):
        op.add_column("master_services", sa.Column("icon_url", sa.String(500), nullable=True))
    if not _col_exists(conn, "master_services", "tenant_override_allowed"):
        op.add_column("master_services", sa.Column("tenant_override_allowed", sa.Boolean(), nullable=False, server_default="false"))
    if not _col_exists(conn, "master_services", "tenant_custom_name_allowed"):
        op.add_column("master_services", sa.Column("tenant_custom_name_allowed", sa.Boolean(), nullable=False, server_default="true"))
    if not _col_exists(conn, "master_services", "display_order"):
        op.add_column("master_services", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
    if not _col_exists(conn, "master_services", "deleted_at"):
        op.add_column("master_services", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ── pricing_tiers ─────────────────────────────────────────────────────────
    if not _col_exists(conn, "pricing_tiers", "deleted_at"):
        op.add_column("pricing_tiers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ── tier_locations ────────────────────────────────────────────────────────
    if not _col_exists(conn, "tier_locations", "priority"):
        op.add_column("tier_locations", sa.Column("priority", sa.Integer(), nullable=False, server_default="100"))
    if not _col_exists(conn, "tier_locations", "deleted_at"):
        op.add_column("tier_locations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    # country was VARCHAR(2) (ISO code) but model/service uses full names like "India"
    op.alter_column("tier_locations", "country", type_=sa.String(60), existing_type=sa.String(2))

    # ── service_types ─────────────────────────────────────────────────────────
    if not _col_exists(conn, "service_types", "icon_url"):
        op.add_column("service_types", sa.Column("icon_url", sa.String(500), nullable=True))
    if not _col_exists(conn, "service_types", "deleted_at"):
        op.add_column("service_types", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ── service_pricing_rules ─────────────────────────────────────────────────
    if not _col_exists(conn, "service_pricing_rules", "deleted_at"):
        op.add_column("service_pricing_rules", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ── tenant_services ───────────────────────────────────────────────────────
    if not _col_exists(conn, "tenant_services", "deleted_at"):
        op.add_column("tenant_services", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    for table, col in [
        ("master_services", "icon_url"),
        ("master_services", "tenant_override_allowed"),
        ("master_services", "tenant_custom_name_allowed"),
        ("master_services", "display_order"),
        ("master_services", "deleted_at"),
        ("pricing_tiers",   "deleted_at"),
        ("tier_locations",  "priority"),
        ("tier_locations",  "deleted_at"),
        ("service_types",   "icon_url"),
        ("service_types",   "deleted_at"),
        ("service_pricing_rules", "deleted_at"),
        ("tenant_services", "deleted_at"),
    ]:
        if _col_exists(conn, table, col):
            op.drop_column(table, col)
