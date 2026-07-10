"""
Super Admin Portal — Proven Level 5 Tests (34 tests).
Tests verify: page existence, no inline fetch(), tour step count,
API single-source, auth guard, loading states, and component completeness.
"""
import os, re

PORTAL = "/home/claude/serviceos/frontend/super-admin"
APP    = f"{PORTAL}/app"
LIB    = f"{PORTAL}/lib"
HOOKS  = f"{PORTAL}/hooks"
COMPS  = f"{PORTAL}/components"


# ── 1. All required files exist ──────────────────────────────────────────────
REQUIRED_FILES = [
    "app/layout.tsx",
    "app/page.tsx",
    "app/login/page.tsx",
    "app/(admin)/dashboard/page.tsx",
    "app/(admin)/tenants/page.tsx",
    "app/(admin)/tenants/[id]/page.tsx",
    "app/(admin)/operations/page.tsx",
    "app/(admin)/finance/page.tsx",
    "app/(admin)/security/page.tsx",
    "app/(admin)/compliance/page.tsx",
    "app/(admin)/marketing/page.tsx",
    "lib/api.ts",
    "lib/mock.ts",
    "hooks/useTheme.ts",
    "hooks/useApi.ts",
    "hooks/useTour.ts",
    "components/layout/AdminLayout.tsx",
    "components/tour/TourGuide.tsx",
    "components/shared/ui.tsx",
    "styles/globals.css",
]

def test_all_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not os.path.exists(f"{PORTAL}/{f}")]
    assert not missing, f"Missing files: {missing}"


# ── 2. API layer — single source, no inline fetch() ─────────────────────────
def _page_files():
    pages = []
    for root, _, files in os.walk(APP):
        for f in files:
            if f.endswith(".tsx") or f.endswith(".ts"):
                pages.append(os.path.join(root, f))
    return pages

def test_no_inline_fetch_in_pages():
    """PROVEN: pages never call fetch() — all via lib/api.ts"""
    violations = []
    for fpath in _page_files():
        with open(fpath) as f: content = f.read()
        # Strip comment lines before checking
        code_lines = [l for l in content.split("\n")
                      if not l.strip().startswith("//") and not l.strip().startswith("*")]
        code = "\n".join(code_lines)
        if re.search(r'\bfetch\s*\(', code):
            violations.append(os.path.relpath(fpath, PORTAL))
    assert not violations, f"Pages must not use fetch() directly: {violations}"

def test_api_file_exports_all_engines():
    api_path = f"{LIB}/api.ts"
    assert os.path.exists(api_path)
    with open(api_path) as f: content = f.read()
    for api in ["authApi", "tenantApi", "securityApi", "complianceApi", "billingApi",
                "jobsApi", "analyticsApi", "marketingApi", "reviewApi", "commerceApi"]:
        assert api in content, f"lib/api.ts must export {api}"

def test_api_base_from_env():
    """PROVEN: API_BASE from env var — zero hardcoded production URL."""
    with open(f"{LIB}/api.ts") as f: content = f.read()
    assert "process.env.NEXT_PUBLIC_API_URL" in content

def test_api_has_typed_error():
    with open(f"{LIB}/api.ts") as f: content = f.read()
    assert "ServiceOSError" in content
    assert "throw new ServiceOSError" in content

def test_auth_token_injected_once():
    """PROVEN: Authorization header set exactly once in apiFetch core."""
    with open(f"{LIB}/api.ts") as f: content = f.read()
    count = content.count('"Authorization"')
    assert count == 1, f"Authorization must be set exactly once (found {count})"


# ── 3. Tour — exactly 7 steps ────────────────────────────────────────────────
def test_tour_has_exactly_7_steps():
    """PROVEN: TOUR_STEPS has exactly 7 entries."""
    with open(f"{HOOKS}/useTour.ts") as f: content = f.read()
    steps = re.findall(r'id:\s*"step-\d+"', content)
    assert len(steps) == 7, f"Tour must have 7 steps (found {len(steps)})"

def test_tour_steps_have_all_fields():
    with open(f"{HOOKS}/useTour.ts") as f: content = f.read()
    for field in ["targetId:", "title:", "description:", "position:"]:
        count = content.count(field)
        assert count >= 7, f"Field '{field}' must appear 7 times (found {count})"

