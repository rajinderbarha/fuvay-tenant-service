"""Disable the duplicate `brands`/`brand_requests` modules under Home
Services -- another leak from migration 159's reseed replaying the ORIGINAL
migration 089 seed data, which predates the later "Sidebar Duplicate
Cleanup" sprint (tests/test_p0_sidebar_duplicate_cleanup.py) that removed
them in favor of the single consolidated `types_brands` entry.

Confirmed via that test's own assertions (test_home_services_excludes_
brand_and_pricing_modules expects brands/brand_requests absent;
test_home_services_keeps_canonical_items expects types_brands present) --
not a guess, the target end-state is already documented in an existing
test that predates this fix.

Scoped to home_services only -- no other vertical has both `types_brands`
and `brands`/`brand_requests` assigned (confirmed live), so this is not a
platform-wide duplicate the way pricing_tiers/location_mapping/pricing_rules
were in migration 163.

Revision ID: 166
Revises: 165
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "166"
down_revision = "165"
branch_labels = None
depends_on = None

_DUPLICATE_KEYS = ("brands", "brand_requests")


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = false
        WHERE module_id IN (SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys))
          AND vertical_id IN (SELECT id FROM verticals WHERE key = 'home_services')
        RETURNING id
    """), {"keys": list(_DUPLICATE_KEYS)})
    print(f"[166] disabled {result.rowcount} duplicate brands/brand_requests rows under Home Services")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys))
          AND vertical_id IN (SELECT id FROM verticals WHERE key = 'home_services')
    """), {"keys": list(_DUPLICATE_KEYS)})
