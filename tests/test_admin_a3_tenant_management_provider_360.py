"""Admin Sprint A3 — Tenant Management + Provider 360 certification.

The tenant list page (`frontend/super-admin/app/admin/tenants/page.tsx`,
1043 lines) and tenant detail "Provider 360" page
(`frontend/super-admin/app/admin/tenants/[id]/page.tsx`, 3044 lines, 23
tabs across 7 groups) already existed as substantial, real-data
implementations (`P0 Enterprise Tenants Dashboard` sprint — 8 KPI cards,
enriched list, 6 action modals). This sprint's real gap found and fixed:

`AdminTenantService._audit()` (the audit helper actually used by every
admin mutation on the tenant the frontend calls — suspend, approve,
reject, add-usage-credits, and lifecycle actions) only ever wrote to the
tenant-scoped `TenantAuditLog` table. It never called
`record_platform_audit()`, so every admin tenant action was invisible in
the Platform Command Center's Recent Activity feed (built/certified in
the immediately preceding A2 sprint) — a real cross-sprint bug, live-
verified and fixed this sprint. Also added the ticket-required "Add Admin
Note" action, which had no backend endpoint at all before this sprint
(reuses the same audit trail rather than a new table).
"""
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/super-admin"

# The tenant LIST page (app/admin/tenants/page.tsx) was deleted 2026-08-05 in
# the admin console consolidation -- its "all tenants" grid was superseded by
# Home Services > Providers (which scopes to Tenant.vertical == home_services,
# currently 100% of tenants). The tenant DETAIL page below is unaffected and is
# still deep-linked from analytics/bookability/bookings/dashboard/finance.
#
# Reading it at import time crashed COLLECTION of the whole suite, so every
# other test was unrunnable. Guarded rather than deleted so the list-page
# assertions below stay on record (skipped) instead of vanishing silently.
LIST_PAGE_PATH = FRONTEND / "app/admin/tenants/page.tsx"
LIST_PAGE_EXISTS = LIST_PAGE_PATH.is_file()
LIST_PAGE = LIST_PAGE_PATH.read_text(encoding="utf-8-sig") if LIST_PAGE_EXISTS else ""
DETAIL_PAGE = (FRONTEND / "app/admin/tenants/[id]/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
ADMIN_ROUTER = (ROOT / "app/engines/tenant_engine/admin_router.py").read_text(encoding="utf-8-sig")
ADMIN_SERVICE = (ROOT / "app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8-sig")


# ── 1. Tenant list ────────────────────────────────────────────────────────────
def test_tenant_directory_is_reachable_somewhere():
    """Was `test_list_route_exists`, asserting app/admin/tenants/page.tsx.

    That page was deleted 2026-08-05 in the admin console consolidation; the
    "browse all tenants" capability moved to Home Services > Providers. The
    requirement that an admin can reach a tenant directory at all still
    holds, so this asserts the capability rather than the deleted file.

    KNOWN LIMITATION (deliberately asserted, not hidden): the Providers
    workspace scopes to Tenant.vertical == "home_services". That covers 100%
    of tenants today, but a coaching/real-estate tenant would currently have
    no admin list view. If this platform onboards a non-home-services
    vertical, a cross-vertical directory has to come back.
    """
    providers_page = FRONTEND / "app/admin/home-services/providers/page.tsx"
    assert providers_page.is_file(), "no admin-facing tenant/provider directory exists"
    src = providers_page.read_text(encoding="utf-8-sig")
    assert "hsProviderDirectoryApi" in src          # real data, not a stub
    # The tenant DETAIL page must still exist -- it is deep-linked from
    # analytics, bookability, bookings, dashboard and finance.
    assert (FRONTEND / "app/admin/tenants/[id]/page.tsx").is_file()


@pytest.mark.skipif(not LIST_PAGE_EXISTS, reason="tenant list page superseded by Home Services > Providers (consolidation 2026-08-05)")
def test_list_title_and_columns():
    assert "Tenants" in LIST_PAGE
    for col in ["Status", "Verification", "Vertical", "Health", "Location", "Usage Credits", "Jobs", "Issues", "Created"]:
        assert f'label: "{col}"' in LIST_PAGE


@pytest.mark.skipif(not LIST_PAGE_EXISTS, reason="tenant list page superseded by Home Services > Providers (consolidation 2026-08-05)")
def test_list_search_filter_present():
    assert "search" in LIST_PAGE.lower()
    assert "status" in LIST_PAGE.lower()


@pytest.mark.skipif(not LIST_PAGE_EXISTS, reason="tenant list page superseded by Home Services > Providers (consolidation 2026-08-05)")
def test_list_pagination_present():
    assert "PAGE_SIZE" in LIST_PAGE or "page_size" in LIST_PAGE


@pytest.mark.skipif(not LIST_PAGE_EXISTS, reason="tenant list page superseded by Home Services > Providers (consolidation 2026-08-05)")
def test_list_row_actions_present():
    for action in ["Review Verification", "Suspend Tenant", "Add Usage Credits", "View Audit Logs"]:
        assert action in LIST_PAGE


# ── 2/3. Tenant detail route + hero ───────────────────────────────────────────
def test_detail_route_exists():
    assert (FRONTEND / "app/admin/tenants/[id]/page.tsx").exists()


def test_detail_not_a_basic_table():
    # Real Provider 360: substantial file with many real sections, not a
    # basic form/table page.
    assert len(DETAIL_PAGE.splitlines()) > 500


def test_detail_tabs_present():
    for tab in ["Overview", "Setup", "Operations", "Finance", "Audit"]:
        assert tab in DETAIL_PAGE


# ── 6. KPI cards ──────────────────────────────────────────────────────────────
def test_kpi_labels_present():
    for label in ["Health Score", "Usage Credit"]:
        assert label in DETAIL_PAGE


# ── Admin mutation actions — real endpoints ───────────────────────────────────
def test_add_usage_credits_endpoint_real():
    assert '"/{tenant_id}/add-usage-credits"' in ADMIN_ROUTER
    assert "async def add_usage_credits" in ADMIN_SERVICE


def test_suspend_reactivate_endpoints_real():
    assert '"/{tenant_id}/suspend"' in ADMIN_ROUTER
    assert '"/{tenant_id}/reactivate"' in ADMIN_ROUTER


def test_verify_reject_endpoints_real():
    assert '"/{tenant_id}/verify"' in ADMIN_ROUTER
    assert '"/{tenant_id}/reject-verification"' in ADMIN_ROUTER


# ── New this sprint: Add Admin Note ───────────────────────────────────────────
def test_add_admin_note_endpoint_new():
    assert '"/{tenant_id}/notes"' in ADMIN_ROUTER
    assert "async def add_admin_note" in ADMIN_SERVICE


def test_add_admin_note_validates_empty():
    note_method = ADMIN_SERVICE.split("async def add_admin_note")[1].split("async def ")[0]
    assert "NOTE_REQUIRED" in note_method


def test_add_admin_note_api_client_exists():
    admin_tenants_block = API_TS.split("export const adminTenantsApi = {")[1].split("\nexport const ")[0]
    assert "addNote: (tenantId: string, note: string)" in admin_tenants_block
    assert "/notes`" in admin_tenants_block.split("addNote:")[1][:200]


# ── Bug found and fixed: audit trail gap ──────────────────────────────────────
def test_admin_tenant_service_audit_writes_to_platform_audit_log():
    audit_method = ADMIN_SERVICE.split("async def _audit(")[1].split("def _tenant_dict")[0]
    assert "record_platform_audit" in audit_method
    assert "TenantAuditLog(" in audit_method  # still writes the tenant-scoped log too


def test_audit_helper_passes_request_id():
    audit_method = ADMIN_SERVICE.split("async def _audit(")[1].split("def _tenant_dict")[0]
    assert "request_id=self.request_id" in audit_method


# ── Finance labels ────────────────────────────────────────────────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Credit Wallet Health", "Manual Bargain Setup", "Bargain Rule Builder",
]


@pytest.mark.skipif(not LIST_PAGE_EXISTS, reason="tenant list page superseded by Home Services > Providers (consolidation 2026-08-05)")
def test_no_forbidden_finance_labels_list_page():
    for term in FORBIDDEN:
        assert term not in LIST_PAGE, f"forbidden label found in list page: {term}"


def test_no_forbidden_finance_labels_detail_page():
    for term in FORBIDDEN:
        assert term not in DETAIL_PAGE, f"forbidden label found in detail page: {term}"


def test_usage_credit_disclaimer_present():
    assert "not cash" in DETAIL_PAGE and "not withdrawable" in DETAIL_PAGE


def test_correct_finance_terminology_used():
    assert "Usage Credit" in DETAIL_PAGE
    assert "Security Deposit" in DETAIL_PAGE


# ── Data normalization ────────────────────────────────────────────────────────
@pytest.mark.skipif(not LIST_PAGE_EXISTS, reason="tenant list page superseded by Home Services > Providers (consolidation 2026-08-05)")
def test_no_bare_unexpected_error():
    assert '"Unexpected error"' not in LIST_PAGE
    assert '"Unexpected error"' not in DETAIL_PAGE