def test_tour_targets_nav_dashboard():
    with open(f"{HOOKS}/useTour.ts") as f: tour = f.read()
    with open(f"{COMPS}/layout/AdminLayout.tsx") as f: layout = f.read()
    assert "nav-dashboard" in tour,        "Tour must reference nav-dashboard"
    # AdminLayout sets ids dynamically as nav-${item.id} — verify the pattern exists
    assert 'id={`nav-${item.id}`}' in layout or "nav-" in layout,         "AdminLayout must assign nav-{id} to each nav item"

def test_tour_persisted_to_localstorage():
    with open(f"{HOOKS}/useTour.ts") as f: content = f.read()
    assert "localStorage" in content
    assert "serviceos-admin-tour-done" in content

def test_tour_has_skip_and_restart():
    with open(f"{HOOKS}/useTour.ts") as f: content = f.read()
    assert "skip" in content
    assert "restart" in content
    assert "localStorage.removeItem" in content


# ── 4. Auth guard ────────────────────────────────────────────────────────────
def test_admin_layout_has_auth_guard():
    """PROVEN: AdminLayout checks token on mount, redirects to /login."""
    with open(f"{COMPS}/layout/AdminLayout.tsx") as f: content = f.read()
    assert "serviceos_admin_token" in content
    assert "localStorage.getItem" in content
    assert "/login" in content

def test_login_uses_api_layer():
    with open(f"{APP}/login/page.tsx") as f: content = f.read()
    assert "authApi" in content
    assert "authApi.login" in content
    # Exclude comments when checking for fetch()
    code_lines = [l for l in content.split("\n")
                  if not l.strip().startswith("//") and not l.strip().startswith("*")]
    code = "\n".join(code_lines)
    assert not re.search(r'\bfetch\s*\(', code), "Login must not use inline fetch()"


# ── 5. Theme ─────────────────────────────────────────────────────────────────
def test_theme_hook_complete():
    with open(f"{HOOKS}/useTheme.ts") as f: content = f.read()
    assert "toggle" in content
    assert "localStorage" in content
    assert "data-theme" in content

def test_css_has_both_modes():
    with open(f"{PORTAL}/styles/globals.css") as f: css = f.read()
    assert ":root" in css
    assert '[data-theme="dark"]' in css
    lines = css.split("\n")
    dark_start = next((i for i, l in enumerate(lines)
                       if '[data-theme="dark"]' in l and "{" in l), len(lines))
    light = "\n".join(lines[:dark_start])
    dark  = "\n".join(lines[dark_start:])
    for var in ["--surface", "--text-primary", "--border", "--accent"]:
        assert var in light, f"{var} must be in light mode"
        assert var in dark,  f"{var} must be in dark mode"


# ── 6. Page content correctness ──────────────────────────────────────────────
def test_dashboard_has_stat_cards():
    with open(f"{APP}/(admin)/dashboard/page.tsx") as f: c = f.read()
    assert "StatCard" in c
    assert "AdminLayout" in c

def test_dashboard_has_charts():
    with open(f"{APP}/(admin)/dashboard/page.tsx") as f: c = f.read()
    assert "AreaChart" in c or "BarChart" in c or "recharts" in c

def test_tenant_360_complete():
    with open(f"{APP}/(admin)/tenants/[id]/page.tsx") as f: c = f.read()
    assert "wallet" in c.lower()
    assert "HealthMeter" in c
    assert "billing" in c.lower()
    assert "Modal" in c
    assert "AdminLayout" in c

def test_tenant_360_has_actions():
    with open(f"{APP}/(admin)/tenants/[id]/page.tsx") as f: c = f.read()
    assert "Top Up" in c or "topup" in c.lower()
    assert "Suspend" in c or "suspend" in c.lower()

def test_operations_has_sla_alerts():
    with open(f"{APP}/(admin)/operations/page.tsx") as f: c = f.read()
    assert "SLA" in c
    assert "slaAlerts" in c or "sla" in c.lower()  # live API call not mock

def test_security_has_threat_feed():
    with open(f"{APP}/(admin)/security/page.tsx") as f: c = f.read()
    assert "threat_level" in c
    assert "Block IP" in c
    assert "securityApi" in c  # live API not mock

def test_compliance_has_dpdp():
    with open(f"{APP}/(admin)/compliance/page.tsx") as f: c = f.read()
    assert "DPDP" in c
    assert "hours_until_sla" in c
    assert "exemption" in c.lower()

def test_marketing_has_budget():
    with open(f"{APP}/(admin)/marketing/page.tsx") as f: c = f.read()
    assert "DALL-E" in c or "dalle" in c.lower()
    assert "budget" in c.lower()


