"""
FRONTEND-CONNECT-01 — API Client + Auth/Tenant Context Foundation.

No JS test runner is configured in either frontend's package.json (checked:
neither has a `test` script). Following this repo's established convention
(many prior frontend sprints — e.g. test_p0_dashboard_command_center_frontend.py,
test_phase1_admin_setup_certification_frontend.py) this is a Python
source-inspection test suite asserting on the actual .tsx/.ts file content
instead of executing JS.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TENANT = ROOT / "frontend" / "tenant-portal"
ADMIN = ROOT / "frontend" / "super-admin"


def read(p: Path) -> str:
    assert p.exists(), f"missing file: {p}"
    return p.read_text(encoding="utf-8")


def strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//.*", "", src)
    return src


# ── API client sends auth token ──────────────────────────────────────────────
def test_tenant_api_client_attaches_auth_token():
    src = read(TENANT / "lib" / "api.ts")
    assert "Authorization" in src and "Bearer" in src
    assert "getToken" in src


def test_admin_api_client_attaches_auth_token():
    src = read(ADMIN / "lib" / "api.ts")
    assert "Authorization" in src and "Bearer" in src


# ── tenant context included when required ───────────────────────────────────
def test_tenant_context_helpers_exist_and_never_fabricate():
    src = read(TENANT / "lib" / "api-foundation" / "tenant-context.ts")
    assert "getTenantContext" in src
    assert "requireTenantContext" in src
    assert "TenantContextMissingError" in src
    assert "Tenant context missing" in src


def test_tenant_modules_require_tenant_context():
    src = read(TENANT / "lib" / "api-foundation" / "tenant-modules.ts")
    assert "requireTenantContext" in src


# ── request_id parsed from error response ────────────────────────────────────
def test_error_model_parses_request_id_both_frontends():
    for base in (TENANT, ADMIN):
        src = read(base / "lib" / "api-foundation" / "error-model.ts")
        assert "request_id" in src
        assert "ApiError" in src
        assert "toApiError" in src
        assert "parseErrorResponse" in src


def test_error_model_handles_401_403_422_500():
    for base in (TENANT, ADMIN):
        src = read(base / "lib" / "api-foundation" / "error-model.ts")
        assert "401" in src
        assert "403" in src
        assert "422" in src
        assert "500" in src


# ── safe* normalization ──────────────────────────────────────────────────────
def test_safe_helpers_prevent_null_nan_undefined():
    for base in (TENANT, ADMIN):
        src = read(base / "lib" / "api-foundation" / "normalize.ts")
        assert "safeText" in src or "safeText" in read(TENANT / "lib" / "status-format.ts")
        assert "safeNumber" in src or "safeNum" in src
        assert "safeStatus" in src
        assert "safeArray" in src


def test_admin_normalize_defines_safe_number_and_status():
    src = read(ADMIN / "lib" / "api-foundation" / "normalize.ts")
    assert re.search(r"function safeNumber", src)
    assert re.search(r"function safeStatus", src)
    assert "Number.isFinite" in src  # NaN guard


# ── admin/tenant API modules use central client ──────────────────────────────
def test_admin_modules_do_not_use_direct_fetch():
    src = strip_comments(read(ADMIN / "lib" / "api-foundation" / "admin-modules.ts"))
    assert re.search(r"(?<![.\w])fetch\(", src) is None
    assert 'from "../api"' in src


def test_tenant_modules_do_not_use_direct_fetch():
    src = strip_comments(read(TENANT / "lib" / "api-foundation" / "tenant-modules.ts"))
    assert re.search(r"(?<![.\w])fetch\(", src) is None
    assert 'from "../api"' in src


# ── shared UI states ──────────────────────────────────────────────────────────
def test_api_states_component_family_exists_both_frontends():
    for base in (TENANT, ADMIN):
        src = read(base / "components" / "shared" / "ApiStates.tsx")
        for name in [
            "ApiLoadingState", "ApiErrorState", "ApiEmptyState",
            "ApiPermissionDeniedState", "ApiValidationErrorList",
            "RequestIdBadge", "CopyRequestIdButton",
        ]:
            assert f"export function {name}" in src, f"{name} missing in {base}"


# ── smoke pages render loading + error-with-request_id ──────────────────────
def test_tenant_smoke_page_uses_new_error_and_loading_states():
    # NOTE: this page later adopted the richer, per-section
    # TenantStatusSectionError (title/message/requestId/section/onRetry per
    # failing data source, not one generic top-level error) instead of the
    # single-error ApiErrorState/ApiLoadingState pair -- a real design
    # upgrade (see test_tenant_my_status_enterprise_ui.py's
    # test_page_uses_section_error_component_for_each_major_section, which
    # requires >=4 real per-section error states).
    src = read(TENANT / "app" / "(tenant)" / "provider" / "status" / "page.tsx")
    assert "TenantStatusSectionError" in src
    assert "requestId" in src


def test_admin_smoke_page_exists_and_uses_foundation():
    p = ADMIN / "app" / "admin" / "home-services" / "overview" / "page.tsx"
    src = read(p)
    assert "ApiErrorState" in src
    assert "ApiLoadingState" in src
    assert "ApiEmptyState" in src
    assert "getAdminHomeServicesOverview" in src
    assert re.search(r"(?<![.\w])fetch\(", strip_comments(src)) is None


# ── forbidden labels absent from foundation + smoke pages ───────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Credit Wallet Health", "Platform Pay Now", "Online Payment Required",
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
]


def test_no_forbidden_labels_in_foundation_and_smoke_pages():
    files = [
        TENANT / "lib" / "api-foundation" / "error-model.ts",
        TENANT / "lib" / "api-foundation" / "normalize.ts",
        TENANT / "lib" / "api-foundation" / "tenant-context.ts",
        TENANT / "lib" / "api-foundation" / "tenant-modules.ts",
        TENANT / "lib" / "api-foundation" / "home-services-types.ts",
        TENANT / "components" / "shared" / "ApiStates.tsx",
        TENANT / "app" / "(tenant)" / "provider" / "status" / "page.tsx",
        ADMIN / "lib" / "api-foundation" / "error-model.ts",
        ADMIN / "lib" / "api-foundation" / "normalize.ts",
        ADMIN / "lib" / "api-foundation" / "admin-context.ts",
        ADMIN / "lib" / "api-foundation" / "admin-modules.ts",
        ADMIN / "lib" / "api-foundation" / "home-services-types.ts",
        ADMIN / "components" / "shared" / "ApiStates.tsx",
        ADMIN / "app" / "admin" / "home-services" / "overview" / "page.tsx",
    ]
    for f in files:
        src = read(f).lower()
        for label in FORBIDDEN:
            assert label.lower() not in src, f"forbidden label '{label}' found in {f}"


# ── payment model typed correctly (not wallet/payout) ───────────────────────
def test_payment_mode_type_is_direct_not_wallet():
    for base in (TENANT, ADMIN):
        src = read(base / "lib" / "api-foundation" / "home-services-types.ts")
        assert 'customer_pays_provider_directly' in src
        assert "PaymentMode" in src
        assert "CustomerPriceOptions" in src
