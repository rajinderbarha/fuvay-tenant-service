"""P0 Sidebar Duplicate Menu Cleanup — dedupe Home Services vertical catalog modules.

Brands, Brand Requests, Pricing Tiers, City/Zip Mapping, and Pricing Rules were
mapped both as globally-universal `catalog_module_definitions` (is_universal=true,
rendered as static top-level sidebar items) AND as `vertical_catalog_modules`
entries under the `home_services` vertical (rendered again inside the Home
Services vertical section) — showing the exact same route twice in the sidebar.
Types & Brands already exists as the canonical Home-Services brand entry point;
Pricing Tiers/City-Zip Mapping/Pricing Rules have their own canonical "Pricing"
sidebar group. This migration soft-disables (is_enabled=false) the redundant
home_services junction rows — non-destructive, reversible, matches the pattern
used elsewhere in vertical_catalog_modules.

Revision ID: 096
Revises: 095
"""
from alembic import op
import sqlalchemy as sa

revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None

_DUPLICATE_MODULE_KEYS = ("brands", "brand_requests", "pricing_tiers", "location_mapping", "pricing_rules")


def upgrade() -> None:
    conn = op.get_bind()
    for key in _DUPLICATE_MODULE_KEYS:
        conn.execute(sa.text("""
            UPDATE vertical_catalog_modules vcm
            SET is_enabled = false, updated_at = now()
            FROM verticals v, catalog_module_definitions cmd
            WHERE vcm.vertical_id = v.id AND vcm.module_id = cmd.id
              AND v.key = 'home_services' AND cmd.key = :key
              AND vcm.is_enabled = true
        """), {"key": key})


def downgrade() -> None:
    conn = op.get_bind()
    for key in _DUPLICATE_MODULE_KEYS:
        conn.execute(sa.text("""
            UPDATE vertical_catalog_modules vcm
            SET is_enabled = true, updated_at = now()
            FROM verticals v, catalog_module_definitions cmd
            WHERE vcm.vertical_id = v.id AND vcm.module_id = cmd.id
              AND v.key = 'home_services' AND cmd.key = :key
        """), {"key": key})
