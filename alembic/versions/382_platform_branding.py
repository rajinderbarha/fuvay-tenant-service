"""Seed runtime-configurable platform brand identity.

Revision ID: 382
Revises: 381
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "382"
down_revision = "381"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "platform_settings" not in sa.inspect(op.get_bind()).get_table_names():
        return
    bind = op.get_bind()
    exists = bind.execute(sa.text(
        "SELECT 1 FROM platform_settings WHERE key = 'platform_branding'"
    )).scalar()
    if exists:
        return
    platform_settings = sa.table(
        "platform_settings",
        sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("setting_type", sa.String), sa.column("label", sa.String),
        sa.column("description", sa.Text), sa.column("category", sa.String),
        sa.column("is_public", sa.Boolean), sa.column("is_secret", sa.Boolean),
        sa.column("risk_level", sa.String), sa.column("requires_approval", sa.Boolean),
        sa.column("requires_restart", sa.Boolean), sa.column("is_runtime_editable", sa.Boolean),
        sa.column("owner_module", sa.String), sa.column("status", sa.String),
    )
    op.bulk_insert(platform_settings, [{
        "key": "platform_branding",
        "value": {"v": {
            "brand_name": "Fuvay", "short_name": "Fuvay", "tagline": "Far Away Is Fare Way",
            "logo_light_url": None, "logo_dark_url": None, "brand_mark_url": None,
            "favicon_url": None, "apple_touch_icon_url": None, "email_logo_url": None,
            "document_logo_url": None, "social_share_image_url": None,
            "primary_color": "#0F6B60", "accent_color": "#2F9E8F",
        }},
        "setting_type": "json", "label": "Platform Brand Identity",
        "description": "Public logos, icons, names and brand colours used across ServiceOS surfaces.",
        "category": "general_platform", "is_public": True, "is_secret": False,
        "risk_level": "high", "requires_approval": False, "requires_restart": False,
        "is_runtime_editable": True, "owner_module": "platform_branding", "status": "active",
    }])


def downgrade() -> None:
    if "platform_settings" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.execute("""
        DELETE FROM platform_settings
         WHERE key = 'platform_branding'
           AND owner_module = 'platform_branding'
    """)
