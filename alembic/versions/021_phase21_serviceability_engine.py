"""Phase 21 — Serviceability Engine: customer addresses, tenant service areas,
service area mappings, audit log, and booking serviceability columns.

Revision ID: 021
Revises: 020
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_addresses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("address_line_1", sa.String(300), nullable=False),
        sa.Column("address_line_2", sa.String(300), nullable=True),
        sa.Column("landmark", sa.String(200), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("country", sa.String(50), nullable=False, server_default="India"),
        sa.Column("zipcode", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_ca_customer_active", "customer_addresses", ["customer_id", "is_active"])
    op.create_index("ix_ca_customer_default", "customer_addresses", ["customer_id", "is_default"])
    op.create_index("ix_ca_city_zip", "customer_addresses", ["city", "zipcode"])

    op.create_table(
        "tenant_service_areas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("coverage_type", sa.String(20), nullable=False),
        sa.Column("country", sa.String(50), nullable=False, server_default="India"),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("zipcode", sa.String(20), nullable=True),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("zone_name", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("radius_km", sa.Numeric(8, 2), nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("tenant_id", "coverage_type", "city", "zipcode", name="uq_tsa_tenant_coverage"),
    )
    op.create_index("ix_tsa_tenant_city", "tenant_service_areas", ["tenant_id", "city", "is_active"])
    op.create_index("ix_tsa_tenant_zip", "tenant_service_areas", ["tenant_id", "zipcode", "is_active"])

    op.create_table(
        "tenant_service_area_services",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_service_area_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("is_available", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("sla_minutes", sa.Integer, nullable=True),
        sa.Column("min_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
    )
    op.create_index("ix_tsas_area_available", "tenant_service_area_services",
                     ["tenant_service_area_id", "is_available"])
    op.create_index("ix_tsas_service_type", "tenant_service_area_services",
                     ["service_id", "job_type", "is_available"])
    op.create_index("ix_tsas_tenant", "tenant_service_area_services", ["tenant_id", "is_available"])

    op.create_table(
        "serviceability_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("address_id", UUID(as_uuid=True), nullable=True),
        sa.Column("service_id", UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(30), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("zipcode", sa.String(20), nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("matched_tenants_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("best_match_level", sa.String(20), nullable=True),
        sa.Column("request_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("response_payload", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_sal_customer", "serviceability_audit_logs", ["customer_id"])
    op.create_index("ix_sal_city_zip", "serviceability_audit_logs", ["city", "zipcode"])
    op.create_index("ix_sal_created_at", "serviceability_audit_logs", ["created_at"])

    # Booking serviceability columns
    op.add_column("bookings", sa.Column("address_id", UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("matched_service_area_id", UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("coverage_match_level", sa.String(20), nullable=True))
    op.add_column("bookings", sa.Column("service_id", UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("job_type", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "job_type")
    op.drop_column("bookings", "service_id")
    op.drop_column("bookings", "coverage_match_level")
    op.drop_column("bookings", "matched_service_area_id")
    op.drop_column("bookings", "address_id")

    op.drop_table("serviceability_audit_logs")
    op.drop_table("tenant_service_area_services")
    op.drop_table("tenant_service_areas")
    op.drop_table("customer_addresses")
