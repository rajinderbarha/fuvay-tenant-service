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

FORBIDDEN_TERMS = [
    "Wallet Balance", "Cash Wallet", "Withdrawable Balance", "Tenant Payout",
    "Provider Earnings Wallet", "Escrow", "Platform Collected Service Payment",
    "Provider Cash Balance", "Credit Wallet Health", "Manual Bargain Setup",
    "Bargain Rule Builder",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestJobsNavigationGuard:
    def test_operations_page_still_carries_the_legacy_field_ops_disclosure_banner(self):
        """The legacy /admin/operations page must keep self-identifying as a
        separate, legacy lifecycle until it is either migrated or retired --
        removing this banner without a real migration would be a silent
        regression back toward treating /v1/jobs as canonical."""
        src = _read(SA / "app" / "admin" / "operations" / "page.tsx")
        assert "legacy" in src.lower()
        assert "/admin/home-services/service-jobs" in src

    def test_canonical_service_jobs_page_exists_and_is_not_a_stub(self):
        list_page = SA / "app" / "admin" / "home-services" / "service-jobs" / "page.tsx"
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

    def test_finance_usage_credits_and_reports_remain_in_nav(self):
        """Regression guard for the FINAL-L5-05 orphan-page fix."""
        src = _read(SA / "components" / "layout" / "AdminLayout.tsx")
        assert "/admin/finance/usage-credits" in src
        assert '"/admin/reports"' in src
