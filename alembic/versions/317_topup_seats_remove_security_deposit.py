"""Replace the security deposit with an admin-managed top-up plan that sells seats.

Revision ID: 317
Revises: 316

WHAT CHANGES

The security deposit is removed entirely. In its place, a Home Services
tenant buys a TOP-UP PLAN: an admin-authored row carrying a price and a
number of technician seats. Paying for it grants wallet credit (base amount
only — GST never enters the wallet, unchanged) and the seats that let the
tenant add technicians.

WHY THE DEPOSIT CANNOT SIMPLY BE DELETED

A deposit is collateral: held, never spent, so it is still there on the day
something goes wrong. Credit is consumable — `deduct_for_completed_job`
spends it on commission after every completed job. Deleting the deposit and
relying on "we will deduct from credit" would mean that by the time a
deduction is needed, the balance is whatever commission left behind, quite
possibly zero.

Two thresholds on the single balance close that gap without freezing money
the tenant paid for:

  credit_warning_threshold  notify the tenant to top up
  credit_booking_floor      below this, no NEW bookings are accepted;
                            jobs already in flight finish normally

Nothing is locked. The floor stops the hole being dug deeper, so there is
always something left to deduct against. Penalty deductions may still take
the balance negative (the ledger already supports allow_negative), and a
negative balance suspends the workspace — which recovers more than a fixed
deposit ever could.

DATA

`activation_payment_orders` is deliberately NOT dropped: it is the payment
audit trail, including a real captured gateway payment. Only the deposit
STATE tables go. Existing deposit orders remain readable as history; their
`payment_kind = 'security_deposit'` simply stops being produced.
"""
from alembic import op

