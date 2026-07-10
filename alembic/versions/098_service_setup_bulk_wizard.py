"""Service Setup Bulk Wizard — migration 098.

Creates 5 tables for the enterprise bulk setup wizard system.

Revision ID: 098
Revises: 097
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import text

revision = "098"
down_revision = "097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_setup_bulk_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("draft_code", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("vertical_key", sa.Text, nullable=False),
        sa.Column("setup_mode", sa.Text, nullable=True, server_default="manual"),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Text, nullable=True, server_default="draft"),
        sa.Column("current_step", sa.Integer, nullable=True, server_default="1"),
        sa.Column("config_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=text("now()")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "service_setup_bulk_preview_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_bulk_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_key", sa.Text, nullable=True),
        sa.Column("record_type", sa.Text, nullable=True),
        sa.Column("record_name", sa.Text, nullable=True),
        sa.Column("record_code", sa.Text, nullable=True),
        sa.Column("action", sa.Text, nullable=True, server_default="create"),
        sa.Column("payload_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=text("now()")),
    )

    op.create_table(
        "service_setup_bulk_validation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_bulk_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.Text, nullable=True, server_default="info"),
        sa.Column("module_key", sa.Text, nullable=True),
        sa.Column("record_type", sa.Text, nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("blocking", sa.Boolean, nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=text("now()")),
    )

    op.create_table(
        "service_setup_bulk_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("run_code", sa.Text, unique=True, nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_bulk_drafts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vertical_key", sa.Text, nullable=True),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Text, nullable=True, server_default="queued"),
        sa.Column("is_dry_run", sa.Boolean, nullable=True, server_default="false"),
        sa.Column("total_items", sa.Integer, nullable=True, server_default="0"),
        sa.Column("created_count", sa.Integer, nullable=True, server_default="0"),
        sa.Column("updated_count", sa.Integer, nullable=True, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=True, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=True, server_default="0"),
        sa.Column("rollback_available", sa.Boolean, nullable=True, server_default="false"),
        sa.Column("execution_reason", sa.Text, nullable=True),
        sa.Column("started_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=text("now()")),
    )

    op.create_table(
        "service_setup_bulk_run_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_bulk_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_key", sa.Text, nullable=True),
        sa.Column("record_type", sa.Text, nullable=True),
        sa.Column("record_name", sa.Text, nullable=True),
        sa.Column("record_code", sa.Text, nullable=True),
        sa.Column("action", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=True, server_default="pending"),
        sa.Column("target_record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=text("now()")),
    )

    op.create_index("ix_bulk_drafts_status", "service_setup_bulk_drafts", ["status"])
    op.create_index("ix_bulk_drafts_vertical", "service_setup_bulk_drafts", ["vertical_key"])
    op.create_index("ix_bulk_preview_items_draft", "service_setup_bulk_preview_items", ["draft_id"])
    op.create_index("ix_bulk_validation_draft", "service_setup_bulk_validation_results", ["draft_id"])
    op.create_index("ix_bulk_runs_draft", "service_setup_bulk_runs", ["draft_id"])
    op.create_index("ix_bulk_run_items_run", "service_setup_bulk_run_items", ["run_id"])


def downgrade() -> None:
    op.drop_table("service_setup_bulk_run_items")
    op.drop_table("service_setup_bulk_runs")
    op.drop_table("service_setup_bulk_validation_results")
    op.drop_table("service_setup_bulk_preview_items")
    op.drop_table("service_setup_bulk_drafts")
