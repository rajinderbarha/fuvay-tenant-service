"""One-day missed-arrival SLA with a cumulative Rs.150 close penalty.

Revision ID: 365
Revises: 364
"""
from alembic import op


revision = "365"
down_revision = "364"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD COLUMN IF NOT EXISTS sla_close_after_hours INTEGER NOT NULL DEFAULT 24,
        ADD COLUMN IF NOT EXISTS sla_total_penalty_amount NUMERIC(12,2) NOT NULL DEFAULT 150
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty,
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_close_after_hours,
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_total_penalty
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_sla_penalty CHECK (
            (sla_breach_hours IS NULL OR sla_breach_hours >= 0) AND
            (sla_penalty_amount IS NULL OR sla_penalty_amount >= 0) AND
            (sla_penalty_debt_cap IS NULL OR sla_penalty_debt_cap >= 0) AND
            (health_suspension_days IS NULL OR health_suspension_days > 0)
        ),
        ADD CONSTRAINT ck_vmp_sla_close_after_hours
            CHECK (sla_close_after_hours BETWEEN 1 AND 168),
        ADD CONSTRAINT ck_vmp_sla_total_penalty
            CHECK (sla_total_penalty_amount >= 0)
    """)

    # The live and pending Home Services configurations both reflect the new
    # promise: Rs.50 when the arrival window is missed, close 24 hours later,
    # and never exceed Rs.150 total for this no-show lifecycle.
    op.execute("""
        UPDATE vertical_monetization_policies p
        SET sla_breach_hours = 0,
            sla_penalty_type = 'fixed',
            sla_penalty_amount = 50,
            sla_penalty_max_days = 1,
            sla_close_after_hours = 24,
            sla_total_penalty_amount = 150,
            sla_auto_cancel = true,
            sla_notify_provider = true,
            sla_breachable_statuses =
                '["pending_assignment","assigned","accepted","scheduled","on_the_way"]'::jsonb,
            sla_penalty_debt_cap = GREATEST(COALESCE(sla_penalty_debt_cap, 150), 150)
        FROM verticals v
        WHERE p.vertical_id = v.id AND v.key = 'home_services'
          AND (p.is_current = true OR p.status = 'draft')
    """)
    op.execute("""
        UPDATE monetization_job_type_rules r
        SET sla_penalty_enabled = true, sla_penalty_amount = 50
        FROM vertical_monetization_policies p, verticals v
        WHERE r.policy_id = p.id AND p.vertical_id = v.id
          AND v.key = 'home_services'
          AND (p.is_current = true OR p.status = 'draft')
    """)

    # A recorded arrival is success for this SLA. Repair any enrolled rows
    # that reached the customer before this release but were still ticking.
    op.execute("""
        UPDATE service_jobs
        SET sla_stopped_at = COALESCE(sla_stopped_at, arrival_verified_at, now()),
            sla_due_at = NULL, sla_next_penalty_at = NULL, updated_at = now()
        WHERE sla_enforcement_started_at IS NOT NULL
          AND sla_stopped_at IS NULL AND arrival_verified_at IS NOT NULL
    """)
    # The operator explicitly wants currently visible breached jobs governed by
    # this rule as well. Enrol every active scheduled provider job; the worker
    # recalculates its exact timestamp from the stored slot before charging, so
    # future visits remain untouched while already-late visits are actioned.
    op.execute("""
        UPDATE service_jobs
        SET sla_enforcement_started_at = COALESCE(sla_enforcement_started_at, now()),
            sla_next_penalty_at = COALESCE(sla_next_penalty_at, now()),
            updated_at = now()
        WHERE tenant_id IS NOT NULL AND scheduled_date IS NOT NULL
          AND arrival_verified_at IS NULL AND sla_stopped_at IS NULL
          AND status IN ('pending_assignment','assigned','accepted','scheduled','on_the_way')
    """)


def downgrade() -> None:
    # Zero-hour grace is valid only under this revision's constraint.
    op.execute("""
        UPDATE vertical_monetization_policies
        SET sla_breach_hours = 24
        WHERE sla_breach_hours = 0
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_total_penalty,
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_close_after_hours,
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_sla_penalty CHECK (
            (sla_breach_hours IS NULL OR sla_breach_hours > 0) AND
            (sla_penalty_amount IS NULL OR sla_penalty_amount >= 0) AND
            (sla_penalty_debt_cap IS NULL OR sla_penalty_debt_cap >= 0) AND
            (health_suspension_days IS NULL OR health_suspension_days > 0)
        )
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP COLUMN IF EXISTS sla_total_penalty_amount,
        DROP COLUMN IF EXISTS sla_close_after_hours
    """)
