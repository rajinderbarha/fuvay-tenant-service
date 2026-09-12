"""Daily SLA penalties and verified technician arrival.

Revision ID: 355
Revises: 354

Only jobs whose SLA is stamped after this migration are enrolled. Existing
overdue jobs are deliberately not backfilled, so deployment cannot create
surprise retroactive deductions.
"""
from alembic import op


revision = "355"
down_revision = "354"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE service_jobs
        ADD COLUMN IF NOT EXISTS sla_enforcement_started_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS sla_next_penalty_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS sla_penalty_day_count INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS sla_stopped_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS arrival_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS arrival_distance_meters NUMERIC(10,2) NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_service_jobs_sla_daily_due
        ON service_jobs (sla_next_penalty_at)
        WHERE sla_enforcement_started_at IS NOT NULL
          AND sla_stopped_at IS NULL
          AND sla_next_penalty_at IS NOT NULL
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD COLUMN IF NOT EXISTS sla_penalty_max_days INTEGER NOT NULL DEFAULT 3,
        ADD COLUMN IF NOT EXISTS assignment_timeout_enabled BOOLEAN NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS assignment_timeout_minutes INTEGER NOT NULL DEFAULT 30,
        ADD COLUMN IF NOT EXISTS customer_reschedule_limit INTEGER NOT NULL DEFAULT 3,
        ADD COLUMN IF NOT EXISTS arrival_verification_enabled BOOLEAN NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS arrival_radius_meters INTEGER NOT NULL DEFAULT 250,
        ADD COLUMN IF NOT EXISTS arrival_location_max_age_seconds INTEGER NOT NULL DEFAULT 120,
        ADD COLUMN IF NOT EXISTS arrival_max_accuracy_meters INTEGER NOT NULL DEFAULT 100,
        ADD COLUMN IF NOT EXISTS false_arrival_auto_close BOOLEAN NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS false_arrival_penalty_amount NUMERIC(12,2) NOT NULL DEFAULT 150,
        ADD COLUMN IF NOT EXISTS false_arrival_health_weight NUMERIC(6,2) NOT NULL DEFAULT 3
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty_max_days
    """)
    for constraint in (
        "ck_vmp_assignment_timeout_minutes", "ck_vmp_customer_reschedule_limit",
        "ck_vmp_arrival_radius_meters", "ck_vmp_arrival_location_age",
        "ck_vmp_arrival_accuracy", "ck_vmp_false_arrival_penalty",
        "ck_vmp_false_arrival_health_weight",
    ):
        op.execute(
            f"ALTER TABLE vertical_monetization_policies "
            f"DROP CONSTRAINT IF EXISTS {constraint}"
        )
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_sla_penalty_max_days
        CHECK (sla_penalty_max_days BETWEEN 1 AND 30)
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_assignment_timeout_minutes CHECK (assignment_timeout_minutes BETWEEN 1 AND 1440),
        ADD CONSTRAINT ck_vmp_customer_reschedule_limit CHECK (customer_reschedule_limit BETWEEN 0 AND 20),
        ADD CONSTRAINT ck_vmp_arrival_radius_meters CHECK (arrival_radius_meters BETWEEN 25 AND 5000),
        ADD CONSTRAINT ck_vmp_arrival_location_age CHECK (arrival_location_max_age_seconds BETWEEN 15 AND 3600),
        ADD CONSTRAINT ck_vmp_arrival_accuracy CHECK (arrival_max_accuracy_meters BETWEEN 5 AND 1000),
        ADD CONSTRAINT ck_vmp_false_arrival_penalty CHECK (false_arrival_penalty_amount >= 0),
        ADD CONSTRAINT ck_vmp_false_arrival_health_weight CHECK (false_arrival_health_weight BETWEEN 0 AND 20)
    """)
    # Requested Home Services policy: Rs.50 on each breached day and close
    # after the third charge (Rs.150 before any configured debt cap).
    op.execute("""
        UPDATE vertical_monetization_policies p
        SET provider_chargeable_event = 'job_completed',
            sla_breach_hours = 24, sla_penalty_type = 'fixed', sla_penalty_amount = 50,
            sla_penalty_max_days = 3, sla_auto_cancel = true,
            sla_penalty_debt_cap = GREATEST(COALESCE(sla_penalty_debt_cap, 150), 150)
        FROM verticals v
        WHERE p.vertical_id = v.id AND v.key = 'home_services'
          AND p.is_current = true
    """)
    op.execute("""
        UPDATE home_services_activation_finance_policies p
        SET credit_booking_floor = 500
        FROM verticals v
        WHERE p.vertical_id = v.id AND v.key = 'home_services'
          AND p.is_current = true
    """)
    op.execute("""
        UPDATE monetization_job_type_rules r
        SET sla_penalty_enabled = true, sla_penalty_amount = 50,
            provider_chargeable_event = CASE
                WHEN jt.key = 'consultation' THEN 'consultation_completed'
                ELSE 'job_completed' END
        FROM vertical_monetization_policies p, verticals v, job_types jt
        WHERE r.policy_id = p.id AND p.vertical_id = v.id
          AND r.job_type_id = jt.id
          AND v.key = 'home_services' AND p.is_current = true
    """)


def downgrade() -> None:
    for constraint in (
        "ck_vmp_assignment_timeout_minutes", "ck_vmp_customer_reschedule_limit",
        "ck_vmp_arrival_radius_meters", "ck_vmp_arrival_location_age",
        "ck_vmp_arrival_accuracy", "ck_vmp_false_arrival_penalty",
        "ck_vmp_false_arrival_health_weight",
    ):
        op.execute(f"ALTER TABLE vertical_monetization_policies DROP CONSTRAINT IF EXISTS {constraint}")
    op.execute("ALTER TABLE vertical_monetization_policies DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty_max_days")
    for column in (
        "false_arrival_health_weight", "false_arrival_penalty_amount",
        "false_arrival_auto_close", "arrival_max_accuracy_meters",
        "arrival_location_max_age_seconds", "arrival_radius_meters",
        "arrival_verification_enabled", "customer_reschedule_limit",
        "assignment_timeout_minutes", "assignment_timeout_enabled",
        "sla_penalty_max_days",
    ):
        op.execute(f"ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS {column}")
    op.execute("DROP INDEX IF EXISTS ix_service_jobs_sla_daily_due")
    for column in (
        "arrival_distance_meters", "arrival_verified_at", "sla_stopped_at",
        "sla_penalty_day_count", "sla_next_penalty_at", "sla_enforcement_started_at",
    ):
        op.execute(f"ALTER TABLE service_jobs DROP COLUMN IF EXISTS {column}")
