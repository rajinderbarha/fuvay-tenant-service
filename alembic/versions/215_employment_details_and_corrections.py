"""Phase S -- Employment Details: add reports_to columns to provider_team_members,
a real per-skill verification table (skills was a raw JSONB blob with no
verification metadata -- confirmed by audit), and a generic staff employment
correction-request workflow (confirmed no such system existed anywhere).

Revision ID: 215
Revises: 214
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "215"
down_revision = "214"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("provider_team_members", sa.Column("reports_to_display_name", sa.String(200), nullable=True))
    op.add_column("provider_team_members", sa.Column("reports_to_designation", sa.String(100), nullable=True))

    op.create_table(
        "staff_skill_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(150), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ssr_tenant_staff", "staff_skill_records", ["tenant_id", "staff_member_id"])

    op.create_table(
        "staff_correction_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_key", sa.String(40), nullable=False),
        sa.Column("current_value", sa.Text(), nullable=True),
        sa.Column("requested_value", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_scr_tenant_staff", "staff_correction_requests", ["tenant_id", "staff_member_id"])
    op.create_index("ix_scr_status", "staff_correction_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_scr_status", table_name="staff_correction_requests")
    op.drop_index("ix_scr_tenant_staff", table_name="staff_correction_requests")
    op.drop_table("staff_correction_requests")
    op.drop_index("ix_ssr_tenant_staff", table_name="staff_skill_records")
    op.drop_table("staff_skill_records")
    op.drop_column("provider_team_members", "reports_to_designation")
    op.drop_column("provider_team_members", "reports_to_display_name")