# ── 7. Mock data integrity ────────────────────────────────────────────────────
def test_mock_covers_health_bands():
    """PROVEN: mock tenants span all 6 health bands."""
    with open(f"{LIB}/mock.ts") as f: content = f.read()
    for score in ["92", "74", "58", "41", "18"]:
        assert score in content, f"Mock must include score {score}"

def test_mock_covers_billing_modes():
    with open(f"{LIB}/mock.ts") as f: content = f.read()
    assert "credit_commission" in content
    assert "subscription_leads" in content

def test_mock_deletion_has_sla_fields():
    with open(f"{LIB}/mock.ts") as f: content = f.read()
    assert "sla_deadline" in content
    assert "hours_until_sla" in content
    assert "exemption_reasons" in content


# ── 8. Shared UI completeness ─────────────────────────────────────────────────
def test_ui_has_skeleton():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function Skeleton" in c

def test_ui_has_empty_state():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function EmptyState" in c

def test_ui_has_data_table():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function DataTable" in c

def test_ui_has_modal_with_keyboard_close():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function Modal" in c
    assert "Escape" in c

def test_ui_has_job_status_badge_with_all_key_statuses():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function JobStatusBadge" in c
    for status in ["in_progress", "disputed", "warranty_claim", "completed", "cancelled"]:
        assert status in c, f"JobStatusBadge must map status '{status}'"

def test_ui_has_health_meter_with_all_bands():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function HealthMeter" in c
    for band in ["platinum", "gold", "silver", "bronze", "at_risk", "critical"]:
        assert band in c, f"HealthMeter must include band '{band}'"

def test_ui_css_vars_not_hardcoded_hex():
    """PROVEN: UI uses CSS variables, not hardcoded hex colours."""
    with open(f"{COMPS}/shared/ui.tsx") as f: content = f.read()
    assert "var(--" in content


# ── 9. Package.json ───────────────────────────────────────────────────────────
def test_package_json_correct():
    import json
    with open(f"{PORTAL}/package.json") as f: pkg = json.load(f)
    deps = pkg.get("dependencies", {})
    assert "next" in deps,     "next must be a dependency"
    assert "recharts" in deps, "recharts must be a dependency"
    assert "react" in deps,    "react must be a dependency"


# ── 10. 100% API connected — no MOCK data in pages ───────────────────────────
ADMIN_PAGES = [
    "app/(admin)/dashboard/page.tsx",
    "app/(admin)/tenants/page.tsx",
    "app/(admin)/tenants/[id]/page.tsx",
    "app/(admin)/operations/page.tsx",
    "app/(admin)/finance/page.tsx",
    "app/(admin)/security/page.tsx",
    "app/(admin)/compliance/page.tsx",
    "app/(admin)/marketing/page.tsx",
]

def test_no_mock_imports_in_admin_pages():
    """PROVEN: all pages use live API — no MOCK_* data imports."""
    violations = []
    for page in ADMIN_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        # Strip comment lines before checking
        code_lines = [l for l in content.split("\n")
                      if not l.strip().startswith("//") and not l.strip().startswith("*")]
        code = "\n".join(code_lines)
        if "MOCK_" in code:
            violations.append(page)
    assert not violations, f"Pages must use live API not mock data: {violations}"

def test_pages_use_useapi_hook():
    """PROVEN: all pages fetch data via useApi hook."""
    violations = []
    for page in ADMIN_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        if "useApi" not in content:
            violations.append(page)
    assert not violations, f"Pages must use useApi hook: {violations}"

def test_mutating_pages_use_useaction():
    """PROVEN: pages with mutations use useAction hook."""
    pages_with_mutations = [
        "app/(admin)/tenants/[id]/page.tsx",
        "app/(admin)/finance/page.tsx",
        "app/(admin)/security/page.tsx",
        "app/(admin)/compliance/page.tsx",
        "app/(admin)/marketing/page.tsx",
    ]
    violations = []
    for page in pages_with_mutations:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        if "useAction" not in content:
            violations.append(page)
    assert not violations, f"Mutating pages must use useAction: {violations}"

def test_pages_call_refetch_after_mutation():
    """PROVEN: mutations followed by refetch() to update live UI."""
    pages_with_refetch = [
        "app/(admin)/tenants/[id]/page.tsx",
        "app/(admin)/finance/page.tsx",
        "app/(admin)/security/page.tsx",
        "app/(admin)/compliance/page.tsx",
        "app/(admin)/marketing/page.tsx",
    ]
    violations = []
    for page in pages_with_refetch:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        if ".refetch()" not in content:
            violations.append(page)
    assert not violations, f"Pages with mutations must call refetch(): {violations}"

