"""Phase 2 — Catalog + Service Setup Certification Sprint — frontend
static-inspection tests. No JS test runner in this repo; Python
source-inspection tests matching this repo's established convention.

Note: real page paths differ from the ticket's assumed
`/admin/catalog/home-services/*` paths — actual paths are
`/admin/categories`, `/admin/service-groups`, `/admin/master-services`,
`/admin/types-brands`, `/admin/service-setup/issue-types`,
`/admin/service-setup/service-options`, `/admin/service-setup/templates`,
`/admin/service-setup/bulk-wizard`. Documented in
PHASE_2_CATALOG_SERVICE_SETUP_AUDIT.md — not a defect, all pages are real
and wired to live APIs.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend/super-admin"
CATEGORIES = (FE / "app/admin/categories/page.tsx").read_text(encoding="utf-8")
SERVICE_GROUPS = (FE / "app/admin/service-groups/page.tsx").read_text(encoding="utf-8")
MASTER_SERVICES = (FE / "app/admin/master-services/page.tsx").read_text(encoding="utf-8")
TYPES_BRANDS = (FE / "app/admin/types-brands/page.tsx").read_text(encoding="utf-8")
ISSUE_TYPES = (FE / "app/admin/service-setup/issue-types/page.tsx").read_text(encoding="utf-8")
SERVICE_OPTIONS = (FE / "app/admin/service-setup/service-options/page.tsx").read_text(encoding="utf-8")
TEMPLATES = (FE / "app/admin/service-setup/templates/page.tsx").read_text(encoding="utf-8")
BULK_WIZARD = (FE / "app/admin/service-setup/bulk-wizard/page.tsx").read_text(encoding="utf-8")
ADMIN_LAYOUT = (FE / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8")


def test_1_home_services_category_page_renders():
    assert "AdminLayout" in CATEGORIES
    assert len(CATEGORIES) > 500


def test_2_service_groups_page_renders():
    assert "AdminLayout" in SERVICE_GROUPS
    assert len(SERVICE_GROUPS) > 500


def test_3_master_services_page_renders():
    assert "AdminLayout" in MASTER_SERVICES
    assert len(MASTER_SERVICES) > 500


def test_4_types_brands_page_renders_all_four_required_tabs():
    for tab_label in ('"Service Types"', '"Brands"', '"Brand Requests"', '"Brand-Service Mapping"'):
        assert tab_label in TYPES_BRANDS


def test_5_issue_types_page_renders():
    # Sprint 34K: AdminLayout is applied centrally via app/admin/layout.tsx,
    # not imported per-page — real API import is the correct render signal here.
    assert "serviceOptionApi" in ISSUE_TYPES
    assert len(ISSUE_TYPES) > 500


def test_6_service_options_page_renders():
    assert "serviceOptionApi" in SERVICE_OPTIONS
    assert len(SERVICE_OPTIONS) > 500


def test_7_service_setup_templates_page_renders():
    assert "serviceSetupTemplatesApi" in TEMPLATES
    assert len(TEMPLATES) > 500


def test_8_bulk_wizard_page_renders_and_calls_real_api():
    assert "bulkWizardApi" in BULK_WIZARD
    assert "createDraft" in BULK_WIZARD
    assert "validateDraft" in BULK_WIZARD
    assert "dryRun" in BULK_WIZARD
    assert "executeDraft" in BULK_WIZARD


def test_9_sidebar_has_no_duplicate_brands_or_pricing():
    assert ADMIN_LAYOUT.count('label: "Pricing Tiers"') == 1
    assert ADMIN_LAYOUT.count('label: "City/Zip Mapping"') == 1
    assert ADMIN_LAYOUT.count('label: "Pricing Rules"') == 1
    assert 'label: "Brands"' not in ADMIN_LAYOUT
    assert 'label: "Brand Requests"' not in ADMIN_LAYOUT


def test_10_types_brands_page_has_approve_reject_merge_actions():
    assert '"Approve"' in TYPES_BRANDS or ">Approve<" in TYPES_BRANDS
    assert '"Reject"' in TYPES_BRANDS or ">Reject<" in TYPES_BRANDS
    assert "merge" in TYPES_BRANDS.lower()
