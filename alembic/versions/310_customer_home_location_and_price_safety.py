"""Make Customer Home recommendations PIN-safe and price-free.

Revision ID: 310
Revises: 309
"""

from alembic import op


revision = "310"
down_revision = "309"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AC is the only provider-backed service group in the current catalogue.
    # Remove the old speculative "From ₹..." copy and map the campaign to the
    # group so it is projected only in PIN codes where AC is actually bookable.
    op.execute(
        """
        UPDATE marketing_campaign_rules AS rule
           SET rule_config = (rule.rule_config - 'offer_text')
                           || jsonb_build_object('service_group_slug', 'ac_services'),
               updated_at = now()
          FROM marketing_campaigns AS campaign
         WHERE campaign.id = rule.campaign_id
           AND rule.rule_type = 'channel'
           AND rule.rule_config->>'surface' = 'customer_home'
           AND rule.rule_config->>'placement' = 'home_recommendation'
           AND campaign.campaign_name ILIKE '%AC%'
        """
    )

    # Drain Cleaning has no active provider-backed service group in this
    # deployment. Keeping it live produced a dead-end recommendation.
    op.execute(
        """
        UPDATE marketing_campaigns AS campaign
           SET status = 'draft', updated_at = now()
         WHERE campaign.campaign_name ILIKE '%Drain%'
           AND EXISTS (
               SELECT 1
                 FROM marketing_campaign_rules AS rule
                WHERE rule.campaign_id = campaign.id
                  AND rule.rule_type = 'channel'
                  AND rule.rule_config->>'surface' = 'customer_home'
           )
        """
    )


def downgrade() -> None:
    # Do not reintroduce a misleading price or an unbookable promotion.
    pass
