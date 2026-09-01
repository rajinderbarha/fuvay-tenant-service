"""Publish the approved native customer Home composition.

Revision ID: 325
Revises: 324

The app owns a finite set of accessible native components. Admin still owns
their order, visibility, title, item cap, spacing, surface and allowed variant;
this only replaces the old four-section seed with the approved marketplace
starting point.
"""

import json

import sqlalchemy as sa
from alembic import op


revision = "325"
down_revision = "324"
branch_labels = None
depends_on = None


SECTIONS = [
    {"key": "hero", "title": None, "enabled": True, "spacing": "compact", "surface": "canvas", "variant": "marketplace", "max_items": 5},
    {"key": "service_groups", "title": "Popular Service", "enabled": True, "spacing": "compact", "surface": "canvas", "variant": "compact_grid", "max_items": 8},
    {"key": "live_booking", "title": "Live Booking", "enabled": True, "spacing": "compact", "surface": "canvas", "variant": "timeline", "max_items": 1},
    {"key": "master_services", "title": "Recommended for you", "enabled": True, "spacing": "compact", "surface": "canvas", "variant": "recommendation_cards", "max_items": 5},
    {"key": "spotlight", "title": "Spotlights", "enabled": True, "spacing": "compact", "surface": "canvas", "variant": "cinematic_card", "max_items": 3},
    {"key": "global_services", "title": "Build with Fuvay", "enabled": True, "spacing": "compact", "surface": "canvas", "variant": "compact_services", "max_items": 5},
    {"key": "nearby_services", "title": "Services Nearby", "enabled": False, "spacing": "compact", "surface": "canvas", "variant": "two_row", "max_items": 8},
    {"key": "recent_bookings", "title": "More Active Booking", "enabled": False, "spacing": "compact", "surface": "canvas", "variant": "compact_rail", "max_items": 1},
    {"key": "assistant", "title": None, "enabled": False, "spacing": "compact", "surface": "canvas", "variant": "command_strip", "max_items": 1},
    {"key": "trust_strip", "title": None, "enabled": False, "spacing": "compact", "surface": "subtle", "variant": "icon_row", "max_items": 4},
    {"key": "featured_problems", "title": "What Needs Fixing", "enabled": False, "spacing": "compact", "surface": "canvas", "variant": "photo_cards", "max_items": 4},
    {"key": "featured_services", "title": "More home services", "enabled": False, "spacing": "compact", "surface": "canvas", "variant": "catalog_grid", "max_items": 6},
    {"key": "banners", "title": None, "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "contained", "max_items": 4},
    {"key": "collection", "title": "Offers for you", "enabled": False, "spacing": "compact", "surface": "canvas", "variant": "editorial_cards", "max_items": 8},
    {"key": "stories", "title": "Ideas and offers", "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "landscape", "max_items": 8},
    {"key": "mosaic", "title": "Fresh ways to care for home", "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "asymmetric", "max_items": 3},
    {"key": "active_bookings", "title": "More active bookings", "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "stack", "max_items": 3},
    {"key": "repair_problems", "title": "Repairs you can book now", "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "editorial_rail", "max_items": 12},
    {"key": "consultation_problems", "title": "Get an expert opinion", "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "editorial_list", "max_items": 8},
    {"key": "more_problems", "title": "More ways we can help", "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "compact_grid", "max_items": 12},
    {"key": "notices", "title": None, "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "strips", "max_items": 2},
    {"key": "support_actions", "title": None, "enabled": False, "spacing": "standard", "surface": "canvas", "variant": "utility_rows", "max_items": 2},
]


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE platform_settings
               SET value = CAST(:value AS jsonb),
                   updated_at = now()
             WHERE key = 'customer_home.section_composition.v1'
            """
        ),
        {"value": json.dumps({"v": SECTIONS})},
    )


def downgrade() -> None:
    # A downgrade must not silently republish a stale customer experience.
    pass
