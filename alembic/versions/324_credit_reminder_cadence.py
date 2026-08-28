"""Remind a provider to top up, at a rate matched to how bad it is.

Revision ID: 324
Revises: 323

WHY NOT A FIXED EVERY-TWO-HOURS

Twelve notifications a day, indefinitely, is how a provider learns to mute the
channel -- and they mute all of it, including the job assignment that arrives
next. The cadence is tied to severity instead, so the platform still gets to be
loud at the point where it is actually blocking someone's business:

  low       balance under the warning threshold      once a day
  blocked   under the floor, no new bookings          every 6 hours
  arrears   negative, or the team suspended           every 2 hours

All three are admin policy, and unset means the default above.

`last_credit_reminder_at` and `credit_reminder_level` are what make it a
cadence rather than a flood. The level is stored as well as the time so that
CROSSING into a worse state notifies immediately rather than waiting out the
previous tier's interval -- the moment bookings stop is the moment worth
telling someone about, not six hours later.

Both clear when the balance recovers, so a provider who tops up is not chased
by a reminder queued before they paid.
"""
from alembic import op

revision = "324"
down_revision = "323"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE tenant_billing
        ADD COLUMN IF NOT EXISTS last_credit_reminder_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS credit_reminder_level   VARCHAR(20) NULL
    """)
    # The sweep asks one question: who is due a reminder?
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tenant_billing_reminder_due
        ON tenant_billing (last_credit_reminder_at)
        WHERE credit_reminder_level IS NOT NULL
    """)

    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD COLUMN IF NOT EXISTS credit_reminder_hours_low     INTEGER NULL,
        ADD COLUMN IF NOT EXISTS credit_reminder_hours_blocked INTEGER NULL,
        ADD COLUMN IF NOT EXISTS credit_reminder_hours_arrears INTEGER NULL
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        DROP CONSTRAINT IF EXISTS ck_vmp_reminder_hours
    """)
    op.execute("""
        ALTER TABLE vertical_monetization_policies
        ADD CONSTRAINT ck_vmp_reminder_hours CHECK (
            (credit_reminder_hours_low     IS NULL OR credit_reminder_hours_low     > 0) AND
            (credit_reminder_hours_blocked IS NULL OR credit_reminder_hours_blocked > 0) AND
            (credit_reminder_hours_arrears IS NULL OR credit_reminder_hours_arrears > 0)
        )
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE vertical_monetization_policies DROP CONSTRAINT IF EXISTS ck_vmp_reminder_hours")
    for col in ("credit_reminder_hours_low", "credit_reminder_hours_blocked",
                "credit_reminder_hours_arrears"):
        op.execute(f"ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS {col}")
    op.execute("DROP INDEX IF EXISTS ix_tenant_billing_reminder_due")
    op.execute("ALTER TABLE tenant_billing DROP COLUMN IF EXISTS credit_reminder_level")
    op.execute("ALTER TABLE tenant_billing DROP COLUMN IF EXISTS last_credit_reminder_at")
