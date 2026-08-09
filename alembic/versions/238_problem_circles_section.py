"""A second problem surface, in circles, above Build with Fuvay.

`quick_problems` shows a small shortlist as square tiles. This adds a larger
circular one lower down the screen: the same real problem list, a different
selection, and a different visual weight -- so a customer who did not find their
fault in the shortlist meets more of the catalogue further down instead of having
to open a sheet.

Seeded at 75 so it sits between the mid banner slot and Build with Fuvay, which is
where it was asked for. Enabled: unlike an empty banner slot, this section has
real content to show on every deployment that has problems authored.

Revision ID: 238
Revises: 237
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "238"
down_revision = "237"
branch_labels = None
depends_on = None

KEY = "problem_circles"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO home_section_settings (section_key, is_enabled, display_order) "
            "VALUES (:k, true, 75) ON CONFLICT (section_key) DO NOTHING"
        ).bindparams(k=KEY)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM home_section_settings WHERE section_key = :k").bindparams(k=KEY))
