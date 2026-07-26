"""Reseed Home Services' bespoke catalog modules (Overview, Service Catalog,
Provider Matching, Matching Diagnostics, Completed Job Deduction, Settings,
Provider Bookability).

USER REQ: "we made [updated] service catalog page recently... its not
showing in the home service menu."

Root cause: per frontend/super-admin/components/layout/AdminLayout.tsx's
own comments, these 7 pages were migrated from a hardcoded
`vertical_key === "home_services"` menu escape hatch to real, backend-
registered `catalog_module_definitions` + `vertical_catalog_modules` rows
(module keys hs_overview / hs_service_catalog / hs_provider_matching /
hs_matching_diagnostics / hs_completed_job_deduction / hs_settings /
hs_bookability) -- but that registration was done via the live admin API
at the time, NOT captured in any alembic migration. The full-data-wipe task
erased them with no migration able to reconstruct them (unlike migration
159/161's reseeds, which could replay original migration seed data -- this
data never existed in a migration to replay).

Reconstructed here from AdminLayout.tsx's HOME_SERVICES_EXTRA_ITEMS array
(the same source of truth the frontend itself documents), which is the
current, real route/label/permission set for these pages.

Revision ID: 165
Revises: 164
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "165"
down_revision = "164"
branch_labels = None
depends_on = None

# key, label, icon, admin_path, sort_order
_MODULES = [
    ("hs_overview", "Overview", "LayoutGrid", "/admin/home-services/overview", 20),
    ("hs_service_catalog", "Service Catalog", "ListChecks", "/admin/catalog-workspace", 21),
    ("hs_provider_matching", "Provider Matching", "Zap", "/admin/home-services/provider-matching", 22),
    ("hs_matching_diagnostics", "Matching Diagnostics", "Wrench", "/admin/home-services/matching-diagnostics", 23),
    ("hs_completed_job_deduction", "Completed Job Deduction", "PercentSquare", "/admin/home-services/completed-job-deduction", 24),
    ("hs_settings", "Home Services Settings", "Settings", "/admin/home-services/settings", 25),
    ("hs_bookability", "Provider Bookability", "Zap", "/admin/bookability/providers", 26),
]


def upgrade() -> None:
    conn = op.get_bind()

    vertical_id = conn.execute(sa.text(
        "SELECT id FROM verticals WHERE key = 'home_services'")).scalar()
    if not vertical_id:
        print("[165] home_services vertical not found -- skipping (nothing to attach these modules to)")
        return

    for key, label, icon, path, sort_order in _MODULES:
        existing = conn.execute(sa.text(
            "SELECT id FROM catalog_module_definitions WHERE key = :key"), {"key": key}).fetchone()
        if existing:
            module_id = str(existing[0])
        else:
            module_id = str(uuid.uuid4())
            conn.execute(sa.text("""
                INSERT INTO catalog_module_definitions
                    (id, key, label, icon, admin_path, module_group, is_universal, sort_order)
                VALUES (:id, :key, :label, :icon, :path, 'operations', false, :sort)
            """), {"id": module_id, "key": key, "label": label, "icon": icon,
                   "path": path, "sort": sort_order})

        conn.execute(sa.text("""
            INSERT INTO vertical_catalog_modules (id, vertical_id, module_id, is_enabled, is_required, sort_order)
            VALUES (:id, :vid, :mid, true, false, :sort)
            ON CONFLICT (vertical_id, module_id) DO UPDATE SET is_enabled = true
        """), {"id": str(uuid.uuid4()), "vid": str(vertical_id), "mid": module_id, "sort": sort_order})

    print(f"[165] reseeded {len(_MODULES)} Home Services bespoke modules")


def downgrade() -> None:
    conn = op.get_bind()
    keys = [m[0] for m in _MODULES]
    conn.execute(sa.text("""
        DELETE FROM vertical_catalog_modules WHERE module_id IN
            (SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys))
    """), {"keys": keys})
    conn.execute(sa.text("DELETE FROM catalog_module_definitions WHERE key = ANY(:keys)"), {"keys": keys})
