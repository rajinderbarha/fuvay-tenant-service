"""TENANT-DOCUMENTS: verification document manifest, versioning, review.

`tenant_documents` was declared in tenant_engine/models.py and already read
by home_services_setup_service.get_setup_overview() (wrapped in a
try/except since the table was never actually migrated) but never created
or written to anywhere -- this migration provisions the real table with the
full versioning/review shape the Verification Documents onboarding step and
setup-overview completion check both need.

One row per UPLOAD (not per requirement): replacing a document inserts a
new current row and flips the prior row to `is_current=False` /
`status=superseded` rather than mutating it, so review history is never
destroyed and a stale review action can never approve a superseded version.

Revision ID: 189
Revises: 188
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "189"
down_revision = "188"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("media_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tenant_docs_tenant_id", "tenant_documents", ["tenant_id"])
    op.create_index("ix_tenant_docs_tenant_doctype", "tenant_documents", ["tenant_id", "doc_type"])
    op.create_index("ix_tenant_docs_current", "tenant_documents", ["tenant_id", "doc_type", "is_current"])


def downgrade() -> None:
    op.drop_index("ix_tenant_docs_current", table_name="tenant_documents")
    op.drop_index("ix_tenant_docs_tenant_doctype", table_name="tenant_documents")
    op.drop_index("ix_tenant_docs_tenant_id", table_name="tenant_documents")
    op.drop_table("tenant_documents")
