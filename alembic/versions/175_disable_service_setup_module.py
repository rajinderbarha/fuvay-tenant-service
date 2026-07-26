"""Disable the dynamic `service_setup` catalog module.

USER REQ: "remove this page http://localhost:3000/admin/service-setup from menu"

Same shape as migrations 173/174: the "Service Setup" sidebar entry was not
in any static nav file (nav-config.ts nor AdminLayout.tsx's NAV_GROUPS/
HOME_SERVICES_EXTRA_ITEMS -- confirmed absent from both) -- it renders from
the dynamic effective-menu (GET /v1/admin/catalog/navigation/effective-menu),
which reads `vertical_catalog_modules.is_enabled` independently of any
frontend nav config. Confirmed live: `service_setup` enabled for
`home_services`. The page itself (/admin/service-setup and its sub-routes)
is left in place and still reachable by direct URL -- only the menu entry is
removed, per the request.

Revision ID: 175
Revises: 174
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "175"
down_revision = "174"
branch_labels = None
depends_on = None

_RETIRED_MODULE_KEYS = ("service_setup",)


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
    print(f"[175] disabled {result.rowcount} vertical_catalog_modules rows (service_setup)")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
