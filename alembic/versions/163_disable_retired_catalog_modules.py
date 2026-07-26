"""Disable retired catalog modules that migration 159's reseed brought back.

USER REQ: "pricing tier, price rule and zip/city mapping are retired but
still showing in home service menu so remove these."

Root cause: migration 159 reseeded `vertical_catalog_modules` from the
ORIGINAL seed data in migration 089/090, which predates a later product
decision (documented in frontend/super-admin/components/layout/
AdminLayout.tsx's HOME_SERVICES_EXTRA_ITEMS comments) to retire admin-
defined price-boundary tiers, city/zipcode-to-tier mapping, and
service-level admin min/max pricing rules platform-wide -- "this platform
is provider-set-price, not admin-defined price boundaries." The hardcoded
frontend nav array was already updated for that decision, but the sidebar
now actually renders from the backend's dynamic effective-menu
(GET /v1/admin/catalog/navigation/effective-menu), which reads
`vertical_catalog_modules.is_enabled` -- migration 159 unknowingly
re-enabled the retired modules there for every vertical.

Fix: disable (not delete -- preserve the historical module definitions and
assignment rows) `pricing_tiers`, `location_mapping`, and `pricing_rules`
for every vertical. This is a real, current fact about the platform
(confirmed live: PricingTier/TierLocation writes already return 410
PRICING_TIER_WRITES_RETIRED), not a guess.

Revision ID: 163
Revises: 162
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "163"
down_revision = "162"
branch_labels = None
depends_on = None

_RETIRED_MODULE_KEYS = ("pricing_tiers", "location_mapping", "pricing_rules")


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = false
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
        RETURNING id
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
    print(f"[162] disabled {result.rowcount} retired vertical_catalog_modules rows "
          f"(pricing_tiers/location_mapping/pricing_rules) across all verticals")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
