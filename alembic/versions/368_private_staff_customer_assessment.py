"""Private post-job staff customer behavior assessments.

Revision ID: 368
Revises: 367
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "368"
down_revision = "367"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_behavior_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("behavior_code", sa.String(length=30), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("behavior_code IN ('respectful','neutral','difficult','unsafe')", name="ck_customer_behavior_code"),
        sa.UniqueConstraint("job_id", name="uq_customer_behavior_job"),
    )
    op.create_index("ix_customer_behavior_tenant_customer", "customer_behavior_assessments", ["tenant_id", "customer_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_behavior_tenant_customer", table_name="customer_behavior_assessments")
    op.drop_table("customer_behavior_assessments")
