"""MODULE-L5-02 — AI settlement policy rules (admin sets the rule; the rest is automatic).

Business rules being encoded:
  * AI settlement is NOT started by hand. It starts automatically once the
    PROVIDER has failed to solve the complaint (no response inside the SLA, or
    the customer rejected what they offered).
  * The AI may only offer up to a capped share of the job's value (default 25%).
  * If the case is strong enough to warrant MORE than the cap, the AI must not
    settle it — the complaint is escalated to admin manual review instead.
  * Compensation is paid in CREDIT POINTS, never real money. Cash refunds are not
    an option the AI is allowed to reach for; non-monetary remedies (rework,
    callback, apology) are.
  * The admin only configures the rule; everything else runs automatically.

These columns hang off the existing complaint_policies table so the rule is
resolvable per tenant/category, with the platform default as the fallback.

Revision ID: 138
Revises: 137
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "138"
down_revision = "137"
branch_labels = None
depends_on = None

# The remedies the AI is allowed to propose. Deliberately excludes every
# monetary/cash option — the platform never settles a dispute with real money.
DEFAULT_ALLOWED_REMEDIES = ["credit_points", "rework", "callback", "apology", "no_action"]


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("complaint_policies")]

    def add(name: str, col: sa.Column) -> None:
        if name not in cols:
            op.add_column("complaint_policies", col)

    add("ai_settlement_enabled", sa.Column(
        "ai_settlement_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # Auto-start the AI once the provider has failed to solve it.
    add("ai_auto_start_on_provider_failure", sa.Column(
        "ai_auto_start_on_provider_failure", sa.Boolean(), nullable=False,
        server_default=sa.text("true")))

    # Max share of the job value the AI may offer (percent). Above this the case
    # goes to a human.
    add("ai_settlement_max_pct", sa.Column(
        "ai_settlement_max_pct", sa.Numeric(5, 2), nullable=False,
        server_default=sa.text("25.00")))

    # Whitelist of remedies the AI may propose. Never contains cash/refund.
    add("ai_settlement_allowed_remedies", sa.Column(
        "ai_settlement_allowed_remedies", JSONB(), nullable=True))

    # Settlement compensation is paid as customer credit points, not money.
    add("settlement_payout_in_credits_only", sa.Column(
        "settlement_payout_in_credits_only", sa.Boolean(), nullable=False,
        server_default=sa.text("true")))

    conn.execute(
        sa.text("""
            UPDATE complaint_policies
               SET ai_settlement_allowed_remedies = CAST(:remedies AS JSONB)
             WHERE ai_settlement_allowed_remedies IS NULL
        """),
        {"remedies": '["credit_points", "rework", "callback", "apology", "no_action"]'},
    )


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("complaint_policies")]
    for name in (
        "settlement_payout_in_credits_only",
        "ai_settlement_allowed_remedies",
        "ai_settlement_max_pct",
        "ai_auto_start_on_provider_failure",
        "ai_settlement_enabled",
    ):
        if name in cols:
            op.drop_column("complaint_policies", name)