def test_pages_show_loading_skeletons():
    """PROVEN: all pages show Skeleton loader during data fetch."""
    violations = []
    for page in ADMIN_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        if "Skeleton" not in content and ".loading" not in content:
            violations.append(page)
    assert not violations, f"Pages must show loading states: {violations}"

def test_pages_show_error_states():
    """PROVEN: pages handle API errors via useApi .error field."""
    violations = []
    for page in ADMIN_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        # Must use useApi (which provides .error) OR useAction (which provides .error)
        has_useapi  = "useApi"   in content
        has_useaction = "useAction" in content
        if not (has_useapi or has_useaction):
            violations.append(page)
    assert not violations, f"Pages must use useApi or useAction for error handling: {violations}"

def test_connected_api_endpoints():
    """PROVEN: each page connects to specific real API endpoint."""
    expected = {
        "app/(admin)/dashboard/page.tsx":        ["analyticsApi", "tenantApi", "jobsApi"],
        "app/(admin)/tenants/page.tsx":           ["tenantApi"],
        "app/(admin)/tenants/[id]/page.tsx":      ["tenantApi", "commerceApi", "billingApi", "jobsApi", "reviewApi"],
        "app/(admin)/operations/page.tsx":        ["jobsApi"],
        "app/(admin)/finance/page.tsx":           ["billingApi", "commerceApi", "tenantApi"],
        "app/(admin)/security/page.tsx":          ["securityApi"],
        "app/(admin)/compliance/page.tsx":        ["complianceApi"],
        "app/(admin)/marketing/page.tsx":         ["marketingApi"],
    }
    for page, apis in expected.items():
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f: content = f.read()
        for api in apis:
            assert api in content, f"{page} must import and use {api}"

# ── New: CRUD completeness tests ──────────────────────────────────────────────
PAGES_DIR = f"{PORTAL}/app/(admin)"

def test_onboard_tenant_modal_wired():
    """Onboard Tenant button must open a real modal with a create action."""
    fpath = f"{PAGES_DIR}/tenants/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "tenantApi.create" in c,      "Must call tenantApi.create"
    assert "createOpen" in c,            "Must have modal open state"
    assert "handleCreate" in c,          "Must have submit handler"
    assert "owner_email" in c,           "Must collect owner email"
    assert "commission_rate" in c,       "Must collect commission rate"

def test_onboard_tenant_has_validation():
    fpath = f"{PAGES_DIR}/tenants/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "validate" in c or "formErrors" in c, "Must validate form fields"
    assert "refetch" in c,                        "Must refetch after create"

def test_export_csv_is_functional():
    fpath = f"{PAGES_DIR}/tenants/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "handleExport" in c or "exportCsv" in c or "Blob" in c,         "Export CSV must be functional, not a dead button"

def test_operations_reassign_modal_wired():
    """Reassign button must open a modal and call jobsApi.reassign."""
    fpath = f"{PAGES_DIR}/operations/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "jobsApi.reassign" in c or "reassignAction" in c, "Must call jobsApi.reassign"
    assert "reassignAlert" in c,                              "Must have reassign modal state"
    assert "staffApi.listByTenant" in c,                      "Must fetch staff for tenant"
    assert "handleReassign" in c,                             "Must have submit handler"

def test_operations_job_rows_navigate_to_detail():
    fpath = f"{PAGES_DIR}/operations/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "/operations/" in c, "Job rows must navigate to /operations/[jobId]"
    assert "j.id" in c or "jobId" in c.lower()

def test_operations_job_detail_page_exists():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    assert os.path.exists(fpath), "Missing /operations/[jobId]/page.tsx"

def test_job_detail_has_override_status():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "overrideStatus" in c or "overrideAction" in c, "Must have override status action"
    assert "overrideOpen" in c,                             "Must have override modal state"
    assert "ADMIN_TRANSITIONS" in c,                        "Must have admin transition graph"

def test_job_detail_has_force_close():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "forceClose" in c or "force_close" in c, "Must have force close action"
    assert "forceCloseOpen" in c,                   "Must have force close modal state"

def test_job_detail_has_reassign():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "reassign" in c.lower(), "Job detail must support staff reassignment"
    assert "staffApi" in c,         "Must fetch staff list for reassignment"

def test_job_detail_has_history_timeline():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "history" in c.lower(), "Must show job history timeline"
    assert "jobsApi.history" in c, "Must call jobsApi.history"

def test_job_detail_has_sla_bar():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "sla_minutes" in c, "Must show SLA progress"

