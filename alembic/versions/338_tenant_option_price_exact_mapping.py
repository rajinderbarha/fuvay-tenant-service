"""Scope tenant Service Option pricing to the exact Job-Type mapping.

Revision ID: 338
Revises: 337
"""
from alembic import op


revision = "338"
down_revision = "337"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_tsso_tenant_service_option",
        "tenant_supported_service_options",
        type_="unique",
    )
    op.execute("""
        CREATE UNIQUE INDEX uq_tsso_tenant_mapping_active
          ON tenant_supported_service_options (tenant_id, service_option_mapping_id)
          WHERE deleted_at IS NULL AND service_option_mapping_id IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_tsso_tenant_legacy_option_active
          ON tenant_supported_service_options (tenant_id, master_service_id, service_option_id)
          WHERE deleted_at IS NULL AND service_option_mapping_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index(
        "uq_tsso_tenant_legacy_option_active",
        table_name="tenant_supported_service_options",
    )
    op.drop_index(
        "uq_tsso_tenant_mapping_active",
        table_name="tenant_supported_service_options",
    )
    op.create_unique_constraint(
        "uq_tsso_tenant_service_option",
        "tenant_supported_service_options",
        ["tenant_id", "master_service_id", "service_option_id"],
    )
