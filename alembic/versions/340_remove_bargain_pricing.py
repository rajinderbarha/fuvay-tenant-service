"""Remove bargaining from the active product and persisted booking contracts.

Revision ID: 340
Revises: 339
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID


revision = "340"
down_revision = "339"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()

    # Remove legacy controls so an upgraded installation cannot re-enable the
    # retired feature from a stale setting or feature-flag client.
    if "platform_settings" in tables:
        op.execute("""
            DELETE FROM platform_settings
             WHERE key IN ('bargain_enabled', 'bargain_floor_enforced',
                           'bargain_floor_formula')
        """)
        op.execute("""
            UPDATE platform_settings
               SET category = 'pricing', updated_at = now()
             WHERE category = 'pricing_and_bargain'
        """)
    if "feature_flags" in tables:
        op.execute("""
            DELETE FROM feature_flags
             WHERE flag_key IN ('manual_bargain_rules_enabled',
                                'auto_price_options_enabled')
        """)

    # Strip obsolete keys from snapshots while retaining the immutable agreed
    # price, platform fee, provider and inspection evidence.
    if "home_service_booking_drafts" in tables:
        op.execute("""
            UPDATE home_service_booking_drafts
               SET price_snapshot = price_snapshot - 'bargain_available' - 'price_options',
                   booking_summary = CASE
                       WHEN booking_summary ? 'customer_offer' THEN
                           (booking_summary - 'bargain_available' - 'customer_offer'
                                            - 'allowed_offer_min' - 'allowed_offer_max')
                           || jsonb_build_object('agreed_price', booking_summary->'customer_offer')
                       ELSE booking_summary - 'bargain_available'
                   END
             WHERE price_snapshot ?| ARRAY['bargain_available', 'price_options']
                OR booking_summary ?| ARRAY['bargain_available', 'customer_offer',
                                             'allowed_offer_min', 'allowed_offer_max']
        """)
    if "service_bookings" in tables:
        op.execute("""
            UPDATE service_bookings
               SET price_snapshot = price_snapshot - 'bargain_available' - 'price_options'
             WHERE price_snapshot ?| ARRAY['bargain_available', 'price_options']
        """)

    if "bargain_rules" in tables:
        op.drop_table("bargain_rules")
    if "service_pricing_rules" in tables and "bargain_floor" in _columns("service_pricing_rules"):
        op.drop_column("service_pricing_rules", "bargain_floor")
    if "city_tier_configs" in tables and "bargain_floor" in _columns("city_tier_configs"):
        op.drop_column("city_tier_configs", "bargain_floor")


def downgrade() -> None:
    tables = _tables()
    if "service_pricing_rules" in tables and "bargain_floor" not in _columns("service_pricing_rules"):
        op.add_column("service_pricing_rules", sa.Column("bargain_floor", sa.Numeric(12, 2), nullable=True))
    if "city_tier_configs" in tables and "bargain_floor" not in _columns("city_tier_configs"):
        op.add_column("city_tier_configs", sa.Column("bargain_floor", sa.Numeric(10, 2), nullable=True))
    if "bargain_rules" not in tables:
        op.create_table(
            "bargain_rules",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("vertical_key", sa.String(50), nullable=True),
            sa.Column("category_id", UUID(as_uuid=True), nullable=True),
            sa.Column("master_service_id", UUID(as_uuid=True), nullable=True),
            sa.Column("pricing_rule_id", UUID(as_uuid=True), sa.ForeignKey("service_pricing_rules.id", ondelete="CASCADE"), nullable=True),
            sa.Column("rule_name", sa.String(200), nullable=True),
            sa.Column("rule_code", sa.String(80), nullable=True),
            sa.Column("bargain_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("floor_type", sa.String(20), nullable=False, server_default="fixed"),
            sa.Column("floor_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("customer_min_price", sa.Numeric(12, 2), nullable=True),
            sa.Column("customer_max_price", sa.Numeric(12, 2), nullable=True),
            sa.Column("platform_fee_percent", sa.Numeric(6, 2), nullable=True),
            sa.Column("platform_fee_fixed_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("below_floor_action", sa.String(20), nullable=False, server_default="reject"),
            sa.Column("provider_approval_required", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("max_attempts", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_bargain_rules_pricing_rule", "bargain_rules", ["pricing_rule_id"])
        op.create_index("ix_bargain_rules_master_service", "bargain_rules", ["master_service_id"])
        op.create_index("ix_bargain_rules_status", "bargain_rules", ["status"])
