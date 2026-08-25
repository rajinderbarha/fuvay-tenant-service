"""Make existing Customer Home campaigns evergreen by default.

Revision ID: 309
Revises: 308
"""

from alembic import op


revision = "309"
down_revision = "308"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Early Customer Home rules inherited a generic three-deliveries-per-day
    # default. That made the hero disappear while an operator was previewing
    # the app. Zero is the explicit, supported representation for evergreen.
    op.execute(
        """
        UPDATE marketing_campaign_rules
           SET rule_config = jsonb_set(
                   COALESCE(rule_config, '{}'::jsonb),
                   '{frequency_cap_per_day}',
                   '0'::jsonb,
                   true
               ),
               updated_at = now()
         WHERE rule_type = 'channel'
           AND rule_config->>'surface' = 'customer_home'
           AND COALESCE((rule_config->>'frequency_cap_per_day')::integer, 3) <= 3
        """
    )


def downgrade() -> None:
    # Restoring an implicit cap could unexpectedly hide live content, so the
    # data correction is intentionally retained on downgrade.
    pass
