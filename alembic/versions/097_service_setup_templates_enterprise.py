"""Service Setup Templates Enterprise — migration 097.

Creates 5 tables for the enterprise service setup templates system.

Revision ID: 097
Revises: 096
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import text

revision = "097"
down_revision = "096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_setup_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("code", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("vertical_key", sa.Text, nullable=True, server_default="universal"),
        sa.Column("template_type", sa.Text, nullable=True, server_default="starter_pack"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.Text, nullable=True, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "service_setup_template_modules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_key", sa.Text, nullable=False),
        sa.Column("module_name", sa.Text, nullable=True),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "service_setup_template_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_key", sa.Text, nullable=True),
        sa.Column("item_type", sa.Text, nullable=True),
        sa.Column("item_key", sa.Text, nullable=True),
        sa.Column("item_name", sa.Text, nullable=True),
        sa.Column("parent_item_key", sa.Text, nullable=True),
        sa.Column("payload_json", JSONB, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "service_setup_template_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("snapshot_json", JSONB, nullable=True),
        sa.Column("changed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("change_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "service_setup_template_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("service_setup_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("used_in", sa.Text, nullable=True),
        sa.Column("used_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bulk_run_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text, nullable=True, server_default="pending"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_index("ix_sst_code", "service_setup_templates", ["code"])
    op.create_index("ix_sst_status", "service_setup_templates", ["status"])
    op.create_index("ix_sst_vertical_key", "service_setup_templates", ["vertical_key"])
    op.create_index("ix_sstm_template_id", "service_setup_template_modules", ["template_id"])
    op.create_index("ix_ssti_template_id", "service_setup_template_items", ["template_id"])


def downgrade() -> None:
    op.drop_table("service_setup_template_usage")
    op.drop_table("service_setup_template_versions")
    op.drop_table("service_setup_template_items")
    op.drop_table("service_setup_template_modules")
    op.drop_table("service_setup_templates")
