"""Give every open complaint a provider resolution deadline.

The only complaint clock was the provider's first reply. After one message a
case had no deadline, no escalation and no penalty, so it could stay open
indefinitely. `provider_action_due_at` is re-stamped whenever the case returns
to the provider; `provider_action_penalized_at` makes the resolution penalty
fire once per provider turn. `complaint_resolutions.amount` records the amount
of a refund offer so accepting it can create a real refund.

Existing cases already waiting on the provider get a fresh 72-hour window from
deploy time rather than one measured from filing: back-dating the clock would
penalise every long-stuck case in the first sweep for time that no deadline
covered.

Revision ID: 376
Revises: 375
"""
from alembic import op
import sqlalchemy as sa


revision = "376"
down_revision = "375"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_complaints",
        sa.Column("provider_action_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "customer_complaints",
        sa.Column("provider_action_penalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "complaint_resolutions",
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
    )
    op.execute(sa.text(
        "UPDATE customer_complaints "
        "SET provider_action_due_at = now() + interval '72 hours' "
        "WHERE status IN ('open', 'awaiting_provider_response', "
        "'rework_approved', 'refund_approved')"
    ))
    op.create_index(
        "ix_cc_provider_action_due_at", "customer_complaints", ["provider_action_due_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cc_provider_action_due_at", table_name="customer_complaints")
    op.drop_column("complaint_resolutions", "amount")
    op.drop_column("customer_complaints", "provider_action_penalized_at")
    op.drop_column("customer_complaints", "provider_action_due_at")
