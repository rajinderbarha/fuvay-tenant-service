"""
P0 Enterprise Provider / Tenant 360 Detail Page Upgrade — backend + frontend tests.

Scope: this sprint reuses the large amount of existing tenant-detail infrastructure
(staff/users/service-areas/enabled-services/pricing/jobs/bookings/media/reviews/audit
all already had working endpoints) and adds:
  - reason-required guard on tenant reinstate
  - new frontend tabs wired to already-existing tenant-scoped finance endpoints
    (dispute settlements, tenant penalties) — no new backend needed there
  - Usage Credit / Security Deposit language correction (not real money)
  - Provider Readiness checklist computed client-side from already-loaded data
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


ROUTER  = ROOT / "app" / "engines" / "tenant_engine" / "router.py"
SERVICE = ROOT / "app" / "engines" / "tenant_engine" / "service.py"
API_TS  = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
PAGE    = ROOT / "frontend" / "super-admin" / "app" / "admin" / "tenants" / "[id]" / "page.tsx"


# ════════════════════════════════════════════════════════════════════════════
# Backend — reason requirement + real bug fixes
# ════════════════════════════════════════════════════════════════════════════
class TestReinstateReasonRequired:
    def test_router_requires_reason(self):
        src = _read(ROUTER)
        start = src.index("async def reinstate_tenant")
        end = src.index("async def begin_termination")
        section = src[start:end]
        assert "reason" in section
        assert "VALIDATION_ERROR" in section
        assert 'if not reason' in section

    def test_service_signature_uses_reason(self):
        src = _read(SERVICE)
        assert "async def reinstate_tenant(self, tenant_id: uuid.UUID, reason: str)" in src


class TestTenantLifecycleClient:
    """Tenant lifecycle actions keep their required audit reason."""
    def test_reinstate_requires_reason_param(self):
        src = _read(API_TS)
        start = src.index("reinstate:")
        section = src[start:start + 200]
        assert "reason: string" in section


# ════════════════════════════════════════════════════════════════════════════
# Backend router import sanity
# ════════════════════════════════════════════════════════════════════════════
class TestRouterImports:
    def test_router_file_exists(self):
        assert ROUTER.exists()

    def test_service_os_exception_imported(self):
        assert "from app.exceptions import ServiceOSException" in _read(ROUTER)


# ════════════════════════════════════════════════════════════════════════════
# Frontend — new tabs + labeling
# ════════════════════════════════════════════════════════════════════════════
class TestFrontendLabeling:
    def test_page_exists(self):
        assert PAGE.exists()

    def test_no_wallet_cash_language(self):
        src = _read(PAGE)
        assert "Wallet Balance" not in src
        assert "Wallet / Ledger" not in src

    def test_usage_credit_language_present(self):
        src = _read(PAGE)
        assert "Usage Credit Balance" in src
        assert "Usage Credit Ledger" in src

    def test_not_real_money_note_present(self):
        src = _read(PAGE)
        assert "not withdrawable" in src
        assert "not a payout balance" in src

    def test_security_deposit_is_separate_tab(self):
        src = _read(PAGE)
        assert '"deposit"' in src
        assert "Security Deposit Held" in src

    def test_complaints_disputes_tab_exists(self):
        src = _read(PAGE)
        assert '"disputes"' in src
        assert "Complaints & Disputes" in src

    def test_customer_credit_settlements_tab_exists(self):
        src = _read(PAGE)
        assert '"settlements"' in src
        assert "Customer Credit Settlements" in src

    def test_settlement_deduction_language_correct(self):
        src = _read(PAGE)
        assert "sourced from this" in src or "usage credits first" in src

    def test_risk_health_tab_exists(self):
        src = _read(PAGE)
        assert '"risk-health"' in src
        assert "Health Factors" in src

    def test_readiness_panel_exists(self):
        src = _read(PAGE)
        assert "Provider Readiness" in src

    def test_readiness_output_states(self):
        src = _read(PAGE)
        for state in ['"Ready"', '"Needs Setup"', '"Blocked"', '"At Risk"']:
            assert state in src, f"Missing readiness state: {state}"

    def test_reinstate_has_reason_modal(self):
        src = _read(PAGE)
        assert "reinstateOpen" in src
        assert "reinstateMsg" in src
        assert "Reinstate Tenant" in src

    def test_uses_existing_finance_api_for_disputes(self):
        """No new backend needed — reuses financeApi.listSettlements/listPenalties
        with tenantId filter, which already existed from the customer_credits sprint."""
        src = _read(PAGE)
        assert "financeApi.listSettlements({ tenantId: id" in src
        assert "financeApi.listPenalties({ tenantId: id" in src
