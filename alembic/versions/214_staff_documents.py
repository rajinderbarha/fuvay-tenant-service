"""Phase R -- add staff_documents for per-technician document lifecycle.
Confirmed genuinely missing: no document row anywhere references
ProviderTeamMember; TenantDocument is tenant-level compliance only.

Revision ID: 214
Revises: 213
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "214"
down_revision = "213"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sdoc_tenant_staff", "staff_documents", ["tenant_id", "staff_member_id"])
    op.create_index("ix_sdoc_status", "staff_documents", ["status"])


def downgrade() -> None:
    op.drop_index("ix_sdoc_status", table_name="staff_documents")
    op.drop_index("ix_sdoc_tenant_staff", table_name="staff_documents")
    op.drop_table("staff_documents")
