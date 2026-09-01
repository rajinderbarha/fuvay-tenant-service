"""Remove the retired security deposit from provider health scoring.

Revision ID: 330
Revises: 329
"""
from alembic import op


revision = "330"
down_revision = "329"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM health_penalty_rules
         WHERE metric_key = 'security_deposit_missing'
           AND formula_id IN (
               SELECT id FROM health_formulas
                WHERE formula_key = 'provider_business_health_default'
           )
    """)
    op.execute("""
        DELETE FROM health_formula_components
         WHERE metric_key = 'security_deposit_score'
           AND formula_id IN (
               SELECT id FROM health_formulas
                WHERE formula_key = 'provider_business_health_default'
           )
    """)
    op.execute("""
        UPDATE health_formula_components
           SET weight_percent = 20,
               updated_at = now()
         WHERE metric_key = 'usage_credit_score'
           AND formula_id IN (
               SELECT id FROM health_formulas
                WHERE formula_key = 'provider_business_health_default'
           )
    """)


def downgrade() -> None:
    # The retired deposit columns and metric source no longer exist, so this
    # data cleanup is intentionally not reversible.
    pass
