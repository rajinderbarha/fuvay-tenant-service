"""Fix schema gaps: brands.description + service_packages table

Revision ID: 062
Revises: 061
Create Date: 2026-07-03
"""
from __future__ import annotations
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "062"
down_revision = "061"
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
    # ── brands: add missing columns ────────────────────────────────────────────
    if not _col_exists(conn, "brands", "description"):
        op.add_column("brands", sa.Column("description", sa.Text(), nullable=True))
    if not _col_exists(conn, "brands", "deleted_at"):
        op.add_column("brands", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ── master_service_brands: add is_default ──────────────────────────────────
    if not _col_exists(conn, "master_service_brands", "is_default"):
        op.add_column("master_service_brands",
                      sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"))

    # ── login_events: add updated_at ───────────────────────────────────────────
    op.add_column("login_events",
                  sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True,
                            server_default=sa.text("now()")))

    # ── tenant_operational_settings: create table ──────────────────────────────
    op.create_table(
        "tenant_operational_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id",            postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("timezone",             sa.String(60),   nullable=False, server_default="Asia/Kolkata"),
        sa.Column("currency",             sa.String(10),   nullable=False, server_default="INR"),
        sa.Column("language",             sa.String(10),   nullable=False, server_default="en"),
        sa.Column("commission_rate",      sa.Numeric(5,4), nullable=False, server_default="0.1"),
        sa.Column("notify_new_booking",   sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("notify_job_completed", sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("notify_low_credit",    sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("low_credit_threshold", sa.Numeric(10,2),nullable=False, server_default="500.00"),
        sa.Column("auto_accept_bookings", sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("extra",                postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", name="uq_tos_tenant"),
    )

    # ── service_packages: create table ─────────────────────────────────────────
    op.create_table(
        "service_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name",                   sa.String(150), nullable=False),
        sa.Column("slug",                   sa.String(120), nullable=False, unique=True),
        sa.Column("description",            sa.Text(), nullable=True),
        sa.Column("package_type",           sa.String(30), nullable=False),
        sa.Column("plan_level",             sa.String(30), nullable=True),
        sa.Column("package_price",          sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("security_deposit_amount",sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("included_credit_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("storage_quota_gb",       sa.Numeric(10, 2), nullable=True),
        sa.Column("commission_rate",        sa.Numeric(5, 2), nullable=True),
        sa.Column("validity_days",          sa.Integer(), nullable=True),
        sa.Column("features",              postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active",             sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("display_order",         sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by",            postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",            sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_spkg_slug"),
        sa.CheckConstraint("package_price >= 0", name="ck_spkg_price"),
        sa.CheckConstraint("security_deposit_amount >= 0", name="ck_spkg_deposit"),
        sa.CheckConstraint("included_credit_amount >= 0", name="ck_spkg_credit"),
    )
    op.create_index("ix_spkg_package_type", "service_packages", ["package_type"])
    op.create_index("ix_spkg_is_active",    "service_packages", ["is_active"])
    op.create_index("ix_spkg_display_order","service_packages", ["display_order"])


def downgrade() -> None:
    op.drop_table("service_packages")
    op.drop_table("tenant_operational_settings")
    op.drop_column("login_events", "updated_at")
    op.drop_column("master_service_brands", "is_default")
    op.drop_column("brands", "deleted_at")
    op.drop_column("brands", "description")
