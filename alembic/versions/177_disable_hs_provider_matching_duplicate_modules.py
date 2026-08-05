"""Disable the dynamic `hs_provider_matching`, `hs_bookability`,
`hs_matching_diagnostics`, and `hs_settings` catalog modules.

USER REQ: "there are duplicate menuin home service so check and remove
duplicate"

Root cause: `hs_provider_matching` is enabled both as a generic dynamic
catalog module (`vertical_catalog_modules`, seeded by migration 165) AND as
a hardcoded entry in AdminLayout.tsx's HOME_SERVICES_EXTRA_ITEMS array --
the sidebar's VerticalCatalogSection renders `modules` and `extraItems` back
to back with no de-duplication, so "Provider Matching" appears twice under
Home Services.

The other three keys here (`hs_bookability`, `hs_matching_diagnostics`,
`hs_settings`) are not literal duplicates but the same underlying bug: per
AdminLayout.tsx's own comments, all three were explicitly retired from
HOME_SERVICES_EXTRA_ITEMS during the UX-05 consolidation (Bookability's
capability moved into Provider Matching's "Provider Eligibility" tab;
Matching Diagnostics merged into Provider Matching's own tabs; Settings
moved into Business Verticals > Home Services > Capabilities & Policies) --
but migration 165's reseed still leaves their `vertical_catalog_modules`
rows enabled, so they keep reappearing as dead/redirect-only links
independently of the frontend nav config, exactly like hs_overview (174),
service_setup (175), and hs_completed_job_deduction (176) before them.

Revision ID: 177
Revises: 176
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "177"
down_revision = "176"
branch_labels = None
depends_on = None

_RETIRED_MODULE_KEYS = (
    "hs_provider_matching",
    "hs_bookability",
    "hs_matching_diagnostics",
    "hs_settings",
)


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
    print(f"[177] disabled {result.rowcount} vertical_catalog_modules rows "
          f"(hs_provider_matching duplicate + 3 retired hs modules)")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
