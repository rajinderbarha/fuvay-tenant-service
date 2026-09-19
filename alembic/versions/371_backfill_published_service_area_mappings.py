"""Backfill active-area coverage for every published provider service.

Revision ID: 371
Revises: 370
"""
from alembic import op


revision = "371"
down_revision = "370"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Coverage in the current provider workspace is provider-wide: every
    # active pincode applies to every service the provider publishes. New
    # publishes already materialize this projection in TenantCatalogService;
    # this repairs services published before that rule existed so they become
    # visible to the same ZIP-filtered Instagram/customer catalog.
    op.execute("""
        INSERT INTO tenant_service_area_services (
            id, created_at, updated_at,
            tenant_service_area_id, tenant_id, service_id, job_type,
            is_available, status
        )
        SELECT
            gen_random_uuid(), now(), now(),
            area.id, service.tenant_id, service.master_service_id,
            service.job_type, true, 'ACTIVE'
        FROM tenant_services AS service
        JOIN tenant_service_areas AS area
          ON area.tenant_id = service.tenant_id
         AND area.is_active IS TRUE
        WHERE service.setup_status = 'published'
          AND service.is_enabled IS TRUE
          AND service.is_active IS TRUE
          AND service.deleted_at IS NULL
          AND NOT EXISTS (
              SELECT 1
              FROM tenant_service_area_services AS mapping
              WHERE mapping.tenant_service_area_id = area.id
                AND mapping.tenant_id = service.tenant_id
                AND mapping.service_id = service.master_service_id
                AND mapping.job_type = service.job_type
                AND mapping.is_available IS TRUE
          )
    """)


def downgrade() -> None:
    # Data repair is intentionally irreversible: removing these rows would
    # make legitimate published services disappear from customer booking.
    pass
