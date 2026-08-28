"""Put every part of the SLA penalty under admin control.

Revision ID: 322
Revises: 321

WHAT WAS STILL HARDCODED

Migration 321 made the penalty's timing, amount, destination and debt cap
admin policy. Six things were still decided in code:

  * a breach ALWAYS cancelled the job, so a penalty could not be applied
    without also releasing the customer;
  * the penalty was a flat amount, so abandoning a Rs.50,000 job cost the same
    as abandoning a Rs.500 one;
  * there was no per-job-type override, though commission has had one for a
    while -- a consultation and a full installation were judged alike;
  * the provider was never told they had been charged; they found out from
    their balance;
  * which job statuses could breach was a tuple in a module;
  * and a penalty charged in error could not be undone.

DEFAULTS PRESERVE TODAY'S BEHAVIOUR

`sla_auto_cancel` and `sla_notify_provider` default true, `sla_penalty_type`
defaults to 'fixed', and every override column is NULL. A policy that is not
re-published behaves exactly as it does now.

WAIVER

A charged penalty is never edited or deleted -- the ledger is append-only and
is what an operator has to defend. A waiver posts a COMPENSATING credit and
stamps `sla_penalty_waived_at` so the same breach cannot be waived twice.
Customer credit issued from that penalty is revoked only to the extent it is
still unspent: money the customer has already used on a booking is theirs, and
clawing it back would punish them for the provider's failure.
"""
from alembic import op

revision = "322"
down_revision = "321"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Policy: every lever an operator needs ────────────────────────────────
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD COLUMN IF NOT EXISTS sla_auto_cancel        BOOLEAN       NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS sla_notify_provider    BOOLEAN       NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS sla_penalty_type       VARCHAR(20)   NOT NULL DEFAULT 'fixed',
        ADD COLUMN IF NOT EXISTS sla_penalty_percentage NUMERIC(6,3)  NULL,
        ADD COLUMN IF NOT EXISTS sla_penalty_min        NUMERIC(12,2) NULL,
        ADD COLUMN IF NOT EXISTS sla_penalty_max        NUMERIC(12,2) NULL,
        ADD COLUMN IF NOT EXISTS sla_breachable_statuses JSONB        NULL
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty_type
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_sla_penalty_type CHECK (
            sla_penalty_type IN ('fixed', 'percentage')
            AND (sla_penalty_percentage IS NULL
                 OR (sla_penalty_percentage >= 0 AND sla_penalty_percentage <= 100))
            AND (sla_penalty_min IS NULL OR sla_penalty_min >= 0)
            AND (sla_penalty_max IS NULL OR sla_penalty_max >= 0)
        )
    """)

    # ── Per-job-type override, mirroring how commission already works ────────
    op.execute("""
        ALTER TABLE monetization_job_type_rules
        ADD COLUMN IF NOT EXISTS sla_penalty_enabled BOOLEAN       NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS sla_penalty_amount  NUMERIC(12,2) NULL
    """)

    # ── Waiver: recorded on the job, never by editing the ledger ─────────────
    op.execute("""
        ALTER TABLE service_jobs
        ADD COLUMN IF NOT EXISTS sla_penalty_waived_at TIMESTAMPTZ  NULL,
        ADD COLUMN IF NOT EXISTS sla_penalty_charged   NUMERIC(12,2) NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS sla_penalty_charged")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS sla_penalty_waived_at")
    for col in ("sla_penalty_enabled", "sla_penalty_amount"):
        op.execute(f"ALTER TABLE monetization_job_type_rules DROP COLUMN IF EXISTS {col}")
    op.execute("ALTER TABLE vertical_monetization_policies DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty_type")
    for col in ("sla_auto_cancel", "sla_notify_provider", "sla_penalty_type",
                "sla_penalty_percentage", "sla_penalty_min", "sla_penalty_max",
                "sla_breachable_statuses"):
        op.execute(f"ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS {col}")
