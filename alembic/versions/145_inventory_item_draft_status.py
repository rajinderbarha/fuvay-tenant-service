"""Inventory Document Extraction Engine — draft/publish state for InventoryItem.

USER REQ: providers can upload a PDF (price list / stock sheet); the new
inventory_document_extraction plugin engine extracts line items via the
platform's DeepSeek LLM client and creates InventoryItem rows the provider
must review/edit before publishing. This adds the status column (checked —
no pre-existing status-like field on inventory_items) plus two nullable
columns to trace which upload/extraction produced a draft row.

Revision ID: 145
Revises: 144
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "145"
down_revision = "144"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("status", sa.String(20), server_default="published", nullable=False),
    )
    op.add_column(
        "inventory_items",
        sa.Column("source_upload_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ii_status", "inventory_items", ["tenant_id", "status"])

    op.create_table(
        "inventory_extraction_uploads",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("extracted_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_llm_response", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "content_hash", name="uq_ieu_tenant_hash"),
    )
    op.create_index("ix_ieu_tenant", "inventory_extraction_uploads", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_ieu_tenant", table_name="inventory_extraction_uploads")
    op.drop_table("inventory_extraction_uploads")
    op.drop_index("ix_ii_status", table_name="inventory_items")
    op.drop_column("inventory_items", "source_upload_id")
    op.drop_column("inventory_items", "status")
