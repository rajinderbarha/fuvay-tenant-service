"""Dashboard drill-downs must match the tenant operations workspace contract."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = (
    ROOT / "frontend/tenant-portal/app/(tenant)/dashboard/page.tsx"
).read_text(encoding="utf-8")
DASHBOARD_SERVICE = (
    ROOT / "app/engines/execution/home_services_dashboard_service.py"
).read_text(encoding="utf-8")
ADMIN_REGISTRY = (
    ROOT / "frontend/super-admin/lib/page-registry.ts"
).read_text(encoding="utf-8")
TENANT_REGISTRY = (
    ROOT / "frontend/tenant-portal/lib/page-registry.ts"
).read_text(encoding="utf-8")
ADMIN_LAYOUT_PATH = ROOT / "frontend/super-admin/components/layout/AdminLayout.tsx"
TENANT_LAYOUT_PATH = ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx"


def _sidebar_hrefs(layout_path: Path) -> set[str]:
    source = layout_path.read_text(encoding="utf-8")
    return {
        match.group(1)
        for match in re.finditer(r'href:\s*"([^"?#]+)"', source)
        if match.group(1).startswith("/")
    }


def _page_route_patterns(app_root: Path) -> list[tuple[str, ...]]:
    patterns: list[tuple[str, ...]] = []
    for page in app_root.rglob("page.tsx"):
        parts = page.parent.relative_to(app_root).parts
        patterns.append(tuple(part for part in parts if not part.startswith("(")))
    return patterns


def _route_matches(pattern: tuple[str, ...], route: tuple[str, ...]) -> bool:
    if not pattern:
        return not route
    segment = pattern[0]
    if segment.startswith("[[..."):
        return True
    if segment.startswith("[..."):
        return bool(route)
    if not route:
        return False
    if segment.startswith("[") or segment == route[0]:
        return _route_matches(pattern[1:], route[1:])
    return False


def _missing_sidebar_pages(layout_path: Path, app_root: Path) -> list[str]:
    patterns = _page_route_patterns(app_root)
    missing: list[str] = []
    for href in sorted(_sidebar_hrefs(layout_path)):
        route = tuple(part for part in href.strip("/").split("/") if part)
        if not any(_route_matches(pattern, route) for pattern in patterns):
            missing.append(href)
    return missing


def test_dashboard_job_links_use_the_detail_drawer_parameter():
    assert "bookings-jobs?job_id=${job.job_id}" in DASHBOARD_PAGE
    assert "bookings-jobs?job_id=${event.job_id}" in DASHBOARD_PAGE
    assert "bookings-jobs?job_id=${jobId}" in DASHBOARD_PAGE
    assert "bookings-jobs?job=" not in DASHBOARD_PAGE


def test_attention_links_use_supported_bookings_filters():
    assert "bookings-jobs?stage=new&assignment=unassigned" in DASHBOARD_SERVICE
    assert "bookings-jobs?stage=estimate_approval" in DASHBOARD_SERVICE
    assert "bookings-jobs?status=" not in DASHBOARD_SERVICE


def test_admin_tenants_has_registered_breadcrumb_metadata():
    assert '"/admin/tenants": {' in ADMIN_REGISTRY
    assert 'breadcrumbs: [{ label: "Tenants" }]' in ADMIN_REGISTRY


def test_dashboard_capacity_metric_distinguishes_ready_from_available():
    assert 'label="Available now"' in DASHBOARD_PAGE
    assert "data.staff_capacity.assigned_now" in DASHBOARD_PAGE
    assert 'label="Available technicians"' not in DASHBOARD_PAGE


def test_every_rendered_tenant_sidebar_destination_has_page_metadata():
    routes = [
        "/dashboard", "/profile", "/business/coverage-hours",
        "/business/verification-documents", "/provider/compliance",
        "/home-services/bookings-jobs", "/home-services/dispatch",
        "/appointments", "/home-services/availability",
        "/home-services/services", "/inventory", "/home-services/team",
        "/customers", "/home-services/reviews", "/home-services/complaints",
        "/provider/refund-requests", "/marketing", "/home-services/finance",
        "/home-services/direct-payments", "/media", "/reports",
        "/activity", "/settings", "/help-support",
    ]
    for route in routes:
        assert f'"{route}": {{' in TENANT_REGISTRY, route


def test_every_rendered_admin_sidebar_destination_has_page_metadata():
    routes = [
        "/admin/dashboard", "/admin/customers", "/admin/staff",
        "/admin/verticals",
        "/admin/categories", "/admin/marketing", "/admin/marketing/home",
        "/admin/notifications", "/admin/analytics", "/admin/intelligence",
        "/admin/engines", "/admin/security", "/admin/compliance",
        "/admin/trust-quality", "/admin/audit-logs", "/admin/users",
        "/admin/media",
        "/admin/settings", "/admin/home-services/dashboard",
        "/admin/catalog-workspace", "/admin/home-services/settings",
        "/admin/bookability/providers", "/admin/home-services/providers",
        "/admin/home-services/bookings-jobs", "/admin/home-services/finance",
    ]
    for route in routes:
        assert f'"{route}": {{' in ADMIN_REGISTRY, route


def test_home_services_breadcrumbs_do_not_link_to_deleted_landing_page():
    assert 'href: "/admin/home-services"' not in ADMIN_REGISTRY


def test_every_admin_sidebar_destination_resolves_to_a_next_page():
    app_root = ROOT / "frontend/super-admin/app"
    assert _missing_sidebar_pages(ADMIN_LAYOUT_PATH, app_root) == []


def test_every_tenant_sidebar_destination_resolves_to_a_next_page():
    app_root = ROOT / "frontend/tenant-portal/app"
    assert _missing_sidebar_pages(TENANT_LAYOUT_PATH, app_root) == []
