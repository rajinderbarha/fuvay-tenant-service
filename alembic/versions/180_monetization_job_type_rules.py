"""HOME-SERVICES-FINANCE: per-Job-Type monetization rule overrides.

A single vertical-level policy (migration 178) cannot express "Repair
charges 10 credits, Inspection Only charges 0" -- the Home Services Finance
workspace needs real per-Job-Type differentiation (exact Job Type via
Master Service + Job Type -> Job-Type Blueprint, never inferred from
service count). This table is a child of VerticalMonetizationPolicy: rules
are versioned together with their parent policy (a new policy version gets
its own fresh set of job-type rules, never mutates a prior version's rows).

Purely additive.

Revision ID: 180
Revises: 179
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "180"
down_revision = "179"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monetization_job_type_rules",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_charge_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        # booking_price_snapshot | approved_estimate | final_visit_fee
        sa.Column("customer_charge_basis", sa.String(30), nullable=False, server_default="booking_price_snapshot"),
        sa.Column("provider_charge_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("provider_charge_credit_units", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mjtr_policy", "monetization_job_type_rules", ["policy_id"])
    op.create_index("uq_mjtr_policy_job_type", "monetization_job_type_rules",
                    ["policy_id", "job_type_id"], unique=True)

    # Widen the policy status enum to the full lifecycle (was draft/
    # published/superseded only) -- additive, existing rows keep their
    # current string values (all still valid members of the new set).
    op.alter_column("vertical_monetization_policies", "status", type_=sa.String(30))


def downgrade() -> None:
    op.drop_index("uq_mjtr_policy_job_type", table_name="monetization_job_type_rules")
    op.drop_index("ix_mjtr_policy", table_name="monetization_job_type_rules")
    op.drop_table("monetization_job_type_rules")
    op.alter_column("vertical_monetization_policies", "status", type_=sa.String(20))
