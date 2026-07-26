"""Disable the dynamic `hs_overview` catalog module.

USER REQ: "also delete overview page in home services"

The Home Services "Overview" page's route directory
(frontend/super-admin/app/admin/home-services/overview/) had no page.tsx --
a dead nav link (404) -- and has now been deleted along with its nav entry
in AdminLayout.tsx's HOME_SERVICES_EXTRA_ITEMS. Same shape as migration 173:
the sidebar renders from the dynamic effective-menu
(GET /v1/admin/catalog/navigation/effective-menu), which independently reads
`vertical_catalog_modules.is_enabled` -- `hs_overview` was enabled for
`home_services` (seeded live-only, reconstructed by migration 165) and would
otherwise keep appearing even with the frontend nav entry and route removed.

Revision ID: 174
Revises: 173
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "174"
down_revision = "173"
branch_labels = None
depends_on = None

_RETIRED_MODULE_KEYS = ("hs_overview",)


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
    print(f"[174] disabled {result.rowcount} vertical_catalog_modules rows (hs_overview)")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
