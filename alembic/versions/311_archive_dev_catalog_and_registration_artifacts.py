"""Archive isolated development artifacts without deleting history.

Revision ID: 311
Revises: 310

Several native projection and login certification tests had been run against
the shared development database without cleanup. Their unmistakable synthetic
rows were appearing in real admin/catalog lists. This migration soft-archives
only rows carrying the test-only identities and only when no provider has
published the synthetic service.
"""
from alembic import op
import sqlalchemy as sa


revision = "311"
down_revision = "310"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    archived_services = connection.execute(sa.text("""
        UPDATE master_services ms
           SET is_active = FALSE,
               deleted_at = COALESCE(ms.deleted_at, now()),
               updated_at = now()
         WHERE ms.service_group_id IS NULL
           AND ms.service_name = 'AC'
           AND ms.slug ~ '^ac-[0-9a-f]{6}$'
           AND NOT EXISTS (
               SELECT 1 FROM tenant_services ts
                WHERE ts.master_service_id = ms.id
                  AND ts.deleted_at IS NULL
           )
    """))

    synthetic_tenants = connection.execute(sa.text("""
        SELECT t.id
          FROM tenants t
          JOIN users u ON u.id = t.owner_user_id
         WHERE t.tenant_name = 'Login E2E Biz'
           AND u.email LIKE 'login_e2e_%@example.com'
           AND t.status = 'onboarding_pending'
           AND NOT EXISTS (SELECT 1 FROM tenant_services ts WHERE ts.tenant_id = t.id AND ts.deleted_at IS NULL)
           AND NOT EXISTS (SELECT 1 FROM provider_team_members ptm WHERE ptm.tenant_id = t.id AND ptm.deleted_at IS NULL)
    """
    )).scalars().all()
    if synthetic_tenants:
        connection.execute(sa.text("""
            UPDATE tenants
               SET status = 'terminated',
                   archived_at = COALESCE(archived_at, now()),
                   updated_at = now()
             WHERE id = ANY(CAST(:tenant_ids AS uuid[]))
        """), {"tenant_ids": synthetic_tenants})
        connection.execute(sa.text("""
            UPDATE users
               SET is_active = FALSE,
                   account_status = 'deactivated',
                   deactivated_at = COALESCE(deactivated_at, now()),
                   deactivation_reason = 'Archived synthetic login certification account',
                   updated_at = now()
             WHERE tenant_id = ANY(CAST(:tenant_ids AS uuid[]))
               AND email LIKE 'login_e2e_%@example.com'
        """), {"tenant_ids": synthetic_tenants})

    print(
        f"[311] archived {archived_services.rowcount or 0} synthetic service row(s) "
        f"and {len(synthetic_tenants)} synthetic tenant(s)"
    )


def downgrade() -> None:
    # These are isolated development/test identities. Re-enabling them on a
    # downgrade would republish junk into customer and admin directories.
    pass
