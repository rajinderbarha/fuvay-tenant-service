"""Aggregate failed postcode checks outside booking drafts.

Revision ID: 352
Revises: 351
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "352"
down_revision = "351"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_service_area_demand_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("day_bucket", sa.Date(), nullable=False),
        sa.Column("zipcode", sa.String(20), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("category_key", sa.String(120), nullable=False, server_default=""),
        sa.Column("category_name", sa.String(160), nullable=True),
        sa.Column("service_key", sa.String(160), nullable=False, server_default=""),
        sa.Column("service_name", sa.String(200), nullable=True),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False, server_default="no_coverage"),
        sa.Column("check_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_checked_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint(
            "day_bucket", "zipcode", "category_key", "service_key", "channel", "outcome",
            name="uq_hs_area_demand_daily_dimension",
        ),
    )
    op.create_index(
        "ix_hs_area_demand_zip_day", "home_service_area_demand_signals",
        ["zipcode", "day_bucket"],
    )
    op.create_index(
        "ix_hs_area_demand_last_checked", "home_service_area_demand_signals",
        ["last_checked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_hs_area_demand_last_checked", table_name="home_service_area_demand_signals")
    op.drop_index("ix_hs_area_demand_zip_day", table_name="home_service_area_demand_signals")
    op.drop_table("home_service_area_demand_signals")
