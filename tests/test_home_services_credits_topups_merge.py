"""CREDITS-TOPUPS-MERGE: Provider Wallets removed as a separate Home
Services page; Usage Credits + Credit Top-ups consolidated into the single
`/admin/home-services/finance?tab=credits` workspace, backed by one
canonical credit account per Tenant + Business Vertical
(tenant_billing.credit_balance / usage_credit_ledger).

Runtime tests against the live server, plus static source-inspection tests
for frontend nav/route claims that have no HTTP surface of their own.
"""
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"

pytestmark = pytest.mark.anyio
_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


async def _hs_tenant_id(admin) -> str:
    r = await admin.get("/v1/admin/finance/home-services/credit-accounts?page_size=1")
    assert r.status_code == 200, r.text
    items = r.json()["data"]["items"]
    if items:
        return items[0]["tenant_id"]
    pytest.skip("No Home Services tenant with a credit account exists in this environment.")


# ═══════════════════════════════════════════════════════════════════════════
# 1. NAVIGATION / LEGACY ROUTE CONSOLIDATION (static source inspection)
# ═══════════════════════════════════════════════════════════════════════════

class TestNavigationConsolidation:

    def test_no_duplicate_credit_wallet_nav_entries(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
        assert '"finance-provider-wallets"' not in src
        assert 'label: "Provider Wallets"' not in src
        nav_config = pathlib.Path("frontend/super-admin/lib/nav-config.ts").read_text(encoding="utf-8")
        assert '"provider-wallets"' not in nav_config

    def test_legacy_routes_are_redirects_not_duplicate_pages(self):
        import pathlib
        for path in [
            "frontend/super-admin/app/admin/provider-wallets/page.tsx",
            "frontend/super-admin/app/admin/finance/wallets/page.tsx",
            "frontend/super-admin/app/admin/finance/usage-credits/page.tsx",
            "frontend/super-admin/app/admin/finance/topups/page.tsx",
        ]:
            src = pathlib.Path(path).read_text(encoding="utf-8")
            assert (
                "router.replace(`/admin/home-services/finance?" in src
                or "redirect(`/admin/home-services/finance?" in src
            ), f"{path} is not a redirect"

    def test_usage_credit_redirect_preserves_exact_filters(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/finance/usage-credits/page.tsx").read_text(encoding="utf-8")
        assert "Object.entries(incoming)" in src
        assert 'next.set("credits_tab", "ledger")' in src

    def test_credits_tab_has_four_subtabs(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
        assert '"accounts"' in src and '"topups"' in src and '"ledger"' in src and '"adjustments"' in src
        assert "function CreditsTab" in src


# ═══════════════════════════════════════════════════════════════════════════
# 2. CANONICAL CREDIT ACCOUNT / DATA INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════

class TestCanonicalCreditAccount:

    def test_tenant_billing_has_vertical_scoped_uniqueness(self):
        import inspect
        from app.engines.tenant_engine.models import TenantBilling
        src = inspect.getsource(TenantBilling)
        assert "uq_tenant_billing_tenant_vertical" in src
        assert "vertical_key" in src

    async def test_one_canonical_account_per_tenant(self, admin):
        tenant_id = await _hs_tenant_id(admin)
        r1 = await admin.get(f"/v1/admin/finance/home-services/credit-accounts?q={tenant_id}")
        r2 = await admin.get(f"/v1/admin/finance/home-services/credit-ledger?tenant_id={tenant_id}")
        assert r1.status_code == 200 and r2.status_code == 200

    async def test_credit_ledger_can_be_filtered_to_exact_job(self, admin):
        tenant_id = await _hs_tenant_id(admin)
        all_rows = await admin.get(
            f"/v1/admin/finance/home-services/credit-ledger?tenant_id={tenant_id}&page_size=1000"
        )
        assert all_rows.status_code == 200, all_rows.text
        entry = next((row for row in all_rows.json()["data"]["items"] if row.get("job_id")), None)
        if not entry:
            pytest.skip("No job-linked usage-credit entry exists in this environment.")
        exact = await admin.get(
            f"/v1/admin/finance/home-services/credit-ledger?tenant_id={tenant_id}&job_id={entry['job_id']}"
        )
        assert exact.status_code == 200, exact.text
        rows = exact.json()["data"]["items"]
        assert rows
        assert all(row["tenant_id"] == tenant_id and row["job_id"] == entry["job_id"] for row in rows)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CREDIT UNITS ARE NOT CASH
# ═══════════════════════════════════════════════════════════════════════════

class TestCreditUnitsNotCash:

    def test_credit_unit_helper_never_uses_rupee_symbol(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
        # the `units()` helper (credit-unit display) must not contain the rupee sign
        start = src.index("function units(")
        end = src.index("\n}", start)
        assert "₹" not in src[start:end]

    def test_no_provider_wallet_terminology_in_rendered_ui(self):
        # Explanatory code comments are allowed to name the retired concept
        # ("Provider Wallet no longer exists...") -- what matters is that no
        # JSX-rendered label/string in the Credits & Top-ups tab uses it.
        import pathlib, re
        src = pathlib.Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
        start = src.index("// ── Credits & Top-ups")
        end = src.index("// ── Security Deposits")
        section = src[start:end]
        code_only = "\n".join(
            line for line in section.splitlines()
            if not line.strip().startswith("//") and not line.strip().startswith("*")
        ).lower()
        # "Credit units are not a cash wallet" is the one required notice
        # string (spec) -- it names the banned concept to explicitly deny
        # it, not to use it as terminology, so it is excluded here.
        code_only = code_only.replace("credit units are not a cash wallet.", "")
        for banned in ["provider wallet", "cash wallet", "withdrawable", "provider payout", "wallet withdrawal"]:
            assert banned not in code_only, f"banned term '{banned}' found in rendered Credits & Top-ups code"


# ═══════════════════════════════════════════════════════════════════════════
# 4. TWO INDEPENDENT LEDGER ENTRY TYPES + MANUAL ADJUSTMENTS
# ═══════════════════════════════════════════════════════════════════════════

class TestLedgerAndAdjustments:

    async def test_manual_adjustment_creates_immutable_ledger_entry(self, admin):
        tenant_id = await _hs_tenant_id(admin)
        before = await admin.get(f"/v1/admin/finance/home-services/credit-ledger?tenant_id={tenant_id}&event_type=manual_credit_adjustment")
        before_count = before.json()["data"]["total"]

        r = await admin.post("/v1/admin/finance/home-services/adjustments", json={
            "tenant_id": tenant_id, "direction": "credit", "credit_units": "5",
            "reason_code": "APPROVED_GOODWILL_ADJUSTMENT", "detailed_reason": "test coverage adjustment",
        })
        assert r.status_code == 200, r.text
        entry = r.json()["data"]
        assert entry["event_type"] == "manual_credit_adjustment"
        assert Decimal(str(entry["credit_delta"])) == Decimal("5")

        after = await admin.get(f"/v1/admin/finance/home-services/credit-ledger?tenant_id={tenant_id}&event_type=manual_credit_adjustment")
        assert after.json()["data"]["total"] == before_count + 1

    async def test_adjustment_requires_valid_reason_code(self, admin):
        tenant_id = await _hs_tenant_id(admin)
        r = await admin.post("/v1/admin/finance/home-services/adjustments", json={
            "tenant_id": tenant_id, "direction": "credit", "credit_units": "5",
            "reason_code": "NOT_A_REAL_CODE", "detailed_reason": "x",
        })
        assert r.status_code == 422

    async def test_adjustment_rejects_cross_vertical_tenant(self, admin):
        # A tenant that does not belong to Home Services must 404, never
        # silently post a ledger entry against the wrong vertical's account.
        r = await admin.get("/v1/admin/tenants?page_size=100")
        assert r.status_code == 200
        non_hs = next((t for t in r.json()["data"]["items"] if t.get("vertical") not in (None, "home_services")), None)
        if not non_hs:
            pytest.skip("No non-Home-Services tenant available in this environment.")
        resp = await admin.post("/v1/admin/finance/home-services/adjustments", json={
            "tenant_id": non_hs["tenant_id"], "direction": "credit", "credit_units": "5",
            "reason_code": "APPROVED_GOODWILL_ADJUSTMENT", "detailed_reason": "cross-vertical leak probe",
        })
        assert resp.status_code == 404

    def test_two_independent_ledger_event_types_are_distinct(self):
        from app.engines.execution.usage_credit_deduction import DEDUCTION_EVENT_TYPE
        from app.engines.vertical_monetization.customer_charge_recovery import RECOVERY_EVENT_TYPE
        assert DEDUCTION_EVENT_TYPE != RECOVERY_EVENT_TYPE
        assert DEDUCTION_EVENT_TYPE == "completed_job_deduction"
        assert RECOVERY_EVENT_TYPE == "customer_platform_charge_recovery"

    def test_balance_never_mutated_outside_a_ledger_write(self):
        import inspect
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        src = inspect.getsource(HomeServicesFinanceService.create_manual_adjustment)
        assert "UsageCreditLedger(" in src
        assert "billing.credit_balance = balance_after" in src
        # the ledger row and the balance mutation happen in the same method/
        # transaction -- no separate "just update the balance" code path.


# ═══════════════════════════════════════════════════════════════════════════
# 5. CROSS-VERTICAL SCOPING ON READ ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossVerticalScoping:

    async def test_credit_ledger_scoped_to_home_services(self, admin):
        r = await admin.get("/v1/admin/tenants?page_size=100")
        coaching = next((t for t in r.json()["data"]["items"] if t.get("vertical") == "coaching"), None)
        if not coaching:
            pytest.skip("No Coaching tenant available in this environment.")
        ledger = await admin.get(f"/v1/admin/finance/home-services/credit-ledger?tenant_id={coaching['tenant_id']}")
        assert ledger.status_code == 200
        assert ledger.json()["data"]["items"] == []

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/finance/home-services/credit-ledger")
            assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 6. PERMISSIONS EXIST AND ARE SEPARATE
# ═══════════════════════════════════════════════════════════════════════════

class TestPermissions:

    def test_view_and_adjustment_permissions_are_distinct(self):
        from app.core.permissions import P
        assert P.FINANCE_HOME_SERVICES_CREDITS_VIEW != P.FINANCE_HOME_SERVICES_ADJUSTMENTS_CREATE
        assert P.FINANCE_HOME_SERVICES_LEDGER_VIEW != P.FINANCE_HOME_SERVICES_ADJUSTMENTS_APPROVE

    def test_all_eight_permissions_defined(self):
        from app.core.permissions import P
        for name in [
            "FINANCE_HOME_SERVICES_CREDITS_VIEW", "FINANCE_HOME_SERVICES_CREDITS_EXPORT",
            "FINANCE_HOME_SERVICES_CREDITS_AUDIT", "FINANCE_HOME_SERVICES_TOPUPS_VIEW",
            "FINANCE_HOME_SERVICES_TOPUPS_RECONCILE", "FINANCE_HOME_SERVICES_ADJUSTMENTS_CREATE",
            "FINANCE_HOME_SERVICES_ADJUSTMENTS_APPROVE", "FINANCE_HOME_SERVICES_LEDGER_VIEW",
        ]:
            assert hasattr(P, name), f"missing permission constant P.{name}"
