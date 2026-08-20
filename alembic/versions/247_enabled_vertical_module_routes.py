"""Route enabled vertical modules to functional admin workspaces.

Revision ID: 247
Revises: 246
"""
from alembic import op
from sqlalchemy import text


revision = "247"
down_revision = "246"
branch_labels = None
depends_on = None


ROUTES = {
    "checklist_templates": "/admin/checklists",
    "property_types": "/admin/types-brands",
    "listing_types": "/admin/types-brands",
    "amenities": "/admin/service-options",
    "localities": "/admin/location-mapping",
}


def upgrade() -> None:
    connection = op.get_bind()
    for module_key, admin_path in ROUTES.items():
        connection.execute(
            text(
                "UPDATE catalog_module_definitions "
                "SET admin_path = :admin_path WHERE key = :module_key"
            ),
            {"admin_path": admin_path, "module_key": module_key},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for module_key in ROUTES:
        connection.execute(
            text(
                "UPDATE catalog_module_definitions "
                "SET admin_path = :admin_path WHERE key = :module_key"
            ),
            {
                "admin_path": f"/admin/catalog-module/{module_key}",
                "module_key": module_key,
            },
        )
