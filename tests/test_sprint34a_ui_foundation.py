"""
Sprint 34A — UI Simplification Foundation tests.
Verifies layout primitives, config files, nav simplification, and page updates
without running a browser. All checks are static file inspection.
"""
import os
import re

ROOT      = os.path.dirname(os.path.dirname(__file__))
SA_COMP   = os.path.join(ROOT, "frontend", "super-admin", "components", "shared")
TP_COMP   = os.path.join(ROOT, "frontend", "tenant-portal", "components", "shared")
SA_LIB    = os.path.join(ROOT, "frontend", "super-admin", "lib")
TP_LIB    = os.path.join(ROOT, "frontend", "tenant-portal", "lib")
SA_PAGES  = os.path.join(ROOT, "frontend", "super-admin", "app", "admin")
TP_PAGES  = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)")
SA_LAYOUT = os.path.join(ROOT, "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")
TP_LAYOUT = os.path.join(ROOT, "frontend", "tenant-portal", "components", "layout", "TenantLayout.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Phase 2: Layout primitives ─────────────────────────────────────────────────

def test_layout_file_exists_super_admin():
    assert os.path.exists(os.path.join(SA_COMP, "layout.tsx"))


def test_layout_file_exists_tenant_portal():
    assert os.path.exists(os.path.join(TP_COMP, "layout.tsx"))


def test_layout_exports_page_shell():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function PageShell" in src


def test_layout_exports_page_header():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function PageHeader" in src


def test_layout_exports_search_bar():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function SearchBar" in src


def test_layout_exports_action_menu():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function ActionMenu" in src


def test_layout_exports_summary_strip():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function SummaryStrip" in src


def test_layout_exports_detail_tabs():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function DetailTabs" in src


def test_layout_exports_form_section():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function FormSection" in src


def test_layout_exports_danger_zone():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function DangerZone" in src


def test_layout_exports_entity_header():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function EntityHeader" in src


def test_layout_exports_error_state():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "export function ErrorState" in src


def test_layout_no_classname():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    # Should not have className= assignments (inline styles only)
    assert "className=" not in src


def test_tp_layout_no_classname():
    src = _read(os.path.join(TP_COMP, "layout.tsx"))
    assert "className=" not in src


def test_layout_uses_css_tokens():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "var(--" in src


def test_action_menu_closes_on_outside_click():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "useRef" in src or "addEventListener" in src


def test_action_menu_aria_attributes():
    src = _read(os.path.join(SA_COMP, "layout.tsx"))
    assert "aria-expanded" in src or "aria-haspopup" in src


# ── Phase 11: Config files ─────────────────────────────────────────────────────

def test_status_labels_file_exists_sa():
    assert os.path.exists(os.path.join(SA_LIB, "status-labels.ts"))


def test_status_labels_file_exists_tp():
    assert os.path.exists(os.path.join(TP_LIB, "status-labels.ts"))


def test_status_labels_exports_account_status():
    src = _read(os.path.join(SA_LIB, "status-labels.ts"))
    assert "ACCOUNT_STATUS" in src


def test_status_labels_exports_job_status():
    src = _read(os.path.join(SA_LIB, "status-labels.ts"))
    assert "JOB_STATUS" in src


def test_status_labels_exports_get_status():
    src = _read(os.path.join(SA_LIB, "status-labels.ts"))
    assert "getStatus" in src or "export function getStatus" in src


def test_field_labels_file_exists_sa():
    assert os.path.exists(os.path.join(SA_LIB, "field-labels.ts"))


def test_field_labels_exports_field_label_fn():
    src = _read(os.path.join(SA_LIB, "field-labels.ts"))
    assert "fieldLabel" in src or "FIELD_LABELS" in src


def test_page_copy_config_exists_sa():
    assert os.path.exists(os.path.join(SA_LIB, "page-copy.config.ts"))


def test_page_copy_config_exists_tp():
    assert os.path.exists(os.path.join(TP_LIB, "page-copy.config.ts"))


def test_page_copy_has_admin_section():
    src = _read(os.path.join(SA_LIB, "page-copy.config.ts"))
    assert "admin:" in src or '"admin"' in src


def test_page_copy_has_provider_section():
    src = _read(os.path.join(SA_LIB, "page-copy.config.ts"))
    assert "provider:" in src or '"provider"' in src


def test_page_copy_exports_get_page_copy():
    src = _read(os.path.join(SA_LIB, "page-copy.config.ts"))
    assert "getPageCopy" in src


# ── Phase 3/8: ui.tsx JobStatusBadge fix ──────────────────────────────────────

def test_job_status_badge_no_hardcoded_hex_sa():
    src = _read(os.path.join(SA_COMP, "ui.tsx"))
    # No hardcoded hex colors in JOB_COLORS or similar
    # After the fix these should reference var(--) tokens
    assert "#EFF6FF" not in src or "JOB_COLORS" not in src


def test_job_status_badge_no_hardcoded_hex_tp():
    src = _read(os.path.join(TP_COMP, "ui.tsx"))
    assert "#EFF6FF" not in src or "JOB_COLORS" not in src


def test_job_status_badge_uses_tokens_sa():
    src = _read(os.path.join(SA_COMP, "ui.tsx"))
    assert "var(--success-bg)" in src


def test_job_status_badge_uses_tokens_tp():
    src = _read(os.path.join(TP_COMP, "ui.tsx"))
    assert "var(--success-bg)" in src


# ── Phase 14: Admin dashboard ──────────────────────────────────────────────────

def test_admin_dashboard_uses_page_header():
    src = _read(os.path.join(SA_PAGES, "dashboard", "page.tsx"))
    assert "PageHeader" in src


def test_admin_dashboard_uses_page_shell():
    src = _read(os.path.join(SA_PAGES, "dashboard", "page.tsx"))
    assert "PageShell" in src


def test_admin_dashboard_uses_summary_strip():
    src = _read(os.path.join(SA_PAGES, "dashboard", "page.tsx"))
    assert "SummaryStrip" in src


def test_admin_dashboard_no_hero_gradient():
    src = _read(os.path.join(SA_PAGES, "dashboard", "page.tsx"))
    # The hero gradient banner was replaced by PageHeader
    assert "linear-gradient(135deg" not in src


def test_admin_dashboard_imports_layout():
    src = _read(os.path.join(SA_PAGES, "dashboard", "page.tsx"))
    assert 'from "../../../components/shared/layout"' in src


# ── Phase 14: Admin users page ────────────────────────────────────────────────

def test_admin_users_uses_page_header():
    src = _read(os.path.join(SA_PAGES, "users", "page.tsx"))
    assert "PageHeader" in src


def test_admin_users_uses_page_shell():
    src = _read(os.path.join(SA_PAGES, "users", "page.tsx"))
    assert "PageShell" in src


def test_admin_users_uses_search_bar():
    src = _read(os.path.join(SA_PAGES, "users", "page.tsx"))
    assert "SearchBar" in src


def test_admin_users_uses_action_menu():
    src = _read(os.path.join(SA_PAGES, "users", "page.tsx"))
    assert "ActionMenu" in src


def test_admin_users_no_section_header():
    src = _read(os.path.join(SA_PAGES, "users", "page.tsx"))
    assert "SectionHeader" not in src


# ── Phase 14: Admin settings page ─────────────────────────────────────────────

def test_admin_settings_uses_section_header():
    # Superseded by the P0 Platform Settings Enterprise Upgrade: the page was
    # rewritten into the 7-tab enterprise shell (matching the Security SOC /
    # Customers pattern), which uses SectionHeader + a custom tab bar instead of
    # the older PageHeader/DetailTabs primitives.
    src = _read(os.path.join(SA_PAGES, "settings", "page.tsx"))
    assert "SectionHeader" in src


def test_admin_settings_uses_tab_shell():
    src = _read(os.path.join(SA_PAGES, "settings", "page.tsx"))
    assert "TABS" in src
    assert "Global Settings" in src


def test_admin_settings_has_seed_defaults_action():
    src = _read(os.path.join(SA_PAGES, "settings", "page.tsx"))
    assert "Seed Defaults" in src


# ── Phase 14: Tenant dashboard ────────────────────────────────────────────────

def test_tenant_dashboard_uses_page_header():
    src = _read(os.path.join(TP_PAGES, "dashboard", "page.tsx"))
    assert "PageHeader" in src


def test_tenant_dashboard_uses_page_shell():
    src = _read(os.path.join(TP_PAGES, "dashboard", "page.tsx"))
    assert "PageShell" in src


def test_tenant_dashboard_uses_summary_strip():
    src = _read(os.path.join(TP_PAGES, "dashboard", "page.tsx"))
    assert "SummaryStrip" in src


def test_tenant_dashboard_no_hero_gradient():
    src = _read(os.path.join(TP_PAGES, "dashboard", "page.tsx"))
    # The gradient hero banner was replaced by PageHeader + SummaryStrip
    assert "linear-gradient(135deg" not in src


def test_tenant_dashboard_imports_layout():
    src = _read(os.path.join(TP_PAGES, "dashboard", "page.tsx"))
    assert 'from "../../../components/shared/layout"' in src


# ── Phase 14: Tenant staff page ───────────────────────────────────────────────

def test_tenant_staff_uses_page_header():
    src = _read(os.path.join(TP_PAGES, "staff", "page.tsx"))
    assert "PageHeader" in src


def test_tenant_staff_uses_page_shell():
    src = _read(os.path.join(TP_PAGES, "staff", "page.tsx"))
    assert "PageShell" in src


def test_tenant_staff_uses_search_bar():
    src = _read(os.path.join(TP_PAGES, "staff", "page.tsx"))
    assert "SearchBar" in src


def test_tenant_staff_no_section_header():
    src = _read(os.path.join(TP_PAGES, "staff", "page.tsx"))
    assert "SectionHeader" not in src


def test_tenant_staff_has_search_state():
    src = _read(os.path.join(TP_PAGES, "staff", "page.tsx"))
    assert "search" in src and "setSearch" in src


# ── Phase 10: Navigation simplification ───────────────────────────────────────

def test_admin_layout_no_profile_in_sidebar():
    src = _read(SA_LAYOUT)
    # "My Profile" should not appear in the NAV_GROUPS sidebar definition
    # (it is accessible from the top nav avatar)
    nav_section = src[:src.index("export function AdminLayout")]
    assert "My Profile" not in nav_section


def test_admin_layout_has_analytics_nav():
    src = _read(SA_LAYOUT)
    nav_section = src[:src.index("export function AdminLayout")]
    assert "analytics" in nav_section.lower() or "Analytics" in nav_section


def test_admin_layout_has_media_nav():
    src = _read(SA_LAYOUT)
    nav_section = src[:src.index("export function AdminLayout")]
    assert "media" in nav_section.lower() or "Media" in nav_section


def test_tenant_layout_no_profile_in_sidebar_settings():
    src = _read(TP_LAYOUT)
    # Settings group should not include "My Profile" (redundant with top nav)
    settings_match = re.search(r'label:\s*"Settings".*?}]', src, re.DOTALL)
    if settings_match:
        assert "My Profile" not in settings_match.group()


def test_tenant_layout_has_dashboard_in_fallback():
    src = _read(TP_LAYOUT)
    assert "/dashboard" in src


# ── No className rule ──────────────────────────────────────────────────────────

def test_admin_dashboard_no_classname():
    src = _read(os.path.join(SA_PAGES, "dashboard", "page.tsx"))
    assert "className=" not in src


def test_admin_users_no_classname():
    src = _read(os.path.join(SA_PAGES, "users", "page.tsx"))
    assert "className=" not in src


def test_tenant_dashboard_no_classname():
    src = _read(os.path.join(TP_PAGES, "dashboard", "page.tsx"))
    assert "className=" not in src


def test_tenant_staff_no_classname():
    src = _read(os.path.join(TP_PAGES, "staff", "page.tsx"))
    assert "className=" not in src
