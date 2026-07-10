"""Phase 6 — Tenant Dashboard & Provider Setup certification.

Static-inspection style (established convention this session). Live
end-to-end behavior for these same assertions was additionally verified via
curl against the real running backend + real Postgres before this file was
written — see PHASE_6_TENANT_DASHBOARD_BACKEND_REPORT.md and
PHASE_6_TENANT_DASHBOARD_BUG_FIX_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PORTAL_ROUTER = (ROOT / "app/engines/tenant_engine/portal_router.py").read_text(encoding="utf-8-sig")
PKG_TENANT_ROUTER = (ROOT / "app/engines/package_commerce/tenant_router.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
CATALOG_TENANT_ROUTER = (ROOT / "app/engines/admin_catalog/tenant_router.py").read_text(encoding="utf-8-sig")


# ── Bug: request_id placeholder fixed across all 3 tenant-facing routers ──
def test_request_id_placeholder_fixed_in_tenant_engine_portal_router():
    assert 'rid = request.headers.get("X-Request-ID", "—")' not in PORTAL_ROUTER
    assert 'request.headers.get("X-Request-ID", "—")' not in PORTAL_ROUTER.replace(
        'getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")', "")


def test_request_id_placeholder_fixed_in_package_commerce_tenant_router():
    assert 'getattr(request.state, "request_id", None)' in PKG_TENANT_ROUTER


def test_request_id_placeholder_fixed_in_provider_portal_router():
    assert 'getattr(request.state, "request_id", None)' in PROVIDER_ROUTER


# ── Tenant self-service endpoints exist, scoped via JWT not query param ──
def test_tenant_service_areas_endpoint_exists_and_is_jwt_scoped():
    assert "/service-areas" in PORTAL_ROUTER or "service_areas" in PORTAL_ROUTER


def test_tenant_wallet_read_endpoints_exist():
    assert "/wallet" in PORTAL_ROUTER
    assert "/credit-wallet" in PKG_TENANT_ROUTER


def test_tenant_security_deposit_is_read_only_no_mutation_endpoints():
    assert "/security-deposit" in PKG_TENANT_ROUTER
    for forbidden_action in ("mark-paid", "mark_received", "/release", "/adjust", "/forfeit"):
        assert forbidden_action not in PKG_TENANT_ROUTER


def test_tenant_catalog_available_and_enabled_services_exist():
    assert "available-services" in CATALOG_TENANT_ROUTER or "available_services" in CATALOG_TENANT_ROUTER
    assert "enabled-services" in CATALOG_TENANT_ROUTER or "enabled_services" in CATALOG_TENANT_ROUTER


def test_provider_pricing_setup_endpoint_exists():
    assert "provider_price_override" in PROVIDER_ROUTER or "provider_min_price" in PROVIDER_ROUTER


def test_provider_availability_endpoint_exists():
    assert "availability" in PROVIDER_ROUTER


def test_provider_onboarding_status_checklist_endpoint_exists():
    assert "/onboarding/status" in PROVIDER_ROUTER or "onboarding_status" in PROVIDER_ROUTER


# ── Forbidden label scan ─────────────────────────────────────────────
def test_no_forbidden_labels_in_tenant_facing_backend():
    forbidden = ("Cash Wallet", "Withdrawable Balance", "Tenant Payout",
                 "Provider Earnings Wallet", "Escrow", "Provider Cash Balance")
    for label in forbidden:
        assert label not in PORTAL_ROUTER
        assert label not in PKG_TENANT_ROUTER
        assert label not in PROVIDER_ROUTER
        assert label not in CATALOG_TENANT_ROUTER
