"""SLA breach on jobs, an admin-set penalty, and health-based suspension.

Revision ID: 321
Revises: 320

THREE THINGS HAD NOWHERE TO LIVE

1. Jobs had no SLA at all. `customer_complaints` carries real sla_status and
   deadlines; `service_jobs` carries none, so nothing could know a job was
   late. `sla_due_at` is stamped when a job is scheduled and is the only clock
   the breach sweep reads -- so a breach is decided by the date, never by when
   the sweep happened to run.

   The clock runs from the SCHEDULED SLOT, not from booking creation: a job
   booked today for next Friday must not breach on Tuesday while nothing is
   actually late. Due = end of the scheduled day + `sla_breach_hours`.

2. The penalty is admin policy, not a constant. It lives on the monetization
   policy so it is drafted, validated, published and audited exactly like a
   commission rate -- and so changing it can be reviewed and rolled back.
   `sla_penalty_to_customer` decides whether the amount taken from the provider
   is issued to the customer as service credit (spendable on their next
   booking) or simply withdrawn.

3. Suspension needed an END. `tenants.suspended_at` records that a suspension
   happened but not when it lifts, so nothing could reinstate anyone.
   `suspended_until` is that date, and `health_reinstatement_score` is what
   health is rebaselined to when it passes.

WHY HEALTH IS REBASELINED

Health is 20% of provider matching, the joint-largest weight. A provider
suspended for low health has no jobs for three months, so their health cannot
recover -- it is computed from work they are not doing. Reinstating them at
the same score would re-suspend them immediately, forever. On reinstatement
health is lifted to a level that wins some work again, so they can earn their
way back up or down on merit.
"""
from alembic import op

revision = "321"
down_revision = "320"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Jobs get an SLA ───────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE service_jobs
        ADD COLUMN IF NOT EXISTS sla_due_at     TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS sla_breached_at TIMESTAMPTZ NULL
    """)
    # The sweep asks one question: which live jobs are now past due?
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_service_jobs_sla_due
        ON service_jobs (sla_due_at)
        WHERE sla_due_at IS NOT NULL AND sla_breached_at IS NULL
    """)

    # ── 2. The penalty and the suspension rule are admin policy ──────────────
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD COLUMN IF NOT EXISTS sla_breach_hours            INTEGER        NULL,
        ADD COLUMN IF NOT EXISTS sla_penalty_amount          NUMERIC(12,2)  NULL,
        ADD COLUMN IF NOT EXISTS sla_penalty_to_customer     BOOLEAN        NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS sla_penalty_debt_cap        NUMERIC(12,2)  NULL,
        ADD COLUMN IF NOT EXISTS health_suspension_threshold NUMERIC(6,2)   NULL,
        ADD COLUMN IF NOT EXISTS health_suspension_days      INTEGER        NULL,
        ADD COLUMN IF NOT EXISTS health_reinstatement_score  NUMERIC(6,2)   NULL
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_sla_penalty CHECK (
            (sla_breach_hours   IS NULL OR sla_breach_hours   > 0) AND
            (sla_penalty_amount IS NULL OR sla_penalty_amount >= 0) AND
            (sla_penalty_debt_cap IS NULL OR sla_penalty_debt_cap >= 0) AND
            (health_suspension_days IS NULL OR health_suspension_days > 0)
        )
    """)

    # ── 3. A suspension needs an end date ────────────────────────────────────
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN IF NOT EXISTS suspended_until  TIMESTAMPTZ  NULL,
        ADD COLUMN IF NOT EXISTS suspension_reason VARCHAR(200) NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tenants_suspended_until
        ON tenants (suspended_until)
        WHERE suspended_until IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tenants_suspended_until")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS suspension_reason")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS suspended_until")
    op.execute("ALTER TABLE vertical_monetization_policies DROP CONSTRAINT IF EXISTS ck_vmp_sla_penalty")
    for col in ("sla_breach_hours", "sla_penalty_amount", "sla_penalty_to_customer",
                "sla_penalty_debt_cap", "health_suspension_threshold",
                "health_suspension_days", "health_reinstatement_score"):
        op.execute(f"ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS {col}")
    op.execute("DROP INDEX IF EXISTS ix_service_jobs_sla_due")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS sla_breached_at")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS sla_due_at")
