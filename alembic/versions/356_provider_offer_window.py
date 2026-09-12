"""Give each provider offer a stable 15-minute assignment window.

Revision ID: 356
Revises: 355
"""
from alembic import op

revision = "356"
down_revision = "355"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE service_bookings
        ADD COLUMN IF NOT EXISTS source_channel VARCHAR(20) NULL,
        ADD COLUMN IF NOT EXISTS source_actor_id VARCHAR(120) NULL
    """)
    op.execute("""
        UPDATE service_bookings b
        SET source_channel = t.channel, source_actor_id = t.channel_user_id
        FROM messaging_threads t
        WHERE b.source_channel IS NULL AND b.ai_session_id = t.ai_session_id
          AND b.customer_id = t.customer_id
          AND t.channel IN ('instagram', 'whatsapp')
    """)
    op.execute("""
        ALTER TABLE service_jobs
        ADD COLUMN IF NOT EXISTS provider_offer_started_at TIMESTAMPTZ NULL
    """)
    # Existing open work receives a fresh window on deployment. Historical
    # completed/cancelled jobs do not need a provider-offer timestamp.
    op.execute("""
        UPDATE service_jobs SET provider_offer_started_at = now()
        WHERE provider_offer_started_at IS NULL
          AND tenant_id IS NOT NULL AND assigned_staff_id IS NULL
          AND status IN ('pending_assignment', 'accepted')
    """)
    op.execute("""
        ALTER TABLE service_jobs
        ALTER COLUMN provider_offer_started_at SET DEFAULT now()
    """)
    op.execute("""
        UPDATE vertical_monetization_policies p
        SET assignment_timeout_minutes = 15
        FROM verticals v
        WHERE p.vertical_id = v.id AND v.key = 'home_services'
          AND p.is_current = true AND p.assignment_timeout_minutes = 30
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ALTER COLUMN assignment_timeout_minutes SET DEFAULT 15
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ALTER COLUMN assignment_timeout_minutes SET DEFAULT 30
    """)
    op.execute("""
        ALTER TABLE service_jobs DROP COLUMN IF EXISTS provider_offer_started_at
    """)
    op.execute("""
        ALTER TABLE service_bookings
        DROP COLUMN IF EXISTS source_actor_id,
        DROP COLUMN IF EXISTS source_channel
    """)
