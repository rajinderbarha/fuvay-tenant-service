"""Disable the dynamic `hs_completed_job_deduction` catalog module.

USER REQ: audit and correct the Completed Job Deduction page -- remove the
standalone page/nav entry after migrating its real capability to
Finance -> Home Services Finance -> Completion Charges.

Same shape as migrations 173/174/175: this dynamic module leaked into the
live sidebar independently of AdminLayout.tsx's static
HOME_SERVICES_EXTRA_ITEMS array (which no longer lists
"hs-completed-job-deduction" as of this change). The new "Home Services
Finance" entry is a STATIC NAV_GROUPS item (under Finance, not a per-vertical
dynamic module), so no replacement dynamic-module row is created here.

Revision ID: 176
Revises: 175
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "176"
down_revision = "175"
branch_labels = None
depends_on = None

_RETIRED_MODULE_KEYS = ("hs_completed_job_deduction",)


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
    print(f"[176] disabled {result.rowcount} vertical_catalog_modules rows (hs_completed_job_deduction)")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
        SET is_enabled = true
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(_RETIRED_MODULE_KEYS)})
