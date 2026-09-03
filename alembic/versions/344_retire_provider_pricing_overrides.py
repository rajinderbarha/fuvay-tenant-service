"""Remove the retired admin provider-price override model.

Tenant-published service pricing is the only live pricing source.

Revision ID: 344
Revises: 343
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID


revision = "344"
down_revision = "343"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "provider_pricing_overrides" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("provider_pricing_overrides")


def downgrade() -> None:
    if "provider_pricing_overrides" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "provider_pricing_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_key", sa.String(50), nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_type_id", UUID(as_uuid=True), nullable=True),
        sa.Column("brand_id", UUID(as_uuid=True), nullable=True),
        sa.Column("issue_type_id", UUID(as_uuid=True), nullable=True),
        sa.Column("zipcode", sa.String(20), nullable=True),
        sa.Column("tier_id", UUID(as_uuid=True), nullable=True),
        sa.Column("override_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=text("now()")),
    )
    op.create_index("ix_ppo_tenant", "provider_pricing_overrides", ["tenant_id"])
    op.create_index("ix_ppo_master_service", "provider_pricing_overrides", ["master_service_id"])
    op.create_index("ix_ppo_approval_status", "provider_pricing_overrides", ["approval_status"])
