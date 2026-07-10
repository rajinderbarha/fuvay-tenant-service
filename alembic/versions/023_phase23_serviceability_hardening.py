"""Phase 23 — Serviceability hardening: partial unique indexes + missing
composite indexes for customer_addresses, tenant_service_areas, and
tenant_service_area_services (Step 2 — Coverage Foundation gap-closing).

Revision ID: 023
Revises: 022
"""
from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # customer_addresses — one default active address per customer
    op.create_index(
        "uq_ca_one_default_active", "customer_addresses", ["customer_id"],
        unique=True, postgresql_where=sa.text("is_default = true AND is_active = true"),
    )

    # tenant_service_areas — additional composite lookups
    op.create_index("ix_tsa_city_zip", "tenant_service_areas", ["city", "zipcode"])
    op.create_index(
        "ix_tsa_tenant_coverage_city_zip", "tenant_service_areas",
        ["tenant_id", "coverage_type", "city", "zipcode"],
    )

    # tenant_service_area_services — tenant+service+job_type lookup,
    # and exactly one active mapping per area+service+job_type
    op.create_index(
        "ix_tsas_tenant_service_job", "tenant_service_area_services",
        ["tenant_id", "service_id", "job_type"],
    )
    op.create_index(
        "uq_tsas_active_mapping", "tenant_service_area_services",
        ["tenant_service_area_id", "service_id", "job_type"],
        unique=True, postgresql_where=sa.text("is_available = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_tsas_active_mapping", table_name="tenant_service_area_services")
    op.drop_index("ix_tsas_tenant_service_job", table_name="tenant_service_area_services")
    op.drop_index("ix_tsa_tenant_coverage_city_zip", table_name="tenant_service_areas")
    op.drop_index("ix_tsa_city_zip", table_name="tenant_service_areas")
    op.drop_index("uq_ca_one_default_active", table_name="customer_addresses")
