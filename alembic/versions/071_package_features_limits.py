"""071 — package_features + package_limits tables; extended service_packages fields.

Adds:
  - package_features  table (feature list per package)
  - package_limits    table (usage limits per package)
  - service_packages: short_description, badge_label, cta_label,
                      terms_summary, terms_content_json, trial_days,
                      is_featured, is_recommended, bonus_credits,
                      lead_credits, setup_fee_amount, renewal_price_amount,
                      refund_policy, metadata_json, rich_description_json,
                      rich_description_html
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": col},
    )
    return r.fetchone() is not None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"
        ),
        {"t": table},
    )
    return r.fetchone() is not None


def _index_exists(index: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname=:i"),
        {"i": index},
    )
    return r.fetchone() is not None


def upgrade() -> None:
    # ── New columns on service_packages ──────────────────────────────
    pkg_cols = [
        ("short_description",     sa.Column("short_description",     sa.String(300),      nullable=True)),
        ("rich_description_json", sa.Column("rich_description_json", JSONB,               nullable=True)),
        ("rich_description_html", sa.Column("rich_description_html", sa.Text,             nullable=True)),
        ("badge_label",           sa.Column("badge_label",           sa.String(50),       nullable=True)),
        ("cta_label",             sa.Column("cta_label",             sa.String(80),       nullable=True)),
        ("terms_summary",         sa.Column("terms_summary",         sa.Text,             nullable=True)),
        ("terms_content_json",    sa.Column("terms_content_json",    JSONB,               nullable=True)),
        ("trial_days",            sa.Column("trial_days",            sa.Integer,          nullable=True)),
        ("is_featured",           sa.Column("is_featured",           sa.Boolean,          nullable=False,
                                            server_default="false")),
        ("is_recommended",        sa.Column("is_recommended",        sa.Boolean,          nullable=False,
                                            server_default="false")),
        ("bonus_credits",         sa.Column("bonus_credits",         sa.Numeric(12, 2),   nullable=True)),
        ("lead_credits",          sa.Column("lead_credits",          sa.Integer,          nullable=True)),
        ("setup_fee_amount",      sa.Column("setup_fee_amount",      sa.Numeric(12, 2),   nullable=True)),
        ("renewal_price_amount",  sa.Column("renewal_price_amount",  sa.Numeric(12, 2),   nullable=True)),
        ("refund_policy",         sa.Column("refund_policy",         sa.Text,             nullable=True)),
        ("metadata_json",         sa.Column("metadata_json",         JSONB,               nullable=True)),
    ]
    for col_name, col_obj in pkg_cols:
        if not _col_exists("service_packages", col_name):
            op.add_column("service_packages", col_obj)

    # ── package_features ─────────────────────────────────────────────
    if not _table_exists("package_features"):
        op.create_table(
            "package_features",
            sa.Column("id",                  UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("package_id",          UUID(as_uuid=True),
                      sa.ForeignKey("service_packages.id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("feature_key",         sa.String(100),  nullable=True),
            sa.Column("feature_label",       sa.String(200),  nullable=False),
            sa.Column("feature_description", sa.Text,         nullable=True),
            sa.Column("feature_icon",        sa.String(100),  nullable=True),
            sa.Column("is_highlighted",      sa.Boolean,      nullable=False, server_default="false"),
            sa.Column("is_included",         sa.Boolean,      nullable=False, server_default="true"),
            sa.Column("display_order",       sa.Integer,      nullable=False, server_default="0"),
            sa.Column("status",              sa.String(20),   nullable=False, server_default="'active'"),
            sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at",          sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        )
    if not _index_exists("ix_pkgfeat_package_id"):
        op.create_index("ix_pkgfeat_package_id",     "package_features", ["package_id"])
    if not _index_exists("ix_pkgfeat_display_order"):
        op.create_index("ix_pkgfeat_display_order",  "package_features", ["display_order"])

    # ── package_limits ────────────────────────────────────────────────
    if not _table_exists("package_limits"):
        op.create_table(
            "package_limits",
            sa.Column("id",           UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("package_id",   UUID(as_uuid=True),
                      sa.ForeignKey("service_packages.id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("limit_key",    sa.String(100),   nullable=False),
            sa.Column("limit_label",  sa.String(200),   nullable=False),
            sa.Column("limit_value",  sa.Numeric(12, 2), nullable=True),
            sa.Column("limit_unit",   sa.String(50),    nullable=True),
            sa.Column("is_unlimited", sa.Boolean,       nullable=False, server_default="false"),
            sa.Column("display_order",sa.Integer,       nullable=False, server_default="0"),
            sa.Column("status",       sa.String(20),    nullable=False, server_default="'active'"),
            sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("deleted_at",   sa.DateTime(timezone=True), nullable=True),
        )
    if not _index_exists("ix_pkglim_package_id"):
        op.create_index("ix_pkglim_package_id",     "package_limits", ["package_id"])
    if not _index_exists("ix_pkglim_display_order"):
        op.create_index("ix_pkglim_display_order",  "package_limits", ["display_order"])


def downgrade() -> None:
    pass  # intentionally left — additive migration
