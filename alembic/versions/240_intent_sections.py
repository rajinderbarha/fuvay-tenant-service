"""Two intent-grouped sections on Home: things to repair, and things to ask about.

The problem list mixes two customer intents. "AC Not Cooling" is a fault someone
wants fixed; "New AC Installation" or a site visit is work to be scoped and quoted.
A customer arrives in one mode or the other, so a single mixed list makes them read
past most of it.

Seeded DISABLED. Both draw from the same authored problem list as the grids above
them, and on a catalogue with few consult-type entries one of them would render
nothing while the other repeats what is already on screen -- whether that trade is
worth it is a layout decision for admin, not for a migration. Enable either on the
Home Layout page.

Revision ID: 240
Revises: 239
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "240"
down_revision = "239"
branch_labels = None
depends_on = None

SECTIONS = (("repair_intent", 76), ("consult_intent", 77))


def upgrade() -> None:
    for key, order in SECTIONS:
        op.execute(
            sa.text(
                "INSERT INTO home_section_settings (section_key, is_enabled, display_order) "
                "VALUES (:k, false, :o) ON CONFLICT (section_key) DO NOTHING"
            ).bindparams(k=key, o=order)
        )


def downgrade() -> None:
    for key, _ in SECTIONS:
        op.execute(sa.text("DELETE FROM home_section_settings WHERE section_key = :k").bindparams(k=key))
