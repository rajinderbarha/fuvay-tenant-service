"""Seed public customer-app version and store-link configuration.

Revision ID: 343
Revises: 342
"""
from alembic import op
import sqlalchemy as sa


revision = "343"
down_revision = "342"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "platform_settings" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.execute("""
        INSERT INTO platform_settings
            (key, value, setting_type, label, category, is_public, is_secret,
             risk_level, requires_approval, requires_restart,
             is_runtime_editable, owner_module, status)
        VALUES
            ('customer_min_supported_version', '"1.0.0"'::jsonb, 'string',
             'Customer App Minimum Version', 'general_platform', true, false,
             'high', false, false, true, 'customer_app', 'active'),
            ('customer_ios_store_url', '""'::jsonb, 'string',
             'Customer iOS Store URL', 'general_platform', true, false,
             'low', false, false, true, 'customer_app', 'active'),
            ('customer_android_store_url', '""'::jsonb, 'string',
             'Customer Android Store URL', 'general_platform', true, false,
             'low', false, false, true, 'customer_app', 'active')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    if "platform_settings" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.execute("""
        DELETE FROM platform_settings
         WHERE key IN ('customer_min_supported_version',
                       'customer_ios_store_url',
                       'customer_android_store_url')
           AND owner_module = 'customer_app'
    """)
