"""Sprint 34C — Centralized Master Data Foundation

Revision: 055
Down revision: 054

Adds:
  - master_issue_types  (problem/fault types per service; admin-only write)
  - master_service_options  (add-ons/extras per service; admin-only write)
  - master_workflow_templates  (job workflow definitions; admin-only write)
  - master_data_audit_log  (append-only change trail for all master data entities)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. master_issue_types ─────────────────────────────────────────────────
    op.create_table(
        "master_issue_types",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id",      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id",postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code",             sa.String(80),  nullable=False),
        sa.Column("name",             sa.String(200), nullable=False),
        sa.Column("slug",             sa.String(200), nullable=False),
        sa.Column("description",      sa.Text,        nullable=True),
        sa.Column("severity",         sa.String(20),  nullable=False, server_default="medium"),
        sa.Column("is_active",        sa.Boolean,     nullable=False, server_default=sa.text("true")),
        sa.Column("display_order",    sa.Integer,     nullable=False, server_default="0"),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_mit_slug"),
    )
    op.create_index("ix_mit_category",        "master_issue_types", ["category_id"])
    op.create_index("ix_mit_master_service",  "master_issue_types", ["master_service_id"])
    op.create_index("ix_mit_active",          "master_issue_types", ["is_active"])

    # ── 2. master_service_options ─────────────────────────────────────────────
    op.create_table(
        "master_service_options",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id",           postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code",                  sa.String(80),  nullable=False),
        sa.Column("name",                  sa.String(200), nullable=False),
        sa.Column("slug",                  sa.String(200), nullable=False),
        sa.Column("description",           sa.Text,        nullable=True),
        sa.Column("option_type",           sa.String(30),  nullable=False, server_default="add_on"),
        sa.Column("unit",                  sa.String(30),  nullable=False, server_default="per_unit"),
        sa.Column("default_price",         sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("min_price",             sa.Numeric(12, 2), nullable=True),
        sa.Column("max_price",             sa.Numeric(12, 2), nullable=True),
        sa.Column("is_customer_selectable",sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active",             sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("display_order",         sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at",            sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",            sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_mso_slug"),
    )
    op.create_index("ix_mso_category",       "master_service_options", ["category_id"])
    op.create_index("ix_mso_master_service", "master_service_options", ["master_service_id"])
    op.create_index("ix_mso_active",         "master_service_options", ["is_active"])

    # ── 3. master_workflow_templates ──────────────────────────────────────────
    op.create_table(
        "master_workflow_templates",
        sa.Column("id",                          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id",                 postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id",           postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name",                        sa.String(200), nullable=False),
        sa.Column("slug",                        sa.String(200), nullable=False),
        sa.Column("description",                 sa.Text, nullable=True),
        sa.Column("workflow_type",               sa.String(30), nullable=False),
        sa.Column("steps",                       postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("estimated_duration_minutes",  sa.Integer, nullable=True),
        sa.Column("is_active",                   sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("display_order",               sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at",                  sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",                  sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_mwt_slug"),
    )
    op.create_index("ix_mwt_category",       "master_workflow_templates", ["category_id"])
    op.create_index("ix_mwt_master_service", "master_workflow_templates", ["master_service_id"])
    op.create_index("ix_mwt_workflow_type",  "master_workflow_templates", ["workflow_type"])
    op.create_index("ix_mwt_active",         "master_workflow_templates", ["is_active"])

    # ── 4. master_data_audit_log ──────────────────────────────────────────────
    op.create_table(
        "master_data_audit_log",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type",    sa.String(60),  nullable=False),
        sa.Column("entity_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action",         sa.String(30),  nullable=False),
        sa.Column("actor_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",     sa.String(30),  nullable=True),
        sa.Column("old_value",      postgresql.JSONB, nullable=True),
        sa.Column("new_value",      postgresql.JSONB, nullable=True),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("request_id",     sa.String(100), nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_mdal_entity",      "master_data_audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_mdal_actor",       "master_data_audit_log", ["actor_user_id"])
    op.create_index("ix_mdal_action",      "master_data_audit_log", ["action"])
    op.create_index("ix_mdal_created_at",  "master_data_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("master_data_audit_log")
    op.drop_table("master_workflow_templates")
    op.drop_table("master_service_options")
    op.drop_table("master_issue_types")
