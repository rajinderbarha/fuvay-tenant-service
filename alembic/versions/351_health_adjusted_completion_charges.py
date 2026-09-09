"""Add versioned provider-health adjustments to completion charges.

Revision ID: 351
Revises: 350
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "351"
down_revision = "350"
branch_labels = None
depends_on = None


_DEFAULT_BANDS = (
    "'{\"platinum\": 0, \"gold\": 0, \"silver\": 2, "
    "\"watchlist\": 5, \"at_risk\": 8, \"blocked\": 10}'::jsonb"
)


def upgrade() -> None:
    # Opt-in on an explicitly published policy: adding the feature must not
    # silently change the charge on already-published immutable versions.
    op.add_column(
        "vertical_monetization_policies",
        sa.Column("provider_health_adjustment_enabled", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
    )
    op.add_column(
        "vertical_monetization_policies",
        sa.Column("provider_health_adjustments_json", JSONB(), nullable=False,
                  server_default=sa.text(_DEFAULT_BANDS)),
    )
    op.add_column(
        "vertical_monetization_policies",
        sa.Column("provider_health_score_max_age_days", sa.Integer(), nullable=False,
                  server_default=sa.text("30")),
    )
    op.add_column(
        "vertical_monetization_policies",
        sa.Column("provider_health_max_effective_percentage", sa.Numeric(6, 3), nullable=False,
                  server_default=sa.text("25")),
    )

    # Freeze every finance decision beside the append-only ledger row. This
    # makes a later health recalculation or policy version change incapable of
    # rewriting why a historical charge had its amount.
    op.add_column(
        "usage_credit_ledger",
        sa.Column("calculation_snapshot_json", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usage_credit_ledger", "calculation_snapshot_json")
    op.drop_column("vertical_monetization_policies", "provider_health_max_effective_percentage")
    op.drop_column("vertical_monetization_policies", "provider_health_score_max_age_days")
    op.drop_column("vertical_monetization_policies", "provider_health_adjustments_json")
    op.drop_column("vertical_monetization_policies", "provider_health_adjustment_enabled")
