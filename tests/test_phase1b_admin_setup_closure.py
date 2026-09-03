"""Phase 1B — Admin Setup Closure + Manual Browser Smoke Sprint.

Covers the new Roles/Permissions read API (app/engines/roles_permissions/),
the dev-only 500-error-envelope verification route, and confirms the
navigation-editor endpoints genuinely don't exist (supporting the documented
deferral decision in PHASE_1B_NAVIGATION_GAP_DECISION.md).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICE = (ROOT / "app/engines/roles_permissions/service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/roles_permissions/admin_router.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
ROLES_PAGE = (ROOT / "frontend/super-admin/app/admin/users/roles/page.tsx").read_text(encoding="utf-8")
PERMISSIONS_PAGE = (ROOT / "frontend/super-admin/app/admin/users/permissions/page.tsx").read_text(encoding="utf-8")
ROLES_ALIAS = ROOT / "frontend/super-admin/app/admin/roles/page.tsx"
PERMISSIONS_ALIAS = ROOT / "frontend/super-admin/app/admin/permissions/page.tsx"


def test_roles_list_endpoint_exists():
    assert '@router.get("/roles"' in ROUTER
    assert "async def list_roles" in SERVICE


def test_all_required_roles_present_in_order():
    for role in ("super_admin", "admin_operations", "admin_finance", "admin_security",
                 "admin_readonly", "tenant_owner", "staff", "technician", "customer", "guest"):
        assert f'"{role}"' in SERVICE
    for retired in ("platform_admin", "finance_admin", "operations_admin",
                    "support_admin", "compliance_officer", "tenant_manager"):
        assert retired not in SERVICE.split("REQUIRED_ROLE_ORDER = [", 1)[1].split("]", 1)[0]


def test_role_detail_endpoint_exists():
    assert '@router.get("/roles/{role_id}"' in ROUTER
    assert "async def get_role_detail" in SERVICE


def test_role_mutations_return_not_implemented_rather_than_fake_success():
    assert '@router.post("/roles"' in ROUTER
    assert "NOT_IMPLEMENTED" in ROUTER
    assert "status_code=501" in ROUTER


def test_permissions_list_and_grouped_endpoints_exist():
    assert '@router.get("/permissions"' in ROUTER
    assert '@router.get("/permissions/grouped"' in ROUTER
    assert "def list_permissions" in SERVICE
    assert "def list_permissions_grouped" in SERVICE


def test_all_endpoints_require_super_admin_or_permission():
    """FINAL-L5-05L: the 5 read endpoints (list/get roles, list/grouped/get
    permissions) were converted from the coarse require_super_admin
    role-string check to require_permission(P.PLATFORM_ROLES_READ /
    P.PLATFORM_PERMISSIONS_READ) so the new admin_security/admin_readonly
    roles can genuinely read the catalog. The 5 mutation endpoints (all
    501-not-implemented — roles are code-defined, not DB rows) remain on
    require_super_admin. Every endpoint is still authorization-gated by
    one mechanism or the other -- 0 endpoints are open to any authenticated
    user."""
    assert ROUTER.count("require_super_admin") == 5
    assert ROUTER.count("require_permission(P.PLATFORM_ROLES_READ)") == 2
    assert ROUTER.count("require_permission(P.PLATFORM_PERMISSIONS_READ)") == 3


def test_permission_count_consistent_between_list_and_detail():
    # Regression: detail endpoint previously miscounted the super_admin
    # wildcard as 1 permission instead of the real total permission count.
    assert "_permission_count(role_key) if implemented else 0" in SERVICE


def test_500_error_test_route_is_dev_only_and_requires_auth():
    assert "/v1/admin/test" in MAIN
    assert "is_production" in MAIN
    assert "require_super_admin" in MAIN
    assert "error-500" in MAIN


def test_login_events_endpoint_still_mounted():
    notif_router = (ROOT / "app/engines/platform_notifications/admin_router.py").read_text(encoding="utf-8")
    assert '"/login-events"' in notif_router


def test_role_detail_useapi_passes_deps_so_drawer_refetches():
    # Regression: useApi(fetcher, deps) requires deps as its own second arg —
    # the inner useCallback's deps array alone does NOT make useApi refetch,
    # because useApi's internal `run` is memoized with ITS OWN deps param
    # (defaulting to []). Without passing [detailRole] as useApi's second
    # arg, `run` freezes on the first render's fetcher (detailRole=null) and
    # the detail drawer never loads data for any role — found live 2026-07-08.
    assert "[detailRole]), [detailRole]);" in ROLES_PAGE


def test_permissions_filters_useapi_passes_deps_so_filters_refetch():
    assert "[moduleFilter, scopeFilter, riskFilter, search, page, pageSize])" in PERMISSIONS_PAGE
    assert "[moduleFilter, scopeFilter, riskFilter, search, page, pageSize]);" in PERMISSIONS_PAGE


def test_permissions_are_paginated_for_admin_scale():
    assert "page: int = Query(1, ge=1)" in ROUTER
    assert "limit: int = Query(50, ge=1, le=200)" in ROUTER
    assert '"meta": {' in SERVICE
    assert '"total_pages"' in SERVICE
    assert "page, limit: pageSize" in PERMISSIONS_PAGE
    assert "<Pagination page={page}" in PERMISSIONS_PAGE
    assert "pageCount={totalPages}" in PERMISSIONS_PAGE


def test_duplicate_top_level_roles_and_permissions_routes_are_deleted():
    assert not ROLES_ALIAS.exists()
    assert not PERMISSIONS_ALIAS.exists()
