"""HS5B — Availability break/lunch + exceptions/holidays + booking-window
settings + per-area type/brand coverage.

1. provider_availability_rules: adds break_start_time/break_end_time
   (nullable — both-or-neither, enforced at the application layer since
   Postgres CHECK constraints can't easily express "both null or both
   set" across two nullable varchar columns portably with the existing
   style used elsewhere in this codebase), max_jobs_per_day, timezone
   (default 'Asia/Kolkata' — safe for existing rows), emergency_available.
2. New table tenant_availability_exceptions (holidays/one-off closures).
3. New table tenant_booking_window_settings (one row per tenant,
   safe defaults matching the ticket's exact suggested values).
4. tenant_service_area_services: adds service_type_id/brand_id (nullable)
   so per-area coverage can be type/brand-scoped, reusing the same
   pattern established in migration 120 for tenant_service_brands.

All additions are nullable or have safe defaults — existing rows remain
valid with no data migration needed.

Revision ID: 121
Revises: 120
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "121"
down_revision = "120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Availability break/lunch + related fields
    par_columns = {c["name"] for c in inspector.get_columns("provider_availability_rules")}
    if "break_start_time" not in par_columns:
        op.add_column("provider_availability_rules", sa.Column("break_start_time", sa.String(8), nullable=True))
    if "break_end_time" not in par_columns:
        op.add_column("provider_availability_rules", sa.Column("break_end_time", sa.String(8), nullable=True))
    if "max_jobs_per_day" not in par_columns:
        op.add_column("provider_availability_rules", sa.Column("max_jobs_per_day", sa.Integer(), nullable=True))
    if "timezone" not in par_columns:
        op.add_column("provider_availability_rules", sa.Column(
            "timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"))
    if "emergency_available" not in par_columns:
        op.add_column("provider_availability_rules", sa.Column(
            "emergency_available", sa.Boolean(), nullable=False, server_default="false"))

    # 2. Exceptions / holidays
    if "tenant_availability_exceptions" not in inspector.get_table_names():
        op.create_table(
            "tenant_availability_exceptions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("reason", sa.String(255), nullable=False),
            sa.Column("full_day_closed", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("start_time", sa.String(8), nullable=True),
            sa.Column("end_time", sa.String(8), nullable=True),
            sa.Column("affected_service_area_ids", postgresql.JSONB(), nullable=True),
            sa.Column("affected_service_ids", postgresql.JSONB(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_tae_tenant_date", "tenant_availability_exceptions", ["tenant_id", "date"])

    # 3. Booking-window settings (one row per tenant, safe ticket-specified defaults)
    if "tenant_booking_window_settings" not in inspector.get_table_names():
        op.create_table(
            "tenant_booking_window_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("minimum_notice_minutes", sa.Integer(), nullable=False, server_default="120"),
            sa.Column("maximum_advance_booking_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("buffer_minutes_between_jobs", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("allow_same_day_booking", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("emergency_booking_allowed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # 4. Per-area type/brand coverage
    tsas_columns = {c["name"] for c in inspector.get_columns("tenant_service_area_services")}
    if "service_type_id" not in tsas_columns:
        op.add_column("tenant_service_area_services", sa.Column("service_type_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "brand_id" not in tsas_columns:
        op.add_column("tenant_service_area_services", sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True))
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("tenant_service_area_services")}
    if "ix_tsas_type_brand" not in existing_indexes:
        op.create_index("ix_tsas_type_brand", "tenant_service_area_services", ["service_type_id", "brand_id"])


def downgrade() -> None:
    op.drop_index("ix_tsas_type_brand", table_name="tenant_service_area_services")
    op.drop_column("tenant_service_area_services", "brand_id")
    op.drop_column("tenant_service_area_services", "service_type_id")
    op.drop_table("tenant_booking_window_settings")
    op.drop_index("ix_tae_tenant_date", table_name="tenant_availability_exceptions")
    op.drop_table("tenant_availability_exceptions")
    op.drop_column("provider_availability_rules", "emergency_available")
    op.drop_column("provider_availability_rules", "timezone")
    op.drop_column("provider_availability_rules", "max_jobs_per_day")
    op.drop_column("provider_availability_rules", "break_end_time")
    op.drop_column("provider_availability_rules", "break_start_time")
