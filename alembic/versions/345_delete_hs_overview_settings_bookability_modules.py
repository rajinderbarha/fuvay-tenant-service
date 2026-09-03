"""Delete the Home Services Overview / Settings / Bookability admin modules.

Removed at explicit product request: the three sidebar entries, their catalog
module registrations and their Next.js pages are gone (not hidden). This drops
the vertical_catalog_modules links and the catalog_module_definitions rows so
GET /v1/admin/catalog/navigation/effective-menu can never re-surface them.

Revision ID: 345
Revises: 344
"""
from alembic import op
from sqlalchemy import text


revision = "345"
down_revision = "344"
branch_labels = None
depends_on = None

MODULE_KEYS = ("hs_overview", "hs_settings", "hs_bookability")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("""
        DELETE FROM vertical_catalog_modules
        WHERE module_id IN (
            SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys)
        )
    """), {"keys": list(MODULE_KEYS)})
    bind.execute(text(
        "DELETE FROM catalog_module_definitions WHERE key = ANY(:keys)"
    ), {"keys": list(MODULE_KEYS)})


def downgrade() -> None:
    # Intentionally irreversible: the pages these modules pointed at were
    # deleted from the repo, so restoring the rows would only recreate 404s.
    pass
