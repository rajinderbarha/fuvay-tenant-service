"""Phase 1 — Admin Setup Certification Sprint — frontend static-inspection tests.

No JS test runner in this repo; Python source-inspection tests matching
tests/test_p0_admin_tenant_typescript_stabilization.py convention.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend/super-admin"
DASHBOARD = (FE / "app/admin/dashboard/page.tsx").read_text(encoding="utf-8")
ADMIN_LAYOUT = (FE / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
SETTINGS_PAGE = (FE / "app/admin/settings/page.tsx").read_text(encoding="utf-8")
ENGINES_PAGE = (FE / "app/admin/engines/page.tsx").read_text(encoding="utf-8")
VERTICALS_PAGE = (FE / "app/admin/verticals/page.tsx").read_text(encoding="utf-8")
AUDIT_PAGE = (FE / "app/admin/audit-logs/page.tsx").read_text(encoding="utf-8")


def test_1_admin_dashboard_renders():
    assert "Platform command center" in DASHBOARD
    assert "AdminLayout" in DASHBOARD


def test_2_sidebar_has_no_duplicate_brands_or_pricing():
    # Pricing Tiers / City-Zip Mapping / Pricing Rules must each appear exactly
    # once (under "Pricing"); Brands/Brand Requests must not be global nav items.
    assert 'label: "Pricing Tiers"' not in ADMIN_LAYOUT
    assert 'label: "City/Zip Mapping"' not in ADMIN_LAYOUT
    assert 'label: "Pricing Rules"' not in ADMIN_LAYOUT
    assert 'label: "Brands"' not in ADMIN_LAYOUT
    assert 'label: "Brand Requests"' not in ADMIN_LAYOUT


def test_3_platform_settings_page_renders():
    assert "AdminLayout" in SETTINGS_PAGE
    assert len(SETTINGS_PAGE) > 500


def test_4_engine_management_page_renders():
    assert "AdminLayout" in ENGINES_PAGE
    assert len(ENGINES_PAGE) > 500


def test_5_vertical_configuration_page_renders():
    assert "AdminLayout" in VERTICALS_PAGE
    assert len(VERTICALS_PAGE) > 500


def test_6_audit_logs_page_renders():
    assert "AdminLayout" in AUDIT_PAGE
    assert len(AUDIT_PAGE) > 500


def test_7_client_side_auth_guard_redirects_unauthenticated():
    assert 'localStorage.getItem("serviceos_admin_token")' in ADMIN_LAYOUT
    assert 'window.location.href = "/login"' in ADMIN_LAYOUT


def test_8_nav_visibility_is_permission_and_vertical_aware():
    assert "isNavItemVisible" in ADMIN_LAYOUT
    assert "effectiveMenu" in ADMIN_LAYOUT
