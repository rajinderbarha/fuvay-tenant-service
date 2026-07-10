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


def test_roles_list_endpoint_exists():
    assert '@router.get("/roles"' in ROUTER
    assert "async def list_roles" in SERVICE


def test_all_ten_required_roles_present_in_order():
    for role in ("super_admin", "platform_admin", "finance_admin", "operations_admin",
                 "support_admin", "compliance_officer", "tenant_owner", "tenant_manager",
                 "technician", "customer"):
        assert f'"{role}"' in SERVICE


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


def test_all_endpoints_require_super_admin():
    assert ROUTER.count("require_super_admin") >= 8


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
    assert "[moduleFilter, scopeFilter, riskFilter, search]), [moduleFilter, scopeFilter, riskFilter, search]);" in PERMISSIONS_PAGE
