"""Types & Brands Enterprise Upgrade
- Extend service_types with code, type_family, customer_visible, status, display_order
- Create service_type_mappings (type → category/group/service)
- Create brand_mappings       (brand → category/group/service)

Revision ID: 076
Revises: 075
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Extend service_types ───────────────────────────────────────────────────
    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    if not _col_exists("service_types", "code"):
        op.add_column("service_types", sa.Column("code", sa.String(100), nullable=True))
    if not _col_exists("service_types", "type_family"):
        op.add_column("service_types", sa.Column("type_family", sa.String(50), nullable=True))
    if not _col_exists("service_types", "customer_visible"):
        op.add_column("service_types", sa.Column("customer_visible", sa.Boolean,
                                                  server_default="true", nullable=False))
    if not _col_exists("service_types", "status"):
        op.add_column("service_types", sa.Column("status", sa.String(20),
                                                  server_default="'active'", nullable=False))
    if not _col_exists("service_types", "display_order"):
        op.add_column("service_types", sa.Column("display_order", sa.Integer,
                                                  server_default="0", nullable=False))

    # ── service_type_mappings ─────────────────────────────────────────────────
    def _table_exists(t: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {"t": t})
        return bool(r.fetchone())

    if not _table_exists("service_type_mappings"):
        op.create_table(
            "service_type_mappings",
            sa.Column("id",               UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("type_id",          UUID(as_uuid=True), sa.ForeignKey("service_types.id"),
                      nullable=False),
            sa.Column("category_id",      UUID(as_uuid=True), nullable=True),
            sa.Column("service_group_id", UUID(as_uuid=True), nullable=True),
            sa.Column("service_id",       UUID(as_uuid=True), nullable=True),
            sa.Column("customer_visible", sa.Boolean, server_default="true",  nullable=False),
            sa.Column("provider_visible", sa.Boolean, server_default="true",  nullable=False),
            sa.Column("status",           sa.String(20), server_default="'active'", nullable=False),
            sa.Column("display_order",    sa.Integer,  server_default="0",    nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
            sa.UniqueConstraint("type_id", "category_id", "service_group_id", "service_id",
                                name="uq_stm_type_cat_grp_svc"),
        )
        op.create_index("ix_stm_type_id",     "service_type_mappings", ["type_id"])
        op.create_index("ix_stm_category_id", "service_type_mappings", ["category_id"])
        op.create_index("ix_stm_service_id",  "service_type_mappings", ["service_id"])

    # ── brand_mappings ────────────────────────────────────────────────────────
    if not _table_exists("brand_mappings"):
        op.create_table(
            "brand_mappings",
            sa.Column("id",               UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("brand_id",         UUID(as_uuid=True), sa.ForeignKey("brands.id"),
                      nullable=False),
            sa.Column("category_id",      UUID(as_uuid=True), nullable=True),
            sa.Column("service_group_id", UUID(as_uuid=True), nullable=True),
            sa.Column("service_id",       UUID(as_uuid=True), nullable=True),
            sa.Column("customer_visible", sa.Boolean, server_default="true",  nullable=False),
            sa.Column("provider_visible", sa.Boolean, server_default="true",  nullable=False),
            sa.Column("status",           sa.String(20), server_default="'active'", nullable=False),
            sa.Column("display_order",    sa.Integer,  server_default="0",    nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
            sa.UniqueConstraint("brand_id", "category_id", "service_group_id", "service_id",
                                name="uq_bm_brand_cat_grp_svc"),
        )
        op.create_index("ix_bm_brand_id",    "brand_mappings", ["brand_id"])
        op.create_index("ix_bm_category_id", "brand_mappings", ["category_id"])
        op.create_index("ix_bm_service_id",  "brand_mappings", ["service_id"])


def downgrade() -> None:
    op.drop_table("brand_mappings")
    op.drop_table("service_type_mappings")
    for col in ("display_order", "status", "customer_visible", "type_family", "code"):
        op.drop_column("service_types", col)
