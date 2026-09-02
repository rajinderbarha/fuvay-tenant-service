"""Retire the last public security-deposit finance-model key.

Revision ID: 335
Revises: 334

The security-deposit tables and behavior were removed in revisions 317, 318,
330, 331 and 334. Category and vertical configuration could still expose the
legacy ``security_deposit_plus_credit_wallet`` identifier even though runtime
behavior was credit-and-seats only. Rename existing values so APIs, Admin UI,
and stored configuration all describe the model that actually runs.
"""
from alembic import op


revision = "335"
down_revision = "334"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE service_categories
           SET finance_model = 'credit_wallet_only'
         WHERE finance_model = 'security_deposit_plus_credit_wallet'
    """)
    op.execute("""
        UPDATE verticals
           SET finance_model = 'credit_wallet_only'
         WHERE finance_model = 'security_deposit_plus_credit_wallet'
    """)


def downgrade() -> None:
    # Intentionally one-way. ``credit_wallet_only`` was already a valid value
    # before this migration, so changing every such row back would corrupt
    # legitimate configuration that never used the retired key.
    pass
