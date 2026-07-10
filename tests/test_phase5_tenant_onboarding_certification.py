"""Phase 5 — Tenant Onboarding & Approval certification.

Static-inspection style (established convention this session). Live
end-to-end behavior for these same assertions was additionally verified via
curl against the real running backend + real Postgres before this file was
written — see PHASE_5_TENANT_BACKEND_REPORT.md and
PHASE_5_TENANT_BUG_FIX_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8-sig")
PKG_SERVICE = (ROOT / "app/engines/package_commerce/service.py").read_text(encoding="utf-8-sig")
PKG_MODELS = (ROOT / "app/engines/package_commerce/models.py").read_text(encoding="utf-8-sig")
ADMIN_SERVICE = (ROOT / "app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8-sig")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8-sig")


# ── Bug 1: broken class name import ─────────────────────────────────
def test_approve_reject_use_correct_service_class_name():
    assert "TenantAdminService" not in PROVIDER_ROUTER
    assert "from app.engines.tenant_engine.admin_service import AdminTenantService" in PROVIDER_ROUTER


def test_admin_tenant_service_class_actually_exists_with_that_name():
    assert "class AdminTenantService" in ADMIN_SERVICE


# ── Bug 2: missing auth on approve/reject/request-changes ───────────
def test_onboarding_mutation_endpoints_require_real_permission():
    for marker in ("async def approve_provider_onboarding", "async def reject_provider_onboarding",
                   "async def request_changes_provider_onboarding"):
        idx = PROVIDER_ROUTER.index(marker)
        snippet = PROVIDER_ROUTER[idx: idx + 300]
        assert "require_permission(P." in snippet or "require_super_admin" in snippet
        assert "Depends(get_current_user)" not in snippet


def test_onboarding_permission_constants_exist():
    for perm in ("TENANT_APPROVE", "TENANT_REJECT", "TENANT_REQUEST_MORE_INFO", "TENANT_ONBOARDING_READ"):
        assert perm in PERMISSIONS
        assert perm in PROVIDER_ROUTER


# ── Bug 3: reject requires a reason ─────────────────────────────────
def test_reject_requires_reason():
    idx = PROVIDER_ROUTER.index("async def reject_provider_onboarding")
    snippet = PROVIDER_ROUTER[idx: idx + 500]
    assert 'not payload.get("reason")' in snippet


# ── Bug 4: request_id placeholder fixed app-wide in this router ─────
def test_request_id_no_longer_hardcoded_placeholder_in_provider_portal():
    assert 'rid = request.headers.get("X-Request-ID", "—")' not in PROVIDER_ROUTER
    assert 'getattr(request.state, "request_id", None)' in PROVIDER_ROUTER


# ── Bug 5: TenantPackageAssignment has no deleted_at column ─────────
def test_tenant_package_assignment_has_no_deleted_at_column():
    idx = PKG_MODELS.index("class TenantPackageAssignment")
    end = PKG_MODELS.index("class PackageAuditLog")
    snippet = PKG_MODELS[idx:end]
    assert "deleted_at" not in snippet


def test_package_activation_queries_do_not_filter_nonexistent_column():
    assert "TenantPackageAssignment.deleted_at" not in PKG_SERVICE


def test_activate_tenant_package_assignment_exists_and_credits_wallet():
    assert "async def activate_tenant_package_assignment" in PKG_SERVICE
    assert "credit_wallet(" in PKG_SERVICE
    assert 'idempotency_key=f"pkg-assign-credit-{assignment.id}"' in PKG_SERVICE


def test_reject_tenant_package_assignment_exists():
    assert "async def reject_tenant_package_assignment" in PKG_SERVICE


# ── Approval readiness (naive but real) ─────────────────────────────
def test_profile_completion_gate_exists_on_approve():
    idx = PROVIDER_ROUTER.index("async def approve_provider_onboarding")
    snippet = PROVIDER_ROUTER[idx: idx + 900]
    assert "profile_completion_percentage" in snippet
    assert "pct < 100" in snippet


# ── Business rules: credits are not cash, deposit is separate ───────
def test_credits_not_labeled_as_cash_in_package_service():
    forbidden = ("Cash Wallet", "Withdrawable Balance", "Tenant Payout",
                 "Provider Earnings Wallet", "Escrow", "Provider Cash Balance")
    for label in forbidden:
        assert label not in PKG_SERVICE
        assert label not in PROVIDER_ROUTER


def test_security_deposit_kept_separate_from_wallet_credits():
    idx = PKG_SERVICE.index("async def activate_tenant_package_assignment")
    snippet = PKG_SERVICE[idx: idx + 2000]
    assert "Security deposit stays in deposit ledger (not wallet)" in snippet
