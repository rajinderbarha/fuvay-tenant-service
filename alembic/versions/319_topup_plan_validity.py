"""Give a top-up plan a validity, and make seats expire with it.

Revision ID: 319
Revises: 318

WHY

Seats were permanent. `entitled_seats` on `tenant_billing` only ever grew
(`current + granted`), and nothing anywhere decreased it, so a single payment
bought capacity for ever. That is fine while seats are a free capacity guard
and commission is the revenue, but it makes "validity" unexpressible: there
was no record of WHICH purchase granted WHICH seats, or when they lapse.

WHAT

`hs_topup_plans.validity_days` -- 0 means the plan never expires, which is the
behaviour every existing plan has today, so the default is a no-op.

`tenant_topup_entitlements` -- one row per purchase: the seats and credit it
granted, when it starts, and when it lapses. Entitled seats become a SUM over
live rows, which can finally go DOWN. `tenant_billing.entitled_seats` stays as
a cached projection so hot paths (the header credit pill, slot search) still
read one integer instead of aggregating.

CREDIT IS CAPPED, NOT LEDGERED PER LOT

`credit_balance` remains the single spendable number -- every consumer
(job commission, invoice checkout, refunds, admin adjustment) keeps working
unchanged. A lot records what it granted and what of that is still unspent;
on expiry only the unspent remainder of PLAN-GRANTED credit is withdrawn.
Money from any other source is never touched, and the balance is never pushed
below zero, so an expiry can only ever remove credit the provider actually
still had from that specific purchase.

BACKFILL

Existing captured orders are replayed into entitlements as NON-expiring rows.
Nobody who has already paid loses a seat to this migration.
"""
from alembic import op

revision = "319"
down_revision = "318"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Plans carry a validity ────────────────────────────────────────────
    op.execute("""
        ALTER TABLE hs_topup_plans
        ADD COLUMN IF NOT EXISTS validity_days INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE hs_topup_plans
        DROP CONSTRAINT IF EXISTS ck_hs_topup_plan_validity
    """)
    op.execute("""
        ALTER TABLE hs_topup_plans
        ADD CONSTRAINT ck_hs_topup_plan_validity CHECK (validity_days >= 0)
    """)

    # ── 2. One row per purchase ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenant_topup_entitlements (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID           NOT NULL,
            plan_id           UUID           NULL,
            order_id          UUID           NULL,
            seats             INTEGER        NOT NULL DEFAULT 0,
            credit_granted    NUMERIC(12,2)  NOT NULL DEFAULT 0,
            credit_expired    NUMERIC(12,2)  NOT NULL DEFAULT 0,
            validity_days     INTEGER        NOT NULL DEFAULT 0,
            starts_at         TIMESTAMPTZ    NOT NULL DEFAULT now(),
            -- NULL means it never lapses. Every backfilled row is NULL.
            expires_at        TIMESTAMPTZ    NULL,
            status            VARCHAR(20)    NOT NULL DEFAULT 'active',
            expired_at        TIMESTAMPTZ    NULL,
            meta              JSONB          NOT NULL DEFAULT '{}'::jsonb,
            created_at        TIMESTAMPTZ    NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ    NOT NULL DEFAULT now(),
            CONSTRAINT ck_tte_seats  CHECK (seats >= 0),
            CONSTRAINT ck_tte_status CHECK (status IN ('active', 'expired'))
        )
    """)
    # The sweep asks one question: which live rows are now due?
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tte_due
        ON tenant_topup_entitlements (expires_at)
        WHERE status = 'active' AND expires_at IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tte_tenant_live
        ON tenant_topup_entitlements (tenant_id, status)
    """)
    # A captured order grants its seats exactly once, however often a webhook
    # is redelivered or a reconcile is re-run.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tte_order
        ON tenant_topup_entitlements (order_id)
        WHERE order_id IS NOT NULL
    """)

    # ── 3. Backfill what tenants already paid for ────────────────────────────
    # Replayed as non-expiring: these were sold as permanent seats and stay
    # permanent. Only purchases made AFTER this migration can lapse.
    op.execute("""
        INSERT INTO tenant_topup_entitlements
            (tenant_id, order_id, seats, credit_granted, validity_days,
             starts_at, expires_at, status, meta)
        SELECT o.tenant_id,
               o.id,
               COALESCE(o.seats_granted, 0),
               COALESCE(o.credited_amount, 0),
               0,
               COALESCE(o.captured_at, o.created_at, now()),
               NULL,
               'active',
               jsonb_build_object('backfilled_from', 'activation_payment_orders')
        FROM activation_payment_orders o
        WHERE COALESCE(o.seats_granted, 0) > 0
          AND o.status IN ('captured', 'paid', 'succeeded')
        ON CONFLICT DO NOTHING
    """)

    # Any seats on tenant_billing that no captured order explains (seeded or
    # granted by hand) become one non-expiring row, so the derived total can
    # never come out lower than what a tenant already had.
    op.execute("""
        INSERT INTO tenant_topup_entitlements
            (tenant_id, seats, credit_granted, validity_days, expires_at, status, meta)
        SELECT b.tenant_id,
               b.entitled_seats - COALESCE(e.seats, 0),
               0, 0, NULL, 'active',
               jsonb_build_object('backfilled_from', 'tenant_billing.entitled_seats')
        FROM tenant_billing b
        LEFT JOIN (
            SELECT tenant_id, SUM(seats) AS seats
            FROM tenant_topup_entitlements GROUP BY tenant_id
        ) e ON e.tenant_id = b.tenant_id
        WHERE b.entitled_seats > COALESCE(e.seats, 0)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_topup_entitlements")
    op.execute("ALTER TABLE hs_topup_plans DROP CONSTRAINT IF EXISTS ck_hs_topup_plan_validity")
    op.execute("ALTER TABLE hs_topup_plans DROP COLUMN IF EXISTS validity_days")
