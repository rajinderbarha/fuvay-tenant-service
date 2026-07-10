"""Phase 14 — Billing Router (3 tables inside Platform Commerce)
Revision ID: 014
Revises: 013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tenant_billing_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("billing_mode",           sa.String(30),      nullable=False),
        sa.Column("vertical",               sa.String(50),      nullable=False),
        sa.Column("commission_rate",        sa.Numeric(5,4),    nullable=False),
        sa.Column("commission_rate_source", sa.String(100),     nullable=True),
        sa.Column("plan_type",              sa.String(30),      nullable=True),
        sa.Column("is_active",              sa.Boolean,         nullable=False,
                  server_default="true"),
        sa.Column("activated_at",           sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deactivated_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by",           UUID(as_uuid=True), nullable=True),
        sa.Column("deactivated_by",         UUID(as_uuid=True), nullable=True),
        sa.Column("deactivation_reason",    sa.String(500),     nullable=True),
        sa.Column("meta",                   JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    # PROVEN: partial unique index — one active profile per tenant
    op.execute(
        "CREATE UNIQUE INDEX uq_tbp_tenant_active "
        "ON tenant_billing_profiles (tenant_id) "
        "WHERE is_active = true AND deactivated_at IS NULL"
    )
    op.create_index("ix_tbp_tenant",   "tenant_billing_profiles", ["tenant_id"])
    op.create_index("ix_tbp_mode",     "tenant_billing_profiles", ["billing_mode"])
    op.create_index("ix_tbp_vertical", "tenant_billing_profiles", ["vertical"])

    op.create_table("vertical_billing_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vertical",        sa.String(50),   nullable=False),
        sa.Column("plan_type",       sa.String(30),   nullable=False),
        sa.Column("billing_mode",    sa.String(30),   nullable=False),
        sa.Column("commission_rate", sa.Numeric(5,4), nullable=False),
        sa.Column("leads_per_month", JSONB,           nullable=True),
        sa.Column("jobs_per_month",  JSONB,           nullable=True),
        sa.Column("valid_from",      sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_until",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("set_by",          UUID(as_uuid=True), nullable=True),
        sa.Column("notes",           sa.String(500),  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vbc_vertical_plan", "vertical_billing_configs",
                    ["vertical","plan_type"])
    op.create_index("ix_vbc_active",        "vertical_billing_configs",
                    ["vertical","valid_until"])

    # Seed default home_services configs
    op.execute("""
        INSERT INTO vertical_billing_configs
            (vertical, plan_type, billing_mode, commission_rate, valid_from)
        VALUES
            ('home_services', 'starter',    'credit_commission', 0.1000, NOW()),
            ('home_services', 'growth',     'credit_commission', 0.0700, NOW()),
            ('home_services', 'enterprise', 'credit_commission', 0.0500, NOW()),
            ('coaching_center','starter',   'subscription_leads',0.0000, NOW()),
            ('coaching_center','growth',    'subscription_leads',0.0000, NOW()),
            ('coaching_center','enterprise','subscription_leads',0.0000, NOW())
    """)

    op.create_table("billing_router_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("billing_mode",         sa.String(30),      nullable=False),
        sa.Column("operation",            sa.String(50),      nullable=False),
        sa.Column("engine_dispatched",    sa.String(50),      nullable=False),
        sa.Column("result",               sa.String(20),      nullable=False),
        sa.Column("commission_rate_used", sa.Numeric(5,4),    nullable=True),
        sa.Column("amount",               sa.Numeric(12,2),   nullable=True),
        sa.Column("request_id",           sa.String(100),     nullable=True),
        sa.Column("context",              JSONB, nullable=False, server_default="{}"),
        sa.Column("error",                sa.String(500),     nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_brl_tenant",    "billing_router_logs", ["tenant_id"])
    op.create_index("ix_brl_mode",      "billing_router_logs", ["billing_mode"])
    op.create_index("ix_brl_operation", "billing_router_logs", ["operation"])
    op.create_index("ix_brl_created",   "billing_router_logs", ["created_at"])


def downgrade() -> None:
    for t in ["billing_router_logs","vertical_billing_configs","tenant_billing_profiles"]:
        op.drop_table(t)
    op.execute("DROP INDEX IF EXISTS uq_tbp_tenant_active")
