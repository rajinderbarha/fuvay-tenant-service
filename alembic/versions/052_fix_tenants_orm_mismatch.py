"""Fix tenants table: add columns that the ORM model expects but the DB lacks.

The Tenant ORM model was updated in Sprints 4–5 to include email, phone,
business_type, city_tier, zone_id, rating_average, and archived_at columns,
but no migration was ever written to add them to the database. The DB has
business_email/business_phone (from the provider-registration migration) while
the ORM maps to simpler email/phone column names.

Revision ID: 052
Revises: 051
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "052"
down_revision = "051"
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

    # ── Add ALL tenant columns from sprints 4/5 that may be missing ──────────
    nullable_str_cols = [
        ("slug",                 sa.String(120)),
        ("tenant_code",          sa.String(30)),
        ("business_name",        sa.String(255)),
        ("legal_name",           sa.String(255)),
        ("email",                sa.String(255)),
        ("phone",                sa.String(20)),
        ("gst_number",           sa.String(20)),
        ("business_type",        sa.String(50)),
        ("address_line1",        sa.String(255)),
        ("address_line2",        sa.String(255)),
        ("district",             sa.String(100)),
        ("zipcode",              sa.String(20)),
        ("logo_url",             sa.String(500)),
        ("city_tier",            sa.String(20)),
        ("health_band",          sa.String(20)),
    ]
    for col_name, col_type in nullable_str_cols:
        if not _col_exists(conn, "tenants", col_name):
            op.add_column("tenants", sa.Column(col_name, col_type, nullable=True))

    if not _col_exists(conn, "tenants", "category_id"):
        op.add_column("tenants", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _col_exists(conn, "tenants", "business_logo_media_id"):
        op.add_column("tenants", sa.Column("business_logo_media_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _col_exists(conn, "tenants", "shop_photo_media_id"):
        op.add_column("tenants", sa.Column("shop_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _col_exists(conn, "tenants", "zone_id"):
        op.add_column("tenants", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _col_exists(conn, "tenants", "verification_status"):
        op.add_column("tenants", sa.Column("verification_status", sa.String(30),
                                           nullable=False, server_default="not_started"))
    if not _col_exists(conn, "tenants", "rating_average"):
        op.add_column("tenants", sa.Column("rating_average", sa.Numeric(3, 2),
                                           nullable=False, server_default="0.00"))
    if not _col_exists(conn, "tenants", "archived_at"):
        op.add_column("tenants", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))

    # Copy existing business_email / business_phone into the new columns if they exist.
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='tenants' AND column_name='business_email'"
    ))
    if result.fetchone():
        op.execute("""
            UPDATE tenants
            SET email = business_email,
                phone = business_phone
            WHERE email IS NULL
        """)

    # ── Create indexes conditionally ─────────────────────────────────────────
    index_map = {
        "ix_tenants_city_tier":            ["city_tier"],
        "ix_tenants_district":             ["district"],
        "ix_tenants_created_at":           ["created_at"],
        "ix_tenants_state":                ["state"],
        "ix_tenants_city":                 ["city"],
        "ix_tenants_category_id":          ["category_id"],
        "ix_tenants_verification_status":  ["verification_status"],
        "ix_tenants_state_district":       ["state", "district"],
        "ix_tenants_state_district_city":  ["state", "district", "city"],
        "ix_tenants_verification_created": ["verification_status", "created_at"],
        "ix_tenants_status_created":       ["status", "created_at"],
    }
    for idx_name, cols in index_map.items():
        if not _index_exists(conn, idx_name):
            op.create_index(idx_name, "tenants", cols)


def downgrade() -> None:
    op.drop_index("ix_tenants_status_created", table_name="tenants")
    op.drop_index("ix_tenants_verification_created", table_name="tenants")
    op.drop_index("ix_tenants_verification_status", table_name="tenants")
    op.drop_index("ix_tenants_state_district_city", table_name="tenants")
    op.drop_index("ix_tenants_state_district", table_name="tenants")
    op.drop_index("ix_tenants_city", table_name="tenants")
    op.drop_index("ix_tenants_state", table_name="tenants")
    op.drop_index("ix_tenants_created_at", table_name="tenants")
    op.drop_index("ix_tenants_district", table_name="tenants")
    op.drop_index("ix_tenants_city_tier", table_name="tenants")
    op.drop_column("tenants", "archived_at")
    op.drop_column("tenants", "rating_average")
    op.drop_column("tenants", "zone_id")
    op.drop_column("tenants", "city_tier")
    op.drop_column("tenants", "business_type")
    op.drop_column("tenants", "phone")
    op.drop_column("tenants", "email")
