"""Remove the leaked plumbing problem from non-plumbing services.

Revision ID: 367
Revises: 366
"""
from alembic import op


revision = "367"
down_revision = "366"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A previously archived/duplicated mapping on staging attached Dripping
    # tap to Air Conditioner. The problem itself is valid and remains active
    # for Plumbing; only cross-service mappings are retired. Runtime queries
    # also require deleted_at IS NULL, so this repair is durable and auditable.
    op.execute("""
        UPDATE service_issue_mappings sim
           SET status = 'inactive',
               customer_visible = false,
               deleted_at = COALESCE(sim.deleted_at, now()),
               updated_at = now()
          FROM master_issue_types issue, master_services service
         WHERE sim.issue_type_id = issue.id
           AND sim.master_service_id = service.id
           AND (
                lower(COALESCE(issue.code, '')) = 'dripping_tap'
                OR lower(COALESCE(issue.slug, '')) IN ('dripping_tap', 'dripping-tap')
                OR lower(COALESCE(issue.name, '')) = 'dripping tap'
           )
           AND lower(COALESCE(service.slug, '')) <> 'plumbing'
           AND lower(COALESCE(service.service_name, '')) <> 'plumbing'
    """)


def downgrade() -> None:
    # Data-integrity repair: restoring a known-invalid cross-service mapping
    # would make the customer bug return, so downgrade is intentionally a no-op.
    pass
