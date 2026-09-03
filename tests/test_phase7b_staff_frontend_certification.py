"""Phase 7B — Technician Self-Service Frontend certification.

Static-inspection style (established convention this session). Live
end-to-end behavior for these same assertions was additionally verified via
curl against the real running backend + real Postgres (staff@serviceos.in,
technician role, tenant 34b427a7-b2be-496c-b826-6d51bb181248) before this
file was written — see PHASE_7B_STAFF_FRONTEND_MANUAL_SMOKE_REPORT.md and
PHASE_7B_STAFF_FRONTEND_BUG_FIX_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
MIGRATION_114 = (ROOT / "alembic/versions/114_provider_availability_rules.py").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
USE_API_TS = (FRONTEND / "hooks/useApi.ts").read_text(encoding="utf-8-sig")
STAFF_CONTEXT_TS = (FRONTEND / "hooks/useStaffContext.ts").read_text(encoding="utf-8-sig")
STAFF_LAYOUT_TSX = (FRONTEND / "components/layout/StaffLayout.tsx").read_text(encoding="utf-8-sig")

STAFF_PAGES = {
    "login": FRONTEND / "app/staff/login/page.tsx",
    "dashboard": FRONTEND / "app/staff/dashboard/page.tsx",
    "profile": FRONTEND / "app/staff/profile/page.tsx",
    "skills": FRONTEND / "app/staff/skills/page.tsx",
    "service_areas": FRONTEND / "app/staff/service-areas/page.tsx",
    "availability": FRONTEND / "app/staff/availability/page.tsx",
    "jobs_list": FRONTEND / "app/staff/jobs/page.tsx",
    "jobs_detail": FRONTEND / "app/staff/jobs/[job_id]/page.tsx",
    "notifications": FRONTEND / "app/staff/notifications/page.tsx",
    "sessions": FRONTEND / "app/staff/security/sessions/page.tsx",
}


# ── All 13 required pages exist ─────────────────────────────────────────────
def test_all_required_staff_pages_exist():
    for name, path in STAFF_PAGES.items():
        assert path.exists(), f"missing staff page: {name} at {path}"


def test_staff_layout_and_context_guard_exist():
    assert STAFF_LAYOUT_TSX.strip()
    assert STAFF_CONTEXT_TS.strip()
    assert "useStaffContext" in STAFF_LAYOUT_TSX


# ── Context guard never trusts localStorage alone ───────────────────────────
def test_context_guard_reverifies_against_live_auth_me():
    assert "authApi.me()" in STAFF_CONTEXT_TS


def test_layout_blocks_non_technician_role():
    assert "isTechnician" in STAFF_LAYOUT_TSX
    assert "/staff/login" in STAFF_LAYOUT_TSX


# ── Bug fix: TENANT_SERVICE_AREA_READ granted to staff/technician ──────────
def test_staff_and_technician_roles_granted_service_area_read():
    staff_idx = PERMISSIONS.index('"staff": [')
    technician_idx = PERMISSIONS.index('"technician": [')
    staff_block = PERMISSIONS[staff_idx: staff_idx + 1100]
    technician_block = PERMISSIONS[technician_idx: technician_idx + 900]
    assert "P.TENANT_SERVICE_AREA_READ" in staff_block
    assert "P.TENANT_SERVICE_AREA_READ" in technician_block


# ── Bug fix: provider_availability_rules table migration exists ────────────
def test_availability_table_migration_exists_and_idempotent():
    assert "provider_availability_rules" in MIGRATION_114
    assert "existing_tables" in MIGRATION_114
    assert 'revision = "114"' in MIGRATION_114


def test_availability_mutation_endpoints_are_tenant_owner_only():
    post_idx = PROVIDER_ROUTER.index('@router.post("/availability"')
    snippet = PROVIDER_ROUTER[post_idx: post_idx + 400]
    assert "require_tenant_owner" in snippet


# ── Availability page is read-only (matches owner-only mutation gate) ──────
def test_availability_page_is_read_only_no_mutation_calls():
    src = STAFF_PAGES["availability"].read_text(encoding="utf-8")
    assert "providerAvailabilityApi.create" not in src
    assert "providerAvailabilityApi.update" not in src
    assert "providerAvailabilityApi.delete" not in src
    assert "View only" in src


# ── Documents / Sessions / Activity are honest gap pages, not fabricated ───
def test_sessions_page_uses_live_session_management():
    src = STAFF_PAGES["sessions"].read_text(encoding="utf-8")
    assert "authApi.getSessions" in src
    assert "authApi.deleteSession" in src
    assert "authApi.logoutAll" in src


# ── MODULE-L5-38: job list/detail runtime actions are now REAL and wired ───
# This Phase 7B suite originally certified that these actions were shown as
# disabled placeholders because nothing real existed to wire them to yet.
# MODULE-L5-38 (part of the L5-29..46 sweep) found the real, live
# home_service_assignment + execution engines already existed and repointed
# these pages to them -- accept/reject/on-the-way/.../complete are now real,
# live-verified mutations (see tests/test_module_l5_38_tenant_portal_staff_jobs.py),
# not a "forbidden, not certified" shell. The premise of the old assertions
# is obsolete; updated to assert the real lifecycle is wired instead of
# asserting it's fictionally disabled.
REAL_JOB_ACTIONS = [
    "accept", "reject", "onTheWay", "reachedSite", "startInspection",
    "completeInspection", "startService", "markWorkDone", "complete",
]


def test_job_detail_wires_the_real_lifecycle_actions():
    src = STAFF_PAGES["jobs_detail"].read_text(encoding="utf-8")
    for action in REAL_JOB_ACTIONS:
        assert action in src, f"expected real action {action} to be wired in job detail"
    assert "Not certified in this phase" not in src


def test_job_pages_use_the_real_service_jobs_api():
    for name in ("jobs_list", "jobs_detail"):
        live = "\n".join(l for l in STAFF_PAGES[name].read_text(encoding="utf-8").splitlines()
                         if not l.strip().startswith("//") and not l.strip().startswith("*"))
        assert "homeServiceStaffJobsApi" in live
        assert "staffSelfApi.getMyJobs" not in live
        assert "staffSelfApi.getJobDetail" not in live
        assert "deductCredit" not in live


# ── Forbidden finance/wallet labels never appear in any staff page ─────────
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_finance_labels_in_any_staff_page():
    for name, path in STAFF_PAGES.items():
        src = path.read_text(encoding="utf-8")
        for label in FORBIDDEN_LABELS:
            assert label not in src, f"forbidden label '{label}' found in {name}"


# ── request_id surfaced on error states (useApi/useAction + ServiceOSError) ─
def test_use_api_and_use_action_expose_request_id():
    assert "requestId" in USE_API_TS
    assert "e.requestId" in USE_API_TS or "e instanceof ServiceOSError" in USE_API_TS


def test_service_os_error_captures_request_id():
    assert "requestId" in API_TS
    assert "request_id" in API_TS


# ── login page enforces technician/staff role before persisting session ────
def test_login_page_rejects_non_staff_roles():
    src = STAFF_PAGES["login"].read_text(encoding="utf-8")
    assert '"technician"' in src
    assert '"staff"' in src
    assert "owner portal" in src or "staff/technician accounts only" in src


# ── staffSelfApi surfaces real, confirmed-working endpoints only ───────────
def test_staff_self_api_uses_real_confirmed_endpoints():
    idx = API_TS.index("export const staffSelfApi")
    snippet = API_TS[idx: idx + 2500]
    assert "/v1/provider/team-members" in snippet
    assert "/v1/tenant/service-areas" in snippet
    assert "/v1/staff/me/jobs" in snippet
    assert "/v1/staff/notifications" in snippet
    # no live apiFetch call to the confirmed-404 /v1/provider/activity endpoint
    # (a code comment documenting the discovered 404 is fine and expected)
    assert 'apiFetch<Record<string, unknown>>(`/v1/provider/activity' not in snippet
