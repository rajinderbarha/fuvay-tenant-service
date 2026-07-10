"""Tenant Home Services Service Setup Wizard — per-type/brand price range + publish state.

Adds tenant_min_price/tenant_max_price to tenant_service_types and
tenant_service_brands (previously only a single tenant_price_adjustment
existed — not a range, and never validated against admin floor/ceiling in
a dedicated setup flow). Adds setup_status (draft|published) and
published_at to tenant_services so the wizard can save a draft before
going live, distinct from is_enabled which already existed for a
different purpose (soft on/off toggle).

Revision ID: 119
Revises: 118
"""
from alembic import op
import sqlalchemy as sa

revision = "119"
down_revision = "118"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tst_columns = {c["name"] for c in inspector.get_columns("tenant_service_types")}
    if "tenant_min_price" not in tst_columns:
        op.add_column("tenant_service_types", sa.Column("tenant_min_price", sa.Numeric(12, 2), nullable=True))
    if "tenant_max_price" not in tst_columns:
        op.add_column("tenant_service_types", sa.Column("tenant_max_price", sa.Numeric(12, 2), nullable=True))

    tsb_columns = {c["name"] for c in inspector.get_columns("tenant_service_brands")}
    if "tenant_min_price" not in tsb_columns:
        op.add_column("tenant_service_brands", sa.Column("tenant_min_price", sa.Numeric(12, 2), nullable=True))
    if "tenant_max_price" not in tsb_columns:
        op.add_column("tenant_service_brands", sa.Column("tenant_max_price", sa.Numeric(12, 2), nullable=True))

    ts_columns = {c["name"] for c in inspector.get_columns("tenant_services")}
    if "setup_status" not in ts_columns:
        op.add_column("tenant_services", sa.Column("setup_status", sa.String(20), nullable=False, server_default="draft"))
    if "published_at" not in ts_columns:
        op.add_column("tenant_services", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_services", "published_at")
    op.drop_column("tenant_services", "setup_status")
    op.drop_column("tenant_service_brands", "tenant_max_price")
    op.drop_column("tenant_service_brands", "tenant_min_price")
    op.drop_column("tenant_service_types", "tenant_max_price")
    op.drop_column("tenant_service_types", "tenant_min_price")
