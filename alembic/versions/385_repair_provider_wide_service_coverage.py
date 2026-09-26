"""Repair provider-wide coverage for every published service.

Revision ID: 385
Revises: 384
"""
from alembic import op


revision = "385"
down_revision = "384"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The retired per-service coverage UI could leave an unavailable row for
    # a service/area pair.  Reactivate one canonical row when no active row
    # exists, then create any genuinely missing projections.  Matching still
    # enforces publication, pricing, technician, trust and live-slot gates.
    op.execute("""
        WITH eligible AS (
            SELECT mapping.id,
                   row_number() OVER (
                       PARTITION BY mapping.tenant_service_area_id,
                                    mapping.tenant_id,
                                    mapping.service_id,
                                    mapping.job_type
                       ORDER BY mapping.created_at DESC, mapping.id DESC
                   ) AS rank_in_pair,
                   bool_or(mapping.is_available) OVER (
                       PARTITION BY mapping.tenant_service_area_id,
                                    mapping.tenant_id,
                                    mapping.service_id,
                                    mapping.job_type
                   ) AS has_active
              FROM tenant_service_area_services AS mapping
              JOIN tenant_service_areas AS area
                ON area.id = mapping.tenant_service_area_id
               AND area.tenant_id = mapping.tenant_id
               AND area.is_active IS TRUE
              JOIN tenant_services AS service
                ON service.tenant_id = mapping.tenant_id
               AND service.master_service_id = mapping.service_id
               AND service.job_type = mapping.job_type
               AND service.setup_status = 'published'
               AND service.is_enabled IS TRUE
               AND service.is_active IS TRUE
               AND service.deleted_at IS NULL
        )
        UPDATE tenant_service_area_services AS mapping
           SET is_available = true, status = 'ACTIVE', updated_at = now()
          FROM eligible
         WHERE mapping.id = eligible.id
           AND eligible.rank_in_pair = 1
           AND eligible.has_active IS FALSE
    """)
    op.execute("""
        INSERT INTO tenant_service_area_services (
            id, created_at, updated_at,
            tenant_service_area_id, tenant_id, service_id, job_type,
            is_available, status
        )
        SELECT gen_random_uuid(), now(), now(),
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
    # Deliberately irreversible data repair. Reverting would hide legitimate
    # published services from customers in an active provider-wide area.
    pass
