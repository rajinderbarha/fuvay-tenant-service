"""Sprint 34F — Service Setup Templates.

Creates service_setup_templates, service_setup_template_items,
service_setup_template_relationships, service_setup_template_runs,
and service_setup_template_run_items tables.

Revision ID: 058
Revises: 057
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── service_setup_templates ───────────────────────────────────────────────
    op.create_table(
        "service_setup_templates",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("code",                sa.String(80),  nullable=False),
        sa.Column("name",                sa.String(200), nullable=False),
        sa.Column("slug",                sa.String(200), nullable=False),
        sa.Column("description",         sa.Text,        nullable=True),
        sa.Column("vertical_type",       sa.String(50),  nullable=True),
        sa.Column("category_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_type",       sa.String(50),  nullable=False, server_default="starter_pack"),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="draft"),
        sa.Column("version",             sa.Integer,     nullable=False, server_default="1"),
        sa.Column("is_system_template",  sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("created_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json",       postgresql.JSONB, nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code",      name="uq_sst_code"),
        sa.UniqueConstraint("slug",      name="uq_sst_slug"),
    )
    op.create_index("ix_sst_status",   "service_setup_templates", ["status"])
    op.create_index("ix_sst_vertical", "service_setup_templates", ["vertical_type"])
    op.create_index("ix_sst_type",     "service_setup_templates", ["template_type"])
    op.create_index("ix_sst_system",   "service_setup_templates", ["is_system_template"])

    # ── service_setup_template_items ──────────────────────────────────────────
    op.create_table(
        "service_setup_template_items",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id",     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type",       sa.String(50),  nullable=False),
        sa.Column("reference_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_code",  sa.String(80),  nullable=True),
        sa.Column("payload_json",    postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("apply_mode",      sa.String(30),  nullable=False, server_default="create_if_missing"),
        sa.Column("is_required",     sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("display_order",   sa.Integer,     nullable=False, server_default="0"),
        sa.Column("status",          sa.String(30),  nullable=False, server_default="active"),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",      sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ssti_template",   "service_setup_template_items", ["template_id"])
    op.create_index("ix_ssti_item_type",  "service_setup_template_items", ["item_type"])
    op.create_index("ix_ssti_ref_id",     "service_setup_template_items", ["reference_id"])
    op.create_index("ix_ssti_ref_code",   "service_setup_template_items", ["reference_code"])
    op.create_index("ix_ssti_status",     "service_setup_template_items", ["status"])

    # ── service_setup_template_relationships ──────────────────────────────────
    op.create_table(
        "service_setup_template_relationships",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_item_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_item_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type",   sa.String(50),  nullable=False),
        sa.Column("payload_json",        postgresql.JSONB, nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="active"),
        sa.Column("display_order",       sa.Integer,     nullable=False, server_default="0"),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sstr_template",   "service_setup_template_relationships", ["template_id"])
    op.create_index("ix_sstr_source",     "service_setup_template_relationships", ["source_item_id"])
    op.create_index("ix_sstr_target",     "service_setup_template_relationships", ["target_item_id"])
    op.create_index("ix_sstr_rel_type",   "service_setup_template_relationships", ["relationship_type"])

    # ── service_setup_template_runs ───────────────────────────────────────────
    op.create_table(
        "service_setup_template_runs",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version",             sa.Integer,     nullable=False, server_default="1"),
        sa.Column("applied_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_scope",        sa.String(30),  nullable=False, server_default="platform"),
        sa.Column("target_category_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_service_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_tenant_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="running"),
        sa.Column("summary_json",        postgresql.JSONB, nullable=True),
        sa.Column("error_json",          postgresql.JSONB, nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at",        sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sst_run_template", "service_setup_template_runs", ["template_id"])
    op.create_index("ix_sst_run_status",   "service_setup_template_runs", ["status"])
    op.create_index("ix_sst_run_actor",    "service_setup_template_runs", ["applied_by_user_id"])

    # ── service_setup_template_run_items ──────────────────────────────────────
    op.create_table(
        "service_setup_template_run_items",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id",              postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_item_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action",              sa.String(30),  nullable=False),
        sa.Column("target_record_type",  sa.String(50),  nullable=True),
        sa.Column("target_record_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message",             sa.Text,        nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sst_run_item_run",    "service_setup_template_run_items", ["run_id"])
    op.create_index("ix_sst_run_item_action", "service_setup_template_run_items", ["action"])


def downgrade() -> None:
    op.drop_table("service_setup_template_run_items")
    op.drop_table("service_setup_template_runs")
    op.drop_table("service_setup_template_relationships")
    op.drop_table("service_setup_template_items")
    op.drop_table("service_setup_templates")
