"""Retire deposit-era settings and notification artifacts.

Revision ID: 331
Revises: 330
"""
from alembic import op


revision = "331"
down_revision = "330"
branch_labels = None
depends_on = None


_SETTING_KEYS = (
    "tenant_security_deposit_required",
    "security_deposit_enabled",
    "security_deposit_one_time_only",
    "security_deposit_adjustment_enabled",
    "security_deposit_deduction_requires_admin_approval",
    "security_deposit_refund_enabled",
    "security_deposit_used_for_dispute_recovery",
)


def upgrade() -> None:
    keys = ", ".join(f"'{key}'" for key in _SETTING_KEYS)
    op.execute(f"DELETE FROM tenant_settings WHERE key IN ({keys})")
    op.execute(f"DELETE FROM plan_settings WHERE key IN ({keys})")
    op.execute(f"DELETE FROM platform_settings WHERE key IN ({keys})")
    op.execute("""
        UPDATE platform_settings
           SET value = '"usage_credit"'::jsonb,
               allowed_values_json = '["usage_credit"]'::jsonb,
               updated_at = now()
         WHERE key = 'settlement_deduction_priority'
    """)
    op.execute("""
        UPDATE notification_templates
           SET status = 'archived', is_active = FALSE, archived_at = now(), updated_at = now()
         WHERE event_type = 'security_deposit_required'
            OR notif_type = 'security_deposit_required'
    """)


def downgrade() -> None:
    # Deposit state and tables no longer exist, so exposing these controls
    # again would be dishonest. This cleanup is intentionally one-way.
    pass
