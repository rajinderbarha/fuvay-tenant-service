"""Disable the dynamic `service_options`/`issue_types` catalog modules --
retired standalone admin nav entries that were still leaking into the live
sidebar.

USER REQ: "remove service option, issue type from admin menu"

Root cause, same shape as migration 163's pricing_tiers/location_mapping/
pricing_rules fix: `frontend/super-admin/lib/nav-config.ts` already marks
Service Options and Issue Types as "retired as standalone nav entries" (Job-
Type Blueprint consolidation -- both are now configured only per exact Job
Type inside Catalog Workspace's Options & Add-ons and Problems & Questions
tabs, per MODULE-L5-56), and their route files (`/admin/service-options`,
`/admin/issue-types`) are retired-notice redirects, not real pages. But the
sidebar actually renders from the backend's dynamic effective-menu
(GET /v1/admin/catalog/navigation/effective-menu), which reads
`vertical_catalog_modules.is_enabled` independently of the static nav config
-- confirmed live: `service_options` enabled under `home_services` AND
`beauty`, `issue_types` enabled under `home_services`. MODULE-L5-56's own
test file (test_module_l5_56_blueprint_consolidation.py) explicitly flagged
this dynamic-module disablement as deferred/out of that ticket's scope --
this migration closes that gap.

Both module definitions already have is_universal=false (confirmed live),
so a per-vertical `is_enabled` disable is sufficient here -- no second gate
to flip (unlike migration 164's pricing_tiers/location_mapping universal-flag
leak).

Revision ID: 173
Revises: 172
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "173"
down_revision = "172"
branch_labels = None
depends_on = None

_RETIRED_MODULE_KEYS = ("service_options", "issue_types")


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
    print(f"[173] disabled {result.rowcount} vertical_catalog_modules rows "
          f"(service_options/issue_types) across all verticals")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
