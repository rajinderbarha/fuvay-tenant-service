"""Reseed job_types + catalog_dimensions -- another core-seed gap missed by
migration 159's vertical/engine reseed after the manual full-data wipe.

Confirmed empty while validating migration 160's reconciliation logic (its
JOIN against job_types.key silently matched zero rows because the table
itself was empty, not because no legacy data existed). Both tables are
platform seed data (job type taxonomy + the two implicit generic
dimensions), not tenant business data -- reusing the exact seed data
originally written in migrations 151 and 154.

Idempotent (ON CONFLICT DO NOTHING equivalent via existence checks).

Revision ID: 161
Revises: 160
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "161"
down_revision = "160"
branch_labels = None
depends_on = None

# From migration 151.
_SEED_JOB_TYPES = [
    ("repair",         "Repair",         True,  True,  False, 1),
    ("service",        "Service",        False, False, True,  2),
    ("consultation",   "Consultation",   True,  True,  False, 3),
    ("installation",   "Installation",   False, False, True,  4),
    ("uninstallation", "Uninstallation", False, False, False, 5),
    ("inspection",      "Inspection",     True,  True,  False, 6),
    ("maintenance",     "Maintenance",    False, False, True,  7),
    ("cleaning",        "Cleaning",       False, False, True,  8),
    ("custom",          "Custom",         True,  True,  True,  9),
]

# From migration 154.
_SEED_DIMENSIONS = [("type", "Type", 1, "service_types"), ("brand", "Brand", 2, "brands")]


def upgrade() -> None:
    conn = op.get_bind()

    for key, label, req_assess, allows_quote, req_checklist, order in _SEED_JOB_TYPES:
        exists = conn.execute(sa.text("SELECT 1 FROM job_types WHERE key=:k"), {"k": key}).fetchone()
        if exists:
            continue
        conn.execute(sa.text("""
            INSERT INTO job_types (key, label, requires_assessment, allows_quote, requires_checklist, display_order)
            VALUES (:key, :label, :req_assess, :allows_quote, :req_checklist, :order)
        """), {"key": key, "label": label, "req_assess": req_assess,
               "allows_quote": allows_quote, "req_checklist": req_checklist, "order": order})

    for key, name, order, legacy in _SEED_DIMENSIONS:
        exists = conn.execute(sa.text("SELECT 1 FROM catalog_dimensions WHERE key=:k"), {"k": key}).fetchone()
        if exists:
            continue
        conn.execute(sa.text("""
            INSERT INTO catalog_dimensions (key, name, data_type, legacy_source, display_order)
            VALUES (:key, :name, 'single_select', :legacy, :order)
        """), {"key": key, "name": name, "legacy": legacy, "order": order})


def downgrade() -> None:
    # Data-only reseed; not reversible.
    pass
