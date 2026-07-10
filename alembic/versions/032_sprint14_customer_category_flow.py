"""Sprint 14 — Customer Category Flow Routing.

Adds customer-facing fields to service_categories and master_offerings,
and creates the customer_flow_configs table.

Revision ID: 024
Revises: 023
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i"
    ), {"i": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()
    # ── service_categories: add customer-visibility / routing fields ──
    if not _col_exists(conn, "service_categories", "is_customer_visible"):
        op.add_column("service_categories",
            sa.Column("is_customer_visible", sa.Boolean(), nullable=False,
                      server_default=sa.text("true")))
    if not _col_exists(conn, "service_categories", "primary_engine_key"):
        op.add_column("service_categories",
            sa.Column("primary_engine_key", sa.String(100), nullable=True))
    if not _col_exists(conn, "service_categories", "frontend_component_key"):
        op.add_column("service_categories",
            sa.Column("frontend_component_key", sa.String(100), nullable=True))
    if not _col_exists(conn, "service_categories", "banner_url"):
        op.add_column("service_categories",
            sa.Column("banner_url", sa.String(500), nullable=True))

    if not _index_exists(conn, "ix_sc_customer_visible"):
        op.create_index("ix_sc_customer_visible", "service_categories", ["is_customer_visible"])

    # ── master_offerings: add customer-flow / requirement fields ──────
    if not _col_exists(conn, "master_offerings", "customer_flow_type"):
        op.add_column("master_offerings",
            sa.Column("customer_flow_type", sa.String(50), nullable=True))
    if not _col_exists(conn, "master_offerings", "primary_engine_key"):
        op.add_column("master_offerings",
            sa.Column("primary_engine_key", sa.String(100), nullable=True))
    if not _col_exists(conn, "master_offerings", "requires_address"):
        op.add_column("master_offerings",
            sa.Column("requires_address", sa.Boolean(), nullable=False,
                      server_default=sa.text("false")))
    if not _col_exists(conn, "master_offerings", "requires_slot"):
        op.add_column("master_offerings",
            sa.Column("requires_slot", sa.Boolean(), nullable=False,
                      server_default=sa.text("false")))
    if not _col_exists(conn, "master_offerings", "requires_photo_upload"):
        op.add_column("master_offerings",
            sa.Column("requires_photo_upload", sa.Boolean(), nullable=False,
                      server_default=sa.text("false")))
    if not _col_exists(conn, "master_offerings", "requires_customer_notes"):
        op.add_column("master_offerings",
            sa.Column("requires_customer_notes", sa.Boolean(), nullable=False,
                      server_default=sa.text("false")))

    if not _index_exists(conn, "ix_mo_customer_flow_type"):
        op.create_index("ix_mo_customer_flow_type", "master_offerings", ["customer_flow_type"])

    # ── customer_flow_configs: per-category customer UX config ────────
    op.create_table(
        "customer_flow_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_flow_type", sa.String(50), nullable=False),
        sa.Column("frontend_component_key", sa.String(100), nullable=False),
        sa.Column("primary_engine_key", sa.String(100), nullable=False),
        sa.Column("required_steps", JSONB, nullable=True),
        sa.Column("optional_steps", JSONB, nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False,
                  onupdate=sa.text("now()")),
        sa.UniqueConstraint("category_id", name="uq_cfc_category"),
    )
    op.create_index("ix_cfc_category", "customer_flow_configs", ["category_id"])
    op.create_index("ix_cfc_flow_type", "customer_flow_configs", ["customer_flow_type"])
    op.create_index("ix_cfc_active", "customer_flow_configs", ["is_active"])


def downgrade() -> None:
    op.drop_table("customer_flow_configs")
    op.drop_index("ix_mo_customer_flow_type", table_name="master_offerings")
    op.drop_column("master_offerings", "requires_customer_notes")
    op.drop_column("master_offerings", "requires_photo_upload")
    op.drop_column("master_offerings", "requires_slot")
    op.drop_column("master_offerings", "requires_address")
    op.drop_column("master_offerings", "primary_engine_key")
    op.drop_column("master_offerings", "customer_flow_type")
    op.drop_index("ix_sc_customer_visible", table_name="service_categories")
    op.drop_column("service_categories", "banner_url")
    op.drop_column("service_categories", "frontend_component_key")
    op.drop_column("service_categories", "primary_engine_key")
    op.drop_column("service_categories", "is_customer_visible")
