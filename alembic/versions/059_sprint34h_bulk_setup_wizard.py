"""Sprint 34H — Admin Bulk Setup Wizard.

Creates admin_bulk_setup_drafts, admin_bulk_setup_runs,
and admin_bulk_setup_run_items tables.

Revision ID: 059
Revises: 058
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── admin_bulk_setup_drafts ───────────────────────────────────────────────
    op.create_table(
        "admin_bulk_setup_drafts",
        sa.Column("id",                         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_by_user_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",                     sa.String(30),  nullable=False, server_default="draft"),
        sa.Column("current_step",               sa.Integer,     nullable=False, server_default="1"),
        sa.Column("target_vertical_type",       sa.String(50),  nullable=True),
        sa.Column("target_category_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_category_payload_json", postgresql.JSONB, nullable=True),
        sa.Column("selected_service_ids_json",  postgresql.JSONB, nullable=True),
        sa.Column("new_services_payload_json",  postgresql.JSONB, nullable=True),
        sa.Column("selected_template_ids_json", postgresql.JSONB, nullable=True),
        sa.Column("bulk_setup_payload_json",    postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("preview_summary_json",       postgresql.JSONB, nullable=True),
        sa.Column("blocking_items_json",        postgresql.JSONB, nullable=True),
        sa.Column("last_previewed_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at",                 sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",                 sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",                 sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",                 sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_abs_draft_creator",  "admin_bulk_setup_drafts", ["created_by_user_id"])
    op.create_index("ix_abs_draft_status",   "admin_bulk_setup_drafts", ["status"])
    op.create_index("ix_abs_draft_vertical", "admin_bulk_setup_drafts", ["target_vertical_type"])
    op.create_index("ix_abs_draft_category", "admin_bulk_setup_drafts", ["target_category_id"])

    # ── admin_bulk_setup_runs ─────────────────────────────────────────────────
    op.create_table(
        "admin_bulk_setup_runs",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("draft_id",              postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applied_by_user_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",                sa.String(30),  nullable=False, server_default="running"),
        sa.Column("target_vertical_type",  sa.String(50),  nullable=True),
        sa.Column("target_category_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary_json",          postgresql.JSONB, nullable=True),
        sa.Column("error_json",            postgresql.JSONB, nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_abs_run_draft",   "admin_bulk_setup_runs", ["draft_id"])
    op.create_index("ix_abs_run_status",  "admin_bulk_setup_runs", ["status"])
    op.create_index("ix_abs_run_actor",   "admin_bulk_setup_runs", ["applied_by_user_id"])

    # ── admin_bulk_setup_run_items ────────────────────────────────────────────
    op.create_table(
        "admin_bulk_setup_run_items",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type",  sa.String(50),  nullable=False),
        sa.Column("entity_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_code",  sa.String(80),  nullable=True),
        sa.Column("action",       sa.String(20),  nullable=False),
        sa.Column("message",      sa.Text,        nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_abs_run_item_run",    "admin_bulk_setup_run_items", ["run_id"])
    op.create_index("ix_abs_run_item_type",   "admin_bulk_setup_run_items", ["entity_type"])
    op.create_index("ix_abs_run_item_action", "admin_bulk_setup_run_items", ["action"])


def downgrade() -> None:
    op.drop_table("admin_bulk_setup_run_items")
    op.drop_table("admin_bulk_setup_runs")
    op.drop_table("admin_bulk_setup_drafts")
