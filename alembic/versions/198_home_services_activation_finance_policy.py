"""HOME-SERVICES-FINANCE-POLICY-01: canonical versioned activation finance policy.

Replaces hardcoded SECURITY_DEPOSIT_PER_TECHNICIAN/CREDIT_PACKAGE_BASE_AMOUNT/
CREDIT_PACKAGE_GST_PERCENT constants (activation_deposit_policy.py) with a
real, admin-configurable, draft/published/retired versioned record —
same idiom as vertical_monetization_policies (version_number + status +
is_current unique partial index).

Revision ID: 198
Revises: 197
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "198"
down_revision = "197"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_services_activation_finance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vertical_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),

        sa.Column("deposit_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deposit_calculation_mode", sa.String(30), nullable=False, server_default="per_technician"),
        sa.Column("deposit_amount_per_technician", sa.Numeric(12, 2), nullable=False, server_default="2000"),
        sa.Column("minimum_deposit", sa.Numeric(12, 2), nullable=False, server_default="2000"),
        sa.Column("technician_count_policy", sa.String(50), nullable=False,
                  server_default="home_services_active_technicians_only"),

        sa.Column("initial_credit_purchase_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("credit_package_base_amount", sa.Numeric(12, 2), nullable=False, server_default="1000"),
        sa.Column("credit_package_gst_percent", sa.Numeric(6, 3), nullable=False, server_default="18"),
        sa.Column("credited_wallet_amount", sa.Numeric(12, 2), nullable=False, server_default="1000"),

        sa.Column("completion_deduction_policy", sa.String(60), nullable=True),

        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_hsafp_vertical", "home_services_activation_finance_policies", ["vertical_id"])
    op.create_index("ix_hsafp_vertical_current", "home_services_activation_finance_policies",
                     ["vertical_id"], unique=True, postgresql_where=sa.text("is_current = true"))
    op.create_index("ix_hsafp_vertical_version", "home_services_activation_finance_policies",
                     ["vertical_id", "version_number"], unique=True)
    op.create_index("ix_hsafp_status", "home_services_activation_finance_policies", ["status"])

    # Seed one published v1 policy for the real home_services vertical row,
    # preserving today's live-verified numbers (₹2000/technician, ₹1000 base
    # + 18% GST) so activation math does not change for any tenant -- only
    # its source of truth moves from a hardcoded constants file to this table.
    op.execute("""
        INSERT INTO home_services_activation_finance_policies
            (id, vertical_id, version_number, status, is_current,
             deposit_required, deposit_calculation_mode, deposit_amount_per_technician, minimum_deposit,
             technician_count_policy,
             initial_credit_purchase_required, credit_package_base_amount, credit_package_gst_percent,
             credited_wallet_amount, completion_deduction_policy, currency, effective_from,
             change_summary, published_at, created_at, updated_at)
        SELECT gen_random_uuid(), v.id, 1, 'published', true,
               true, 'per_technician', 2000, 2000,
               'home_services_active_technicians_only',
               true, 1000, 18,
               1000, 'usage_credit_per_completed_job', 'INR', now(),
               'Initial published policy — migrated from hardcoded activation_deposit_policy.py constants.',
               now(), now(), now()
        FROM verticals v
        WHERE v.key = 'home_services'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_hsafp_status", table_name="home_services_activation_finance_policies")
    op.drop_index("ix_hsafp_vertical_version", table_name="home_services_activation_finance_policies")
    op.drop_index("ix_hsafp_vertical_current", table_name="home_services_activation_finance_policies")
    op.drop_index("ix_hsafp_vertical", table_name="home_services_activation_finance_policies")
    op.drop_table("home_services_activation_finance_policies")
