"""Pricing Enterprise Upgrade
- Extend service_pricing_rules with rule_name, rule_code, bargain_floor, source,
  district, state, zone
- Add composite index on tier_locations(zipcode, is_active) for conflict detection
- Create location_import_batches (CSV import wizard: preview -> confirm -> report)

Revision ID: 077
Revises: 076
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    def _table_exists(t: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {"t": t})
        return bool(r.fetchone())

    def _index_exists(name: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname=:n"), {"n": name})
        return bool(r.fetchone())

    # ── Extend service_pricing_rules ────────────────────────────────────────────
    if not _col_exists("service_pricing_rules", "rule_name"):
        op.add_column("service_pricing_rules", sa.Column("rule_name", sa.String(200), nullable=True))
    if not _col_exists("service_pricing_rules", "rule_code"):
        op.add_column("service_pricing_rules", sa.Column("rule_code", sa.String(80), nullable=True))
    if not _col_exists("service_pricing_rules", "bargain_floor"):
        op.add_column("service_pricing_rules", sa.Column("bargain_floor", sa.Numeric(12, 2), nullable=True))
    if not _col_exists("service_pricing_rules", "source"):
        op.add_column("service_pricing_rules", sa.Column("source", sa.String(30),
                                                           server_default="'admin'", nullable=False))
    if not _col_exists("service_pricing_rules", "district"):
        op.add_column("service_pricing_rules", sa.Column("district", sa.String(100), nullable=True))
    if not _col_exists("service_pricing_rules", "state"):
        op.add_column("service_pricing_rules", sa.Column("state", sa.String(100), nullable=True))
    if not _col_exists("service_pricing_rules", "zone"):
        op.add_column("service_pricing_rules", sa.Column("zone", sa.String(100), nullable=True))

    # ── tier_locations: conflict-detection index ────────────────────────────────
    if not _index_exists("ix_tl_zipcode_active"):
        op.create_index("ix_tl_zipcode_active", "tier_locations", ["zipcode", "is_active"])

    # ── location_import_batches ──────────────────────────────────────────────────
    if not _table_exists("location_import_batches"):
        op.create_table(
            "location_import_batches",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("status", sa.String(20), server_default="'preview'", nullable=False),
            sa.Column("file_name", sa.String(255), nullable=True),
            sa.Column("uploaded_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("total_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("valid_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("invalid_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("conflict_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("created_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("updated_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("skipped_rows", sa.Integer, server_default="0", nullable=False),
            sa.Column("preview_payload", JSONB, nullable=True),
            sa.Column("report_payload", JSONB, nullable=True),
            sa.Column("conflict_resolution", sa.String(20), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
        )
        op.create_index("ix_lib_status", "location_import_batches", ["status"])
        op.create_index("ix_lib_uploaded_by", "location_import_batches", ["uploaded_by_user_id"])


def downgrade() -> None:
    op.drop_table("location_import_batches")
    op.drop_index("ix_tl_zipcode_active", table_name="tier_locations")
    for col in ("zone", "state", "district", "source", "bargain_floor", "rule_code", "rule_name"):
        op.drop_column("service_pricing_rules", col)
