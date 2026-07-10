"""Phase 3 pricing certification — completed_job_deduction_credits column,
bargain_rules table, provider_pricing_overrides table.

1. completed_job_deduction_credits on service_pricing_rules: closes the
   Phase 0/3 baseline requirement ("Completed Job Deduction = 21 usage
   credits") which was never actually implemented as a schema field —
   confirmed absent via research before this sprint. Explicitly usage-credit
   denominated, never cash (ServiceOS business rule: provider usage credits
   are internal platform credits only, never cash/wallet/payout).

2. bargain_rules: new table — no bargain negotiation system existed at all
   prior to this sprint (only a bare bargain_floor value on the pricing
   rule, with no evaluation logic/table/service/router).

3. provider_pricing_overrides: new table — tenant-scoped price overrides
   with an approval workflow, must never violate platform min/max.

Revision ID: 111
Revises: 110
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "111"
down_revision = "110"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    cols = {c["name"] for c in inspector.get_columns("service_pricing_rules")}
    if "completed_job_deduction_credits" not in cols:
        op.add_column(
            "service_pricing_rules",
            sa.Column("completed_job_deduction_credits", sa.Integer(), nullable=False, server_default="0"),
        )

    existing_tables = set(inspector.get_table_names())

    if "bargain_rules" not in existing_tables:
        op.create_table(
            "bargain_rules",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("vertical_key", sa.String(50), nullable=True),
            sa.Column("category_id", UUID(as_uuid=True), nullable=True),
            sa.Column("master_service_id", UUID(as_uuid=True), nullable=True),
            sa.Column("pricing_rule_id", UUID(as_uuid=True),
                      sa.ForeignKey("service_pricing_rules.id", ondelete="CASCADE"), nullable=True),
            sa.Column("rule_name", sa.String(200), nullable=True),
            sa.Column("rule_code", sa.String(80), nullable=True),
            sa.Column("bargain_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("floor_type", sa.String(20), nullable=False, server_default="fixed"),
            sa.Column("floor_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("below_floor_action", sa.String(20), nullable=False, server_default="reject"),
            sa.Column("provider_approval_required", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("max_attempts", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_bargain_rules_pricing_rule", "bargain_rules", ["pricing_rule_id"])
        op.create_index("ix_bargain_rules_master_service", "bargain_rules", ["master_service_id"])
        op.create_index("ix_bargain_rules_status", "bargain_rules", ["status"])

    if "provider_pricing_overrides" not in existing_tables:
        op.create_table(
            "provider_pricing_overrides",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
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
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_ppo_tenant", "provider_pricing_overrides", ["tenant_id"])
        op.create_index("ix_ppo_master_service", "provider_pricing_overrides", ["master_service_id"])
        op.create_index("ix_ppo_approval_status", "provider_pricing_overrides", ["approval_status"])


def downgrade() -> None:
    op.drop_table("provider_pricing_overrides")
    op.drop_table("bargain_rules")
    op.drop_column("service_pricing_rules", "completed_job_deduction_credits")
