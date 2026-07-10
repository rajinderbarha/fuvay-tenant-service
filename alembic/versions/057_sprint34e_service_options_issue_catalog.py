"""Sprint 34E — Service Options + Issue Catalog.

Adds service_option_groups, service_option_mappings, service_issue_mappings,
tenant_supported_service_options tables and enhances master_service_options /
master_issue_types with status + metadata columns.
Also adds issue_type_id + service_option_ids_json to home_service_booking_drafts.

Revision ID: 057
Revises: 056
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── service_option_groups ─────────────────────────────────────────────────
    op.create_table(
        "service_option_groups",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("code",          sa.String(80),  nullable=False),
        sa.Column("name",          sa.String(200), nullable=False),
        sa.Column("description",   sa.Text,        nullable=True),
        sa.Column("category_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vertical_type", sa.String(50),  nullable=True),
        sa.Column("status",        sa.String(30),  nullable=False, server_default="active"),
        sa.Column("display_order", sa.Integer,     nullable=False, server_default="0"),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",    sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_sog_code"),
    )
    op.create_index("ix_sog_category", "service_option_groups", ["category_id"])
    op.create_index("ix_sog_status",   "service_option_groups", ["status"])

    # ── enhance master_service_options ────────────────────────────────────────
    op.add_column("master_service_options",
        sa.Column("option_group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("master_service_options",
        sa.Column("vertical_type", sa.String(50), nullable=True))
    op.add_column("master_service_options",
        sa.Column("status", sa.String(30), nullable=False, server_default="active"))
    op.add_column("master_service_options",
        sa.Column("metadata_json", postgresql.JSONB, nullable=True))
    op.add_column("master_service_options",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("master_service_options",
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_mso_status",       "master_service_options", ["status"])
    op.create_index("ix_mso_option_group", "master_service_options", ["option_group_id"])

    # ── enhance master_issue_types ────────────────────────────────────────────
    op.add_column("master_issue_types",
        sa.Column("vertical_type", sa.String(50), nullable=True))
    op.add_column("master_issue_types",
        sa.Column("status", sa.String(30), nullable=False, server_default="active"))
    op.add_column("master_issue_types",
        sa.Column("metadata_json", postgresql.JSONB, nullable=True))
    op.add_column("master_issue_types",
        sa.Column("requires_photo", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("master_issue_types",
        sa.Column("requires_description", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("master_issue_types",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("master_issue_types",
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_mit_status", "master_issue_types", ["status"])

    # ── service_option_mappings ───────────────────────────────────────────────
    op.create_table(
        "service_option_mappings",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_option_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_group_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="active"),
        sa.Column("is_required",         sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("is_default",          sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("display_order",       sa.Integer,     nullable=False, server_default="0"),
        sa.Column("metadata_json",       postgresql.JSONB, nullable=True),
        sa.Column("created_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("master_service_id", "service_option_id",
                            name="uq_som_service_option"),
    )
    op.create_index("ix_som_service", "service_option_mappings", ["master_service_id"])
    op.create_index("ix_som_option",  "service_option_mappings", ["service_option_id"])
    op.create_index("ix_som_status",  "service_option_mappings", ["status"])

    # ── service_issue_mappings ────────────────────────────────────────────────
    op.create_table(
        "service_issue_mappings",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_type_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status",               sa.String(30),  nullable=False, server_default="active"),
        sa.Column("is_common",            sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("is_default",           sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("requires_photo",       sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("requires_description", sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("display_order",        sa.Integer,     nullable=False, server_default="0"),
        sa.Column("metadata_json",        postgresql.JSONB, nullable=True),
        sa.Column("created_by_user_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",           sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("master_service_id", "issue_type_id",
                            name="uq_sim_service_issue"),
    )
    op.create_index("ix_sim_service", "service_issue_mappings", ["master_service_id"])
    op.create_index("ix_sim_issue",   "service_issue_mappings", ["issue_type_id"])
    op.create_index("ix_sim_status",  "service_issue_mappings", ["status"])
    op.create_index("ix_sim_common",  "service_issue_mappings", ["is_common"])

    # ── tenant_supported_service_options ──────────────────────────────────────
    op.create_table(
        "tenant_supported_service_options",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",           postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_option_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="active"),
        sa.Column("notes",               sa.Text,        nullable=True),
        sa.Column("created_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "master_service_id", "service_option_id",
                            name="uq_tsso_tenant_service_option"),
    )
    op.create_index("ix_tsso_tenant",  "tenant_supported_service_options", ["tenant_id"])
    op.create_index("ix_tsso_service", "tenant_supported_service_options", ["master_service_id"])
    op.create_index("ix_tsso_option",  "tenant_supported_service_options", ["service_option_id"])
    op.create_index("ix_tsso_status",  "tenant_supported_service_options", ["status"])

    # ── home_service_booking_drafts: add structured issue + option columns ─────
    op.add_column("home_service_booking_drafts",
        sa.Column("issue_type_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("home_service_booking_drafts",
        sa.Column("service_option_ids_json", postgresql.JSONB, nullable=True))
    op.create_index("ix_hsbd_issue_type", "home_service_booking_drafts", ["issue_type_id"])


def downgrade() -> None:
    op.drop_index("ix_hsbd_issue_type", "home_service_booking_drafts")
    op.drop_column("home_service_booking_drafts", "service_option_ids_json")
    op.drop_column("home_service_booking_drafts", "issue_type_id")

    op.drop_table("tenant_supported_service_options")
    op.drop_table("service_issue_mappings")
    op.drop_table("service_option_mappings")

    op.drop_index("ix_mit_status", "master_issue_types")
    for col in ("updated_by_user_id", "created_by_user_id", "requires_description",
                "requires_photo", "metadata_json", "status", "vertical_type"):
        op.drop_column("master_issue_types", col)

    op.drop_index("ix_mso_option_group", "master_service_options")
    op.drop_index("ix_mso_status", "master_service_options")
    for col in ("updated_by_user_id", "created_by_user_id", "metadata_json",
                "status", "vertical_type", "option_group_id"):
        op.drop_column("master_service_options", col)

    op.drop_table("service_option_groups")