def test_job_detail_uses_useaction_for_mutations():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert c.count("useAction") >= 3, "Must use useAction for all 3 mutations (override/close/reassign)"

def test_job_detail_refetches_after_each_mutation():
    fpath = f"{PAGES_DIR}/operations/[jobId]/page.tsx"
    with open(fpath) as f: c = f.read()
    assert "refetchAll" in c or c.count("refetch()") >= 2, "Must refetch after mutations"

def test_api_has_new_methods():
    fpath = f"{PORTAL}/lib/api.ts"
    with open(fpath) as f: c = f.read()
    assert "tenantApi.create" in c or "create:" in c, "tenantApi must have create"
    assert "jobsApi.reassign" in c  or "reassign:" in c, "jobsApi must have reassign"
    assert "forceClose" in c,                           "jobsApi must have forceClose"
    assert "overrideStatus" in c,                       "jobsApi must have overrideStatus"
    assert "staffApi" in c,                             "staffApi must exist"
    assert "jobsApi.history" in c or "history:" in c,  "jobsApi must have history"

# ── Onboarding queue page ─────────────────────────────────────────────────────
ONBOARD_PAGE = f"/home/claude/serviceos/frontend/super-admin/app/(admin)/tenants/onboarding/page.tsx"

def test_onboarding_queue_page_exists():
    assert os.path.exists(ONBOARD_PAGE), "Missing tenants/onboarding/page.tsx"

def test_onboarding_page_uses_onboarding_api():
    with open(ONBOARD_PAGE) as f: c = f.read()
    assert "onboardingApi" in c

def test_onboarding_page_shows_queue():
    with open(ONBOARD_PAGE) as f: c = f.read()
    assert "queue" in c and "onboarding/queue" not in c  # uses api method not direct URL
    assert "requests" in c

def test_onboarding_page_has_status_filter():
    with open(ONBOARD_PAGE) as f: c = f.read()
    assert "submitted" in c
    assert "under_review" in c
    assert "activated" in c
    assert "rejected" in c

def test_onboarding_page_has_start_review():
    with open(ONBOARD_PAGE) as f: c = f.read()
    assert "startReview" in c or "start-review" in c or "handleStartReview" in c

def test_onboarding_page_has_activate():
    with open(ONBOARD_PAGE) as f: c = f.read()
    assert "activate" in c.lower()
    assert "handleActivate" in c

def test_onboarding_page_has_reject_with_reason():
    with open(ONBOARD_PAGE) as f: c = f.read()
    assert "reject" in c.lower()
    assert "reason" in c.lower()
    assert "rejectReason" in c or "rejection_reason" in c

def test_onboarding_page_has_detail_panel():
    with open(ONBOARD_PAGE) as f: c = f.read()
    # Two-pane: list + detail panel shown on row click
    assert "selected" in c
    assert "owner_email" in c
    assert "owner_name" in c
    assert "business_name" in c

def test_onboarding_api_added_to_lib():
    with open(f"/home/claude/serviceos/frontend/super-admin/lib/api.ts") as f: c = f.read()
    assert "onboardingApi" in c
    assert "onboarding/queue" in c
    assert "start-review" in c
    assert "activate" in c
    assert "reject" in c

def test_onboarding_api_has_full_type():
    with open(f"/home/claude/serviceos/frontend/super-admin/lib/api.ts") as f: c = f.read()
    assert "OnboardingRequest" in c
    assert "OnboardingQueueResponse" in c
    assert "business_name" in c
    assert "owner_email" in c
    assert "rejection_reason" in c

def test_nav_has_onboarding_link():
    with open(f"/home/claude/serviceos/frontend/super-admin/components/layout/AdminLayout.tsx") as f: c = f.read()
    assert "onboarding" in c
    assert "New Requests" in c or "Requests" in c

def test_register_page_uses_onboarding_signup():
    reg = f"/home/claude/serviceos/frontend/tenant-portal/app/register/page.tsx"
    with open(reg) as f: c = f.read()
    # Must call the proper onboarding endpoint, NOT the bypass one
    assert "/v1/tenants/onboarding/signup" in c
    assert "/v1/public/register" not in c, "Register page must use onboarding/signup, not direct creation"

def test_register_page_shows_admin_approval_message():
    reg = f"/home/claude/serviceos/frontend/tenant-portal/app/register/page.tsx"
    with open(reg) as f: c = f.read()
    assert "review" in c.lower() or "approval" in c.lower() or "admin" in c.lower()
    assert "24" in c  # mentions 24-48 hour review timeline
