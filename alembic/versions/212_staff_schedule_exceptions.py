"""Phase P -- add staff_blocked_times + staff_time_off_requests. Confirmed
genuinely missing: availability_resolver.py's own docstring documents these
exact gaps (no staff_time_off table, no per-staff date-override table) and
reserves reason codes/capability flags for them.

Revision ID: 212
Revises: 211
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "212"
down_revision = "211"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_blocked_times",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="staff"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sbt_tenant_staff", "staff_blocked_times", ["tenant_id", "staff_member_id"])
    op.create_index("ix_sbt_date", "staff_blocked_times", ["block_date"])

    op.create_table(
        "staff_time_off_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_full_day", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("reason_category", sa.String(40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_stor_tenant_staff", "staff_time_off_requests", ["tenant_id", "staff_member_id"])
    op.create_index("ix_stor_status", "staff_time_off_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_stor_status", table_name="staff_time_off_requests")
    op.drop_index("ix_stor_tenant_staff", table_name="staff_time_off_requests")
    op.drop_table("staff_time_off_requests")
    op.drop_index("ix_sbt_date", table_name="staff_blocked_times")
    op.drop_index("ix_sbt_tenant_staff", table_name="staff_blocked_times")
    op.drop_table("staff_blocked_times")
