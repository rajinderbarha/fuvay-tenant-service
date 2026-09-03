"""FINAL-L5-05B — Automated IA regression guards (Part 16).

Static source-level checks that must fail if specific FINAL-L5-05/05B
regressions are reintroduced. These check the real, checked-in frontend
source files directly (not a live server) so they run fast and don't
need a browser.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
SA = ROOT / "frontend" / "super-admin"
APP = ROOT / "app"

FORBIDDEN_TERMS = [
    "Wallet Balance", "Cash Wallet", "Withdrawable Balance", "Tenant Payout",
    "Provider Earnings Wallet", "Escrow", "Platform Collected Service Payment",
    "Provider Cash Balance", "Credit Wallet Health", "Manual Bargain Setup",
    "Bargain Rule Builder",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestJobsNavigationGuard:
    def test_operations_compatibility_page_is_deleted(self):
        """The retired operations route must not return alongside the
        canonical Home Services Bookings & Jobs workspace."""
        assert not (SA / "app" / "admin" / "operations" / "page.tsx").exists()

    def test_operations_compatibility_pages_are_deleted(self):
        assert not (SA / "app" / "admin" / "operations" / "page.tsx").exists()
        assert not (SA / "app" / "admin" / "operations" / "[jobId]" / "page.tsx").exists()

    def test_admin_layout_jobs_nav_points_to_canonical_route(self):
        """FINAL-L5-05E: primary Jobs sidebar item must point at the
        unified Bookings & Jobs page, not the legacy /admin/operations."""
        src = _read(SA / "components" / "layout" / "AdminLayout.tsx")
        assert '"/admin/home-services/bookings-jobs"' in src

    def test_zero_active_jobs_api_imports_anywhere_in_super_admin(self):
        """FINAL-L5-05E: no Super Admin page/component may import jobsApi --
        the legacy client definition may remain in lib/api.ts (dead export)
        but must have zero import sites in app/ or components/."""
        import re
        hits = []
        for base in (SA / "app", SA / "components"):
            for path in base.rglob("*.ts*"):
                if "node_modules" in path.parts or ".next" in path.parts:
                    continue
                text = _read(path)
                for m in re.finditer(r"^import\s.*\bjobsApi\b.*$", text, re.MULTILINE):
                    hits.append(f"{path.relative_to(ROOT)}: {m.group(0).strip()}")
        assert not hits, f"active jobsApi imports found: {hits}"

    def test_canonical_service_jobs_page_exists_and_is_not_a_stub(self):
        list_page = SA / "app" / "admin" / "home-services" / "bookings-jobs" / "page.tsx"
        detail_page = SA / "app" / "admin" / "home-services" / "service-jobs" / "[jobId]" / "page.tsx"
        assert list_page.exists() and detail_page.exists()
        assert len(_read(list_page).splitlines()) > 20
        assert len(_read(detail_page).splitlines()) > 50

    def test_canonical_job_detail_page_renders_timeline_and_notes(self):
        """Regression guard for the FINAL-L5-05B fix: timeline/notes API
        clients must remain wired into the canonical detail page, not
        silently dropped back to dead code."""
        src = _read(SA / "app" / "admin" / "home-services" / "service-jobs" / "[jobId]" / "page.tsx")
        assert "adminServiceJobAssignmentApi" in src
        assert "adminExecutionApi" in src
        assert "Timeline & Notes" in src

    def test_canonical_job_detail_page_has_real_reassign_action(self):
        """Regression guard for the FINAL-L5-05C fix: the canonical page must
        keep a real, working reassignment action (not a disabled button) --
        this is the first of 4 mutation actions this sprint closed against
        service_jobs."""
        src = _read(SA / "app" / "admin" / "home-services" / "service-jobs" / "[jobId]" / "page.tsx")
        assert "reassignJob" in src
        assert "getEligibleTechnicians" in src
        assert "Reassign Technician" in src
        assert 'reason.trim()' in src  # reason is required, not optional


class TestForbiddenTerminologyGuard:
    def test_no_forbidden_terminology_in_admin_source(self):
        hits = []
        for path in SA.rglob("*.ts*"):
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            try:
                text = _read(path)
            except UnicodeDecodeError:
                continue
            for term in FORBIDDEN_TERMS:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT)}: {term!r}")
        assert not hits, f"forbidden terminology found: {hits}"


class TestNavHrefIntegrityGuard:
    def test_no_duplicate_nav_group_hrefs(self):
        """Regression guard for the FINAL-L5-05 hs-overview bug: two
        different nav items pointing at the same href, silently orphaning
        one of the two real pages."""
        import re
        src = _read(SA / "components" / "layout" / "AdminLayout.tsx")
        m = re.search(r"const NAV_GROUPS: NavGroup\[\] = \[(.*?)\n\];", src, re.DOTALL)
        assert m, "NAV_GROUPS array not found"
        hrefs = re.findall(r'href:\s*"([^"]+)"', m.group(1))
        dupes = {h for h in hrefs if hrefs.count(h) > 1}
        assert not dupes, f"duplicate NAV_GROUPS hrefs found: {dupes}"

    def test_consolidated_finance_and_analytics_remain_in_nav(self):
        """Finance and reports each live in their consolidated workspace."""
        src = _read(SA / "components" / "layout" / "AdminLayout.tsx")
        assert "/admin/home-services/finance" in src
        assert '"/admin/analytics"' in src


class TestFinalL5_05H_JobDeductionGate:
    """FINAL-L5-05H Part 7 P0 gate: engine_deduct_wallet posts to a
    different ledger (wallet_transactions) than the canonical Completed
    Job Deduction (usage_credit_ledger) and had zero internal callers.
    Must stay blocked so it can never become a second, non-cross-checked
    job-deduction path."""

    def test_commerce_wallet_deduct_route_is_blocked(self):
        src = _read(APP / "engines" / "platform_commerce" / "router.py")
        assert '"/tenants/{tenant_id}/wallet/deduct"' in src
        assert "status_code=410" in src

    def test_completed_job_deduction_remains_the_sole_wired_caller(self):
        exec_src = _read(APP / "engines" / "execution" / "home_service_service.py")
        assert "deduct_for_completed_job" in exec_src
        commerce_src = _read(APP / "engines" / "platform_commerce" / "service.py")
        assert "def engine_deduct_wallet" in commerce_src


class TestFinalL5_05I_DomainBoundaryGuards:
    """FINAL-L5-05I: source-of-truth and domain-boundary regression guards.
    See docs/final-l5-05/FINAL_L5_05I_CONSUMER_CLASSIFICATION.md and
    FINAL_L5_05I_DOMAIN_BOUNDARIES.md for the full evidence these encode."""

    def test_security_deposit_functions_never_touch_tenant_billing_or_usage_credit_ledger(self):
        """Retired deposit mutation primitives must not return."""
        src = _read(APP / "engines" / "platform_commerce" / "ledger.py")
        for fn_name in ("debit_deposit", "credit_deposit"):
            assert f"async def {fn_name}(" not in src

    def test_known_generic_wallet_mutation_endpoint_count_does_not_silently_grow(self):
        """Field Ops cannot reintroduce the shadow wallet mutation routes."""
        admin = _read(APP / "engines" / "field_ops" / "admin_finance_router.py")
        assert '"/{tenant_id}/wallet/top-up"' not in admin
        assert '"/{tenant_id}/wallet/adjust"' not in admin
        canonical = _read(APP / "engines" / "usage_credits" / "router.py")
        assert '"/{tenant_id}/adjustments"' in canonical

    def test_engine_deduct_wallet_pattern_not_duplicated_by_field_ops_commission_flow(self):
        """Part 9/11: field_ops.BillingService.deduct_commission is a
        separate, legacy-jobs-table-linked commission path (0 real rows) --
        it must not be re-pointed at service_jobs without going through the
        FINAL-L5-05I migration plan (would recreate the exact
        double-deduction risk FINAL-L5-05H closed for engine_deduct_wallet)."""
        src = _read(APP / "engines" / "field_ops" / "billing_service.py")
        assert "from app.engines.field_ops.models import Job" in src
        # Must not import the canonical service_jobs execution model directly.
        assert "app.engines.execution.usage_credit_deduction" not in src
