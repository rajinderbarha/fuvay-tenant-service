"""Fund dispute settlements from credit only, and retire the warranty deposit.

Revision ID: 318
Revises: 317

317 removed the deposit that gated ACTIVATION. A second, older deposit lived
in platform_commerce — `security_deposits`, described in its own model as
"Per-tenant security deposit. Funds warranty claims. 5% of each credit
purchase replenishes." That is the pot a dispute settlement drew from when
the tenant's wallet could not cover a customer refund.

Settlement offered three funding strategies (`deduction_source`):

    tenant_wallet
    security_deposit
    tenant_wallet_then_security_deposit

Two of them no longer have a pot to draw from, so this collapses funding to
credit alone. The consequence is deliberate and is the point of the new
model: a settlement larger than the tenant's balance now drives that balance
NEGATIVE rather than quietly consuming collateral. A negative balance is
below `credit_booking_floor`, so the tenant stops receiving new bookings
until they top up — the platform recovers the full amount instead of being
capped at whatever the deposit happened to hold.

`dispute_settlements.security_deposit_deduction_amount` is dropped rather
than kept at zero: a column that can only ever be 0.00 invites code to keep
branching on it. Settlement totals are unaffected — the amount simply moves
into the wallet deduction it always sat beside.
"""
from alembic import op

revision = "318"
down_revision = "317"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Collapse any historical strategy to credit-only ───────────────────
    # Runs before the tables go so nothing is left pointing at a pot that no
    # longer exists.
    op.execute("""
        UPDATE dispute_settlements
           SET deduction_source = 'tenant_wallet'
         WHERE deduction_source IN ('security_deposit', 'tenant_wallet_then_security_deposit')
    """)

    # Fold any deposit-funded portion into the wallet deduction so settlement
    # totals still reconcile after the column is dropped.
    op.execute("""
        UPDATE dispute_settlements
           SET tenant_wallet_deduction_amount =
                 COALESCE(tenant_wallet_deduction_amount, 0)
               + COALESCE(security_deposit_deduction_amount, 0)
         WHERE COALESCE(security_deposit_deduction_amount, 0) <> 0
    """)

    op.execute("""
        ALTER TABLE dispute_settlements
            DROP COLUMN IF EXISTS security_deposit_deduction_amount
    """)

    # ── 2. Retire the per-vertical toggle for deposit adjustment ─────────────
    op.execute("""
        ALTER TABLE finance_vertical_configs
            DROP COLUMN IF EXISTS security_deposit_adjustment_enabled
    """)

    # ── 2b. Warranty claims recovered from credit alone ──────────────────────
    op.execute("""
        UPDATE warranty_claims
           SET provider_credit_deducted =
                 COALESCE(provider_credit_deducted, 0)
               + COALESCE(security_deposit_deducted, 0)
         WHERE COALESCE(security_deposit_deducted, 0) <> 0
    """)
    op.execute("ALTER TABLE warranty_claims DROP COLUMN IF EXISTS security_deposit_deducted")

    # ── 3. Drop the warranty deposit itself ──────────────────────────────────
    # Adjustments first: its rows reference a settlement and a deposit, and it
    # is the leaf of the three.
    op.execute("DROP TABLE IF EXISTS security_deposit_adjustments")
    op.execute("DROP TABLE IF EXISTS security_deposit_transactions")
    op.execute("DROP TABLE IF EXISTS security_deposits")


def downgrade() -> None:
    # Restores the columns and empty tables. The deposit BALANCES they held
    # cannot be reconstructed — the money they tracked was folded into wallet
    # deductions by upgrade() and there is no record of the original split.
    op.execute("""
        ALTER TABLE dispute_settlements
            ADD COLUMN IF NOT EXISTS security_deposit_deduction_amount NUMERIC(12,2) NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE finance_vertical_configs
            ADD COLUMN IF NOT EXISTS security_deposit_adjustment_enabled BOOLEAN NOT NULL DEFAULT TRUE
    """)
    op.execute("""
        ALTER TABLE warranty_claims
            ADD COLUMN IF NOT EXISTS security_deposit_deducted NUMERIC(12,2)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS security_deposits (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID          NOT NULL,
            required_amount     NUMERIC(10,2) NOT NULL,
            total_paid          NUMERIC(10,2) NOT NULL DEFAULT 0,
            warranty_drawn      NUMERIC(10,2) NOT NULL DEFAULT 0,
            replenishment_total NUMERIC(10,2) NOT NULL DEFAULT 0,
            status              VARCHAR(20)   NOT NULL DEFAULT 'unpaid',
            paid_at             TIMESTAMPTZ,
            razorpay_order_id   VARCHAR(100),
            razorpay_payment_id VARCHAR(100),
            refunded_at         TIMESTAMPTZ,
            package_purchase_id UUID,
            payment_reference   VARCHAR(200),
            hold_state          VARCHAR(20),
            rejection_reason    VARCHAR(500),
            clarification_notes TEXT,
            approved_by         UUID,
            approved_at         TIMESTAMPTZ,
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CONSTRAINT uq_deposit_tenant UNIQUE (tenant_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS security_deposit_transactions (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            deposit_id     UUID          NOT NULL,
            tenant_id      UUID          NOT NULL,
            txn_type       VARCHAR(30)   NOT NULL,
            amount         NUMERIC(12,2) NOT NULL,
            balance_before NUMERIC(12,2),
            balance_after  NUMERIC(12,2),
            reference_id   VARCHAR(100),
            notes          TEXT,
            actor_id       UUID,
            created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS security_deposit_adjustments (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID          NOT NULL,
            settlement_id        UUID,
            dispute_id           UUID,
            adjustment_type      VARCHAR(40)   NOT NULL,
            amount               NUMERIC(12,2) NOT NULL,
            currency             VARCHAR(3)    NOT NULL DEFAULT 'INR',
            reason               TEXT,
            status               VARCHAR(20)   NOT NULL DEFAULT 'pending',
            approved_by_admin_id UUID,
            approved_at          TIMESTAMPTZ,
            executed_at          TIMESTAMPTZ,
            created_at           TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ   NOT NULL DEFAULT now()
        )
    """)