revision = "317"
down_revision = "316"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Admin-authored top-up plan catalogue ──────────────────────────────
    # A catalogue of rows rather than a versioned policy: an admin creates
    # "₹5,000 / 3 seats" once and edits or retires it. What a tenant actually
    # paid is snapshotted onto their payment order, so re-pricing a plan can
    # never rewrite what someone already bought.
    op.execute("""
        CREATE TABLE IF NOT EXISTS hs_topup_plans (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            vertical_id     UUID         NOT NULL,
            name            VARCHAR(120) NOT NULL,
            description     TEXT,
            base_amount     NUMERIC(12,2) NOT NULL,
            gst_percent     NUMERIC(6,3)  NOT NULL DEFAULT 18,
            -- Seats this plan grants. One seat = one technician the tenant
            -- may add = one more job bookable per slot, since slot capacity
            -- is already derived from ready technicians.
            seats           INTEGER      NOT NULL,
            currency        VARCHAR(3)   NOT NULL DEFAULT 'INR',
            is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
            -- Offered to a tenant that has never bought one. At most one per
            -- vertical, enforced by the partial index below.
            is_default      BOOLEAN      NOT NULL DEFAULT FALSE,
            sort_order      INTEGER      NOT NULL DEFAULT 0,
            created_by      UUID,
            meta            JSONB        NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            CONSTRAINT ck_hs_topup_plan_amount   CHECK (base_amount > 0),
            CONSTRAINT ck_hs_topup_plan_gst      CHECK (gst_percent >= 0 AND gst_percent <= 100),
            CONSTRAINT ck_hs_topup_plan_seats    CHECK (seats >= 0),
            CONSTRAINT uq_hs_topup_plan_name     UNIQUE (vertical_id, name)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_hs_topup_plan_active
            ON hs_topup_plans (vertical_id, is_active, sort_order)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_hs_topup_plan_default
            ON hs_topup_plans (vertical_id) WHERE is_default = TRUE
    """)

    # ── 2. Snapshot what was bought onto the payment order ───────────────────
    # Seats are granted at capture, from the plan as it was priced then.
    op.execute("ALTER TABLE activation_payment_orders ADD COLUMN IF NOT EXISTS topup_plan_id UUID")
    op.execute("ALTER TABLE activation_payment_orders ADD COLUMN IF NOT EXISTS seats_granted INTEGER")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_apo_topup_plan
            ON activation_payment_orders (topup_plan_id)
    """)

    # ── 3. Tenant seat entitlement ───────────────────────────────────────────
    # Denormalised running total, rebuilt from captured orders. Kept on
    # tenant_billing because that is already the canonical home of
    # credit_balance, and seats and credit are bought in the same transaction.
    op.execute("ALTER TABLE tenant_billing ADD COLUMN IF NOT EXISTS entitled_seats INTEGER NOT NULL DEFAULT 0")

    # ── 4. Finance policy: deposit out, credit thresholds in ─────────────────
    op.execute("""
        ALTER TABLE home_services_activation_finance_policies
            ADD COLUMN IF NOT EXISTS credit_warning_threshold NUMERIC(12,2) NOT NULL DEFAULT 1000,
            ADD COLUMN IF NOT EXISTS credit_booking_floor     NUMERIC(12,2) NOT NULL DEFAULT 500,
            -- 'cumulative'  : every purchase adds its seats (default)
            -- 'highest_plan': entitlement is the largest plan ever bought
            ADD COLUMN IF NOT EXISTS seat_accrual_mode        VARCHAR(20)   NOT NULL DEFAULT 'cumulative'
    """)
    op.execute("""
        ALTER TABLE home_services_activation_finance_policies
            DROP COLUMN IF EXISTS deposit_required,
            DROP COLUMN IF EXISTS deposit_calculation_mode,
            DROP COLUMN IF EXISTS deposit_amount_per_technician,
            DROP COLUMN IF EXISTS minimum_deposit,
            DROP COLUMN IF EXISTS technician_count_policy
    """)

    # ── 5. Drop the ACTIVATION deposit state ─────────────────────────────────
    # Scope note: this migration removes the deposit that gated ACTIVATION.
    # A second, older deposit system also exists in platform_commerce
    # (`security_deposits` / `security_deposit_transactions` /
    # `security_deposit_adjustments`), which funds warranty claims and is the
    # pot that `DisputeSettlement.security_deposit_deduction_amount` draws
    # from. Removing it means rewiring dispute settlement to deduct from
    # credit instead — real money math that deserves its own migration rather
    # than being tacked on here. Those three tables are left standing and are
    # removed in 318, once the dispute path reads credit.
    op.execute("DROP TABLE IF EXISTS hs_deposit_refund_requests")

    op.execute("""
        ALTER TABLE tenant_billing
            DROP COLUMN IF EXISTS security_deposit_paid,
            DROP COLUMN IF EXISTS security_deposit_amount
    """)

    # ── 6. Seed the starter plan: Rs.5,000 + 18% GST = Rs.5,900, 3 seats ─────
    # Three seats matches the worked example: three technicians, three jobs
    # bookable in one slot. An admin can edit or retire this immediately; it
    # exists so a fresh environment is never left with an empty catalogue and
    # no way for a tenant to activate.
    op.execute("""
        INSERT INTO hs_topup_plans
            (vertical_id, name, description, base_amount, gst_percent, seats,
             is_active, is_default, sort_order)
        SELECT v.id,
               'Starter — 3 seats',
               'Rs.5,000 + 18% GST. Grants Rs.5,000 usable credit and 3 technician seats.',
               5000, 18, 3, TRUE, TRUE, 10
        FROM verticals v
        WHERE v.key = 'home_services'
        ON CONFLICT ON CONSTRAINT uq_hs_topup_plan_name DO NOTHING
    """)

    # Align the published finance policy with the new starter price so the
    # activation flow quotes Rs.5,000, not the old Rs.1,000.
    op.execute("""
        UPDATE home_services_activation_finance_policies
           SET credit_package_base_amount = 5000,
               credited_wallet_amount     = 5000
         WHERE credit_package_base_amount = 1000
    """)


def downgrade() -> None:
    # Deliberately partial: the dropped deposit tables held a state machine
    # that no longer has any code behind it, so recreating empty shells would
    # be misleading. This restores the columns and removes what was added.
    op.execute("""
        ALTER TABLE tenant_billing
            ADD COLUMN IF NOT EXISTS security_deposit_paid   BOOLEAN       NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS security_deposit_amount NUMERIC(10,2) NOT NULL DEFAULT 0
    """)
    op.execute("ALTER TABLE tenant_billing DROP COLUMN IF EXISTS entitled_seats")
    op.execute("""
        ALTER TABLE home_services_activation_finance_policies
            ADD COLUMN IF NOT EXISTS deposit_required              BOOLEAN       NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS deposit_calculation_mode      VARCHAR(30)   NOT NULL DEFAULT 'per_technician',
            ADD COLUMN IF NOT EXISTS deposit_amount_per_technician NUMERIC(12,2) NOT NULL DEFAULT 2000,
            ADD COLUMN IF NOT EXISTS minimum_deposit               NUMERIC(12,2) NOT NULL DEFAULT 2000,
            ADD COLUMN IF NOT EXISTS technician_count_policy       VARCHAR(50)   NOT NULL DEFAULT 'home_services_active_technicians_only',
            DROP COLUMN IF EXISTS credit_warning_threshold,
            DROP COLUMN IF EXISTS credit_booking_floor,
            DROP COLUMN IF EXISTS seat_accrual_mode
    """)
    op.execute("ALTER TABLE activation_payment_orders DROP COLUMN IF EXISTS topup_plan_id")
    op.execute("ALTER TABLE activation_payment_orders DROP COLUMN IF EXISTS seats_granted")
    op.execute("DROP TABLE IF EXISTS hs_topup_plans")
