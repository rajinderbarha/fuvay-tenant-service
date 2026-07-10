"""Add service-level fields to city_tier_configs + update unique constraint.

Revision ID: 067
Revises: 066
Create Date: 2026-07-04

Adds optional service-specific pricing fields so admins can define
rules at the service level (not just category-level).
Existing rows are unaffected (all new columns nullable/have defaults).
"""
from alembic import op
import sqlalchemy as sa

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns (all nullable/with defaults for backward compat)
    op.add_column("city_tier_configs",
        sa.Column("service_name", sa.String(200), nullable=True, comment="Optional: restricts rule to specific service"))
    op.add_column("city_tier_configs",
        sa.Column("min_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("city_tier_configs",
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("city_tier_configs",
        sa.Column("default_estimate", sa.Numeric(10, 2), nullable=True))
    op.add_column("city_tier_configs",
        sa.Column("visit_fee", sa.Numeric(10, 2), nullable=True))
    op.add_column("city_tier_configs",
        sa.Column("bargain_floor", sa.Numeric(10, 2), nullable=True))
    op.add_column("city_tier_configs",
        sa.Column("provider_override_allowed", sa.Boolean(), nullable=False,
                  server_default="true"))

    # Back-fill service_name to empty string so the new unique constraint works
    op.execute("UPDATE city_tier_configs SET service_name = '' WHERE service_name IS NULL")
    op.alter_column("city_tier_configs", "service_name", nullable=False, server_default="")

    # Drop old unique constraint and create a new one that includes service_name
    op.drop_constraint("uq_ctc_city_category", "city_tier_configs", type_="unique")
    op.create_unique_constraint(
        "uq_ctc_city_category_service",
        "city_tier_configs",
        ["city_name", "service_category", "service_name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_ctc_city_category_service", "city_tier_configs", type_="unique")
    op.create_unique_constraint("uq_ctc_city_category", "city_tier_configs",
                                ["city_name", "service_category"])
    op.drop_column("city_tier_configs", "provider_override_allowed")
    op.drop_column("city_tier_configs", "bargain_floor")
    op.drop_column("city_tier_configs", "visit_fee")
    op.drop_column("city_tier_configs", "default_estimate")
    op.drop_column("city_tier_configs", "max_price")
    op.drop_column("city_tier_configs", "min_price")
    op.drop_column("city_tier_configs", "service_name")
