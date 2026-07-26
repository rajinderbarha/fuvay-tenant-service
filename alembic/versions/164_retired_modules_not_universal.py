"""Second leak in the same bug (migration 163 fixed the first): `pricing_tiers`
and `location_mapping` are marked `is_universal = true` on
catalog_module_definitions itself (from the original migration 089 seed),
so get_effective_menu()'s `universal_modules` list renders them for EVERY
vertical unconditionally, bypassing the per-vertical `vertical_catalog_
modules.is_enabled` flag entirely (that's what `is_universal` means: shown
regardless of vertical). Confirmed live via GET /v1/admin/catalog/
navigation/effective-menu -- both still appeared in `universal_modules`
after migration 163 disabled every per-vertical assignment.

`pricing_rules` is NOT universal (home_services-only in the original seed),
so migration 163 alone was sufficient for it.

Fix: these two module DEFINITIONS are retired, not just unassigned from
verticals -- flip is_universal to false so they stop appearing anywhere.
Definitions are kept (not deleted) for historical/audit continuity, same
as the vertical_catalog_modules rows in migration 163.

Revision ID: 164
Revises: 163
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "164"
down_revision = "163"
branch_labels = None
depends_on = None

_RETIRED_UNIVERSAL_KEYS = ("pricing_tiers", "location_mapping")


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        UPDATE catalog_module_definitions
        SET is_universal = false
        WHERE key = ANY(:keys)
        RETURNING id
    """), {"keys": list(_RETIRED_UNIVERSAL_KEYS)})
    print(f"[164] un-universaled {result.rowcount} retired module definitions "
          f"(pricing_tiers/location_mapping)")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE catalog_module_definitions
        SET is_universal = true
        WHERE key = ANY(:keys)
    """), {"keys": list(_RETIRED_UNIVERSAL_KEYS)})
