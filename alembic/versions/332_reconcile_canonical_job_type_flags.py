"""Reconcile canonical job-type workflow flags.

Revision ID: 332
Revises: 331
"""
import sqlalchemy as sa
from alembic import op


revision = "332"
down_revision = "331"
branch_labels = None
depends_on = None


_CANONICAL_FLAGS = (
    ("repair", "Repair", True, True, False, 1),
    ("service", "Service", False, False, True, 2),
    ("consultation", "Consultation", True, True, False, 3),
    ("installation", "Installation", False, False, True, 4),
    ("uninstallation", "Uninstallation", False, False, False, 5),
    ("inspection", "Inspection", True, True, False, 6),
    ("maintenance", "Maintenance", False, False, True, 7),
    ("cleaning", "Cleaning", False, False, True, 8),
    ("custom", "Custom", True, True, True, 9),
)


def upgrade() -> None:
    conn = op.get_bind()
    for key, label, assessment, quote, checklist, order in _CANONICAL_FLAGS:
        conn.execute(sa.text("""
            INSERT INTO job_types
                (key, label, requires_assessment, allows_quote,
                 requires_checklist, display_order)
            VALUES
                (:key, :label, :assessment, :quote, :checklist, :display_order)
            ON CONFLICT (key) DO UPDATE SET
                label = EXCLUDED.label,
                requires_assessment = EXCLUDED.requires_assessment,
                allows_quote = EXCLUDED.allows_quote,
                requires_checklist = EXCLUDED.requires_checklist,
                display_order = EXCLUDED.display_order,
                updated_at = now()
        """), {
            "key": key, "label": label, "assessment": assessment,
            "quote": quote, "checklist": checklist, "display_order": order,
        })


def downgrade() -> None:
    # This repairs drift to the long-standing seed contract; there is no
    # reliable tenant-independent previous value to restore.
    pass
