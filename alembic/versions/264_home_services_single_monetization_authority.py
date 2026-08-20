"""Home Services uses one monetization authority.

Revision ID: 264
Revises: 263

Provider and customer charge configuration for Home Services belongs only
to the published VerticalMonetizationPolicy. Historical category-level
values are cleared so administration and reporting cannot imply a second
active policy.
"""
from __future__ import annotations

from alembic import op

revision = "264"
down_revision = "263"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE service_categories
        SET commission_pct = NULL,
            customer_charge_pct = NULL,
            updated_at = now()
        WHERE vertical_type = 'home_services'
          AND (commission_pct IS NOT NULL OR customer_charge_pct IS NOT NULL)
        """
    )


def downgrade() -> None:
    # Cleared policy values cannot be reconstructed safely. The columns stay
    # available for verticals that have not migrated to dedicated finance.
    pass
