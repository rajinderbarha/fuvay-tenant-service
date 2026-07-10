"""Phase 2 catalog certification — fix checklist_templates module admin_path.

Migration 089 seeded catalog_module_definitions.checklist_templates with
admin_path='/admin/checklist-templates', pointing at a legacy, unstyled,
tenant-scoped page (app/engines/field_ops ServiceChecklistTemplate UI) that
was never wired to the Phase 2 master/admin-catalog checklist system
(master_checklist_items, migration 109). This left the sidebar's dynamic
per-vertical "Checklists" link (rendered via
GET /v1/admin/catalog/navigation/effective-menu) pointing at the wrong,
visually-broken page. Repoints it at the new enterprise page.

Revision ID: 110
Revises: 109
"""
from alembic import op
from sqlalchemy import text

revision = "110"
down_revision = "109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE catalog_module_definitions
        SET admin_path = '/admin/checklists'
        WHERE key = 'checklist_templates'
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE catalog_module_definitions
        SET admin_path = '/admin/checklist-templates'
        WHERE key = 'checklist_templates'
    """))
