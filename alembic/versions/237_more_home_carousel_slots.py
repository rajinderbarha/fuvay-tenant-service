"""More image-carousel slots on Home, and a home for the how-it-works section.

Three campaign slots was too few to lay out a rich Home: admin could put banners
at the top, in the middle and at the bottom, but not (say) directly under the
problem grid where a seasonal push belongs, nor under the service grid. Each new
slot is a Home SECTION, so it can be re-ordered, renamed and switched off from
the same admin surface as everything else -- and each renders as a swipeable
carousel when it holds more than one banner.

`how_it_works` was already in the seeded vocabulary but the app had no renderer
wired for it, so the backend listed a key nothing could draw. It is now rendered;
this migration only records that it belongs in the order.

Revision ID: 237
Revises: 236
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "237"
down_revision = "236"
branch_labels = None
depends_on = None

# The full intended order, applied to every row so the layout is coherent after
# this migration rather than depending on whatever order it had before.
#
# Intent first: what is already happening to the customer, then the fastest route
# to a booking, then browsing, then the things that only help them decide.
# Promotions sit BELOW the shortcut they compete with, never above it.
ORDER = [
    "active_booking",
    "quick_problems",
    "campaign_top",
    "service_grid",
    "campaign_after_services",
    "assistant_entry",
    "campaign_mid",
    "global_services",
    "how_it_works",
    "trust_benefits",
    "campaign_bottom",
]

NEW_SECTIONS = ("campaign_after_problems", "campaign_after_services")


def upgrade() -> None:
    for key in NEW_SECTIONS:
        op.execute(
            sa.text(
                "INSERT INTO home_section_settings (section_key, is_enabled, display_order) "
                "VALUES (:k, :e, :o) ON CONFLICT (section_key) DO NOTHING"
            ).bindparams(k=key, e=True, o=1000)
        )

    # campaign_after_problems ships DISABLED: an empty slot costs nothing, but a
    # second banner immediately under the problem grid, enabled by default on
    # every deployment, is a layout decision that belongs to admin rather than to
    # a migration.
    op.execute(sa.text(
        "UPDATE home_section_settings SET is_enabled = false "
        "WHERE section_key = 'campaign_after_problems'"
    ))

    for index, key in enumerate(ORDER):
        op.execute(
            sa.text(
                "UPDATE home_section_settings SET display_order = :o WHERE section_key = :k"
            ).bindparams(o=(index + 1) * 10, k=key)
        )


def downgrade() -> None:
    for key in NEW_SECTIONS:
        op.execute(
            sa.text("DELETE FROM home_section_settings WHERE section_key = :k").bindparams(k=key)
        )
