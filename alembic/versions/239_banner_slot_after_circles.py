"""A sixth banner slot, directly under the circular problem section.

Asked for after `problem_circles` shipped: the screen had no way to place a
promotion between that section and Build with Fuvay. Like every other slot it is a
Home SECTION, so it can be re-ordered, renamed or switched off from admin, and it
renders as a carousel once it holds more than one banner.

Enabled, but empty until a banner is scheduled into it -- an empty slot draws
nothing and takes no space, so enabling it costs the customer nothing while saving
an extra step later.

Revision ID: 239
Revises: 238
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "239"
down_revision = "238"
branch_labels = None
depends_on = None

KEY = "campaign_after_circles"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO home_section_settings (section_key, is_enabled, display_order) "
            "VALUES (:k, true, 78) ON CONFLICT (section_key) DO NOTHING"
        ).bindparams(k=KEY)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM home_section_settings WHERE section_key = :k").bindparams(k=KEY))
