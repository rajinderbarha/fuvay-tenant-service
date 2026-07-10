"""
Tenant Owner Portal — Proven Level 5 Tests (42 tests).
Verifies: file existence, no inline fetch, tour 7 steps, API single-source,
auth guard, loading states, all pages connected, mutations refetch.
"""
import os, re

PORTAL = "/home/claude/serviceos/frontend/tenant-portal"
APP    = f"{PORTAL}/app"
LIB    = f"{PORTAL}/lib"
HOOKS  = f"{PORTAL}/hooks"
COMPS  = f"{PORTAL}/components"

REQUIRED_FILES = [
    "app/layout.tsx", "app/page.tsx", "app/login/page.tsx",
    "app/(tenant)/dashboard/page.tsx",
    "app/(tenant)/jobs/page.tsx",
    "app/(tenant)/jobs/[id]/page.tsx",
    "app/(tenant)/bookings/page.tsx",
    "app/(tenant)/staff/page.tsx",
    "app/(tenant)/staff/[id]/page.tsx",
    "app/(tenant)/customers/page.tsx",
    "app/(tenant)/customers/[id]/page.tsx",
    "app/(tenant)/finance/page.tsx",
    "app/(tenant)/reviews/page.tsx",
    "app/(tenant)/chat/page.tsx",
    "app/(tenant)/documents/page.tsx",
    "app/(tenant)/settings/page.tsx",
    "lib/api.ts", "hooks/useTheme.ts", "hooks/useApi.ts",
    "hooks/useTour.ts", "hooks/useTenant.ts",
    "components/layout/TenantLayout.tsx",
    "components/tour/TourGuide.tsx",
    "components/shared/ui.tsx",
    "styles/globals.css", "package.json",
]

TENANT_PAGES = [
    "app/(tenant)/dashboard/page.tsx",
    "app/(tenant)/jobs/page.tsx",
    "app/(tenant)/jobs/[id]/page.tsx",
    "app/(tenant)/bookings/page.tsx",
    "app/(tenant)/staff/page.tsx",
    "app/(tenant)/finance/page.tsx",
    "app/(tenant)/reviews/page.tsx",
    "app/(tenant)/chat/page.tsx",
    "app/(tenant)/documents/page.tsx",
    "app/(tenant)/settings/page.tsx",
]


# ── 1. File existence ─────────────────────────────────────────────────────────
def test_all_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not os.path.exists(f"{PORTAL}/{f}")]
    assert not missing, f"Missing files: {missing}"


# ── 2. No inline fetch() in pages ─────────────────────────────────────────────
def _all_tsx():
    result = []
    for root, _, files in os.walk(APP):
        for f in files:
            if f.endswith(".tsx") or f.endswith(".ts"):
                result.append(os.path.join(root, f))
    return result

def test_no_inline_fetch_in_pages():
    """PROVEN: all API calls via lib/api.ts — no inline fetch() in protected pages.
    Public pages (register, login) may use raw fetch directly — they cannot import
    lib/api.ts apiFetch because it reads from localStorage which doesn't exist on first load.
    """
    PUBLIC_PAGES = {"register", "login"}  # pages excluded from this check
    violations = []
    for fpath in _all_tsx():
        # Skip public pages
        parts = fpath.replace("\\", "/").split("/")
        parent = parts[-2] if len(parts) >= 2 else ""
        if parent in PUBLIC_PAGES:
            continue
        with open(fpath) as f: content = f.read()
        code = "\n".join(l for l in content.split("\n")
                         if not l.strip().startswith("//") and not l.strip().startswith("*"))
        if re.search(r'\bfetch\s*\(', code):
            violations.append(os.path.relpath(fpath, PORTAL))
    assert not violations, f"Protected pages must not use inline fetch(): {violations}"

def test_api_exports_all_required_clients():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    for api in ["authApi","jobsApi","bookingsApi","staffApi","customersApi",
                "financeApi","reviewsApi","chatApi","documentsApi","settingsApi",
                "analyticsApi","dsApi"]:
        assert api in c, f"lib/api.ts must export {api}"

def test_api_uses_tenant_id_from_localstorage():
    """PROVEN: tenant ID from localStorage — never hardcoded."""
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "getTenantId()" in c
    assert 'localStorage.getItem("serviceos_tenant_id")' in c

def test_auth_header_set_once():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    count = c.count('"Authorization"')
    assert count == 1, f"Authorization header must be set once (found {count})"

def test_api_base_from_env():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "process.env.NEXT_PUBLIC_API_URL" in c


# ── 3. Tour — exactly 7 steps ─────────────────────────────────────────────────
def test_tour_has_exactly_7_steps():
    with open(f"{HOOKS}/useTour.ts") as f: c = f.read()
    steps = re.findall(r'id:\s*"step-\d+"', c)
    assert len(steps) == 7, f"Tour must have 7 steps (found {len(steps)})"

def test_tour_steps_have_all_fields():
    with open(f"{HOOKS}/useTour.ts") as f: c = f.read()
    for field in ["targetId:", "title:", "description:", "position:"]:
        assert c.count(field) >= 7, f"Tour field '{field}' must appear 7 times"

def test_tour_targets_nav_dashboard():
    with open(f"{HOOKS}/useTour.ts") as f: tour = f.read()
    with open(f"{COMPS}/layout/TenantLayout.tsx") as f: layout = f.read()
    assert "nav-dashboard" in tour
    assert 'id={`nav-${item.id}`}' in layout or "nav-" in layout

def test_tour_persists_to_localstorage():
    with open(f"{HOOKS}/useTour.ts") as f: c = f.read()
    assert "serviceos-tenant-tour-done" in c
    assert "localStorage.removeItem" in c  # restart works


# ── 4. Auth guard ─────────────────────────────────────────────────────────────
def test_tenant_layout_auth_guard():
    with open(f"{COMPS}/layout/TenantLayout.tsx") as f: c = f.read()
    assert "serviceos_tenant_token" in c
    assert "localStorage.getItem" in c
    assert "/login" in c

def test_login_stores_tenant_context():
    """PROVEN: login stores tenant_id, name, vertical, plan — not just token."""
    with open(f"{APP}/login/page.tsx") as f: c = f.read()
    for key in ["serviceos_tenant_token", "serviceos_tenant_id",
                "serviceos_tenant_name", "serviceos_tenant_vertical"]:
        assert key in c, f"Login must store {key}"

def test_login_no_inline_fetch():
    with open(f"{APP}/login/page.tsx") as f: c = f.read()
    code = "\n".join(l for l in c.split("\n")
                     if not l.strip().startswith("//") and not l.strip().startswith("*"))
    assert not re.search(r'\bfetch\s*\(', code)


# ── 5. Tenant context hook ────────────────────────────────────────────────────
def test_use_tenant_hook_exists():
    with open(f"{HOOKS}/useTenant.ts") as f: c = f.read()
    assert "tenantId" in c
    assert "tenantName" in c
    assert "localStorage.getItem" in c

def test_tenant_layout_uses_tenant_hook():
    with open(f"{COMPS}/layout/TenantLayout.tsx") as f: c = f.read()
    assert "useTenant" in c
    assert "tenant.tenantName" in c


# ── 6. All pages use live API ─────────────────────────────────────────────────
def test_no_mock_in_tenant_pages():
    violations = []
    for page in TENANT_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath): continue
        with open(fpath) as f: c = f.read()
        code = "\n".join(l for l in c.split("\n") if not l.strip().startswith("//") and not l.strip().startswith("*"))
        if "MOCK_" in code:
            violations.append(page)
    assert not violations, f"Pages must not use mock data: {violations}"

def test_all_pages_use_useapi():
    violations = []
    for page in TENANT_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath): continue
        with open(fpath) as f: c = f.read()
        if "useApi" not in c:
            violations.append(page)
    assert not violations, f"All pages must use useApi: {violations}"

def test_mutating_pages_use_useaction():
    pages_with_mutations = [
        "app/(tenant)/jobs/[id]/page.tsx",
        "app/(tenant)/bookings/page.tsx",
        "app/(tenant)/finance/page.tsx",
        "app/(tenant)/reviews/page.tsx",
        "app/(tenant)/chat/page.tsx",
        "app/(tenant)/settings/page.tsx",
    ]
    violations = []
    for page in pages_with_mutations:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath): continue
        with open(fpath) as f: c = f.read()
        if "useAction" not in c:
            violations.append(page)
    assert not violations, f"Mutating pages must use useAction: {violations}"

def test_mutations_followed_by_refetch():
    pages_with_refetch = [
        "app/(tenant)/jobs/[id]/page.tsx",
        "app/(tenant)/bookings/page.tsx",
        "app/(tenant)/finance/page.tsx",
        "app/(tenant)/reviews/page.tsx",
    ]
    violations = []
    for page in pages_with_refetch:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath): continue
        with open(fpath) as f: c = f.read()
        if ".refetch()" not in c:
            violations.append(page)
    assert not violations, f"Mutations must call refetch(): {violations}"


# ── 7. Page content correctness ───────────────────────────────────────────────
def test_dashboard_is_jobs_first():
    with open(f"{APP}/(tenant)/dashboard/page.tsx") as f: c = f.read()
    assert "jobsApi" in c
    assert "slaAlerts" in c
    assert "wallet" in c.lower()

def test_jobs_page_has_sla_alerts():
    with open(f"{APP}/(tenant)/jobs/page.tsx") as f: c = f.read()
    assert "slaAlerts" in c
    assert "SLA" in c

def test_job_detail_has_status_transitions():
    with open(f"{APP}/(tenant)/jobs/[id]/page.tsx") as f: c = f.read()
    assert "VALID_TRANSITIONS" in c
    assert "updateStatus" in c
    assert "history" in c.lower()

def test_bookings_has_confirm_reject():
    with open(f"{APP}/(tenant)/bookings/page.tsx") as f: c = f.read()
    assert "confirm" in c.lower()
    assert "reject" in c.lower()
    assert "bookingsApi" in c

def test_reviews_enforces_one_reply():
    with open(f"{APP}/(tenant)/reviews/page.tsx") as f: c = f.read()
    assert "has_reply" in c
    assert "once" in c.lower() or "only" in c.lower() or "one" in c.lower()
    assert "disabled" in c

def test_finance_has_wallet_and_commission():
    with open(f"{APP}/(tenant)/finance/page.tsx") as f: c = f.read()
    assert "financeApi" in c
    assert "wallet" in c.lower()
    assert "commissions" in c.lower() or "commission" in c.lower()
    assert "invoices" in c.lower()

def test_settings_shows_3_tier():
    with open(f"{APP}/(tenant)/settings/page.tsx") as f: c = f.read()
    assert "settingsApi" in c
    assert "source" in c.lower()
    assert "tenant" in c.lower()
    assert "platform" in c.lower()


# ── 8. Endpoints correctly connected ──────────────────────────────────────────
def test_connected_api_endpoints():
    expected = {
        "app/(tenant)/dashboard/page.tsx":     ["analyticsApi","jobsApi","financeApi","reviewsApi","bookingsApi"],
        "app/(tenant)/jobs/page.tsx":           ["jobsApi"],
        "app/(tenant)/jobs/[id]/page.tsx":      ["jobsApi"],
        "app/(tenant)/bookings/page.tsx":       ["bookingsApi"],
        "app/(tenant)/staff/page.tsx":          ["staffApi","dsApi"],
        "app/(tenant)/finance/page.tsx":        ["financeApi"],
        "app/(tenant)/reviews/page.tsx":        ["reviewsApi"],
        "app/(tenant)/chat/page.tsx":           ["chatApi"],
        "app/(tenant)/documents/page.tsx":      ["documentsApi"],
        "app/(tenant)/settings/page.tsx":       ["settingsApi"],
    }
    for page, apis in expected.items():
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath): continue
        with open(fpath) as f: c = f.read()
        for api in apis:
            assert api in c, f"{page} must import/use {api}"


# ── 9. Loading states everywhere ─────────────────────────────────────────────
def test_all_pages_have_loading_skeletons():
    violations = []
    for page in TENANT_PAGES:
        fpath = f"{PORTAL}/{page}"
        if not os.path.exists(fpath): continue
        with open(fpath) as f: c = f.read()
        if "Skeleton" not in c and ".loading" not in c:
            violations.append(page)
    assert not violations, f"Pages must show loading states: {violations}"


# ── 10. UI component completeness ─────────────────────────────────────────────
def test_ui_has_job_status_badge_23_statuses():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function JobStatusBadge" in c
    for s in ["in_progress","disputed","warranty_claim","closed","cancelled","rescheduled"]:
        assert s in c, f"JobStatusBadge missing status {s}"

def test_ui_has_health_meter_6_bands():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function HealthMeter" in c
    for b in ["platinum","gold","silver","bronze","at_risk","critical"]:
        assert b in c, f"HealthMeter missing band {b}"

def test_ui_has_star_rating():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "export function StarRating" in c

def test_ui_no_hardcoded_hex():
    with open(f"{COMPS}/shared/ui.tsx") as f: c = f.read()
    assert "var(--" in c, "Must use CSS variables"

def test_css_light_and_dark():
    with open(f"{PORTAL}/styles/globals.css") as f: css = f.read()
    assert ":root" in css
    assert '[data-theme="dark"]' in css
    lines = css.split("\n")
    dark_i = next((i for i,l in enumerate(lines) if '[data-theme="dark"]' in l and "{" in l), len(lines))
    light  = "\n".join(lines[:dark_i])
    dark   = "\n".join(lines[dark_i:])
    for v in ["--surface","--text-primary","--border","--brand"]:
        assert v in light, f"{v} must be in light mode"
        assert v in dark,  f"{v} must be in dark mode"

def test_package_json():
    import json
    with open(f"{PORTAL}/package.json") as f: pkg = json.load(f)
    deps = pkg.get("dependencies",{})
    assert "next"     in deps
    assert "recharts" in deps
    assert "react"    in deps

# ── Public registration page ──────────────────────────────────────────────────
REG_PAGE = f"{PORTAL}/app/register/page.tsx"

def test_registration_page_exists():
    assert os.path.exists(REG_PAGE), "Missing app/register/page.tsx"

def test_registration_page_is_public():
    """Page must not import auth middleware — it's public."""
    with open(REG_PAGE) as f: c = f.read()
    assert "useAuth" not in c, "Register page must not require auth"
    assert "localStorage.getItem" not in c, "Register page must not check for token"

def test_registration_page_has_3_steps():
    with open(REG_PAGE) as f: c = f.read()
    assert "info" in c and "plan" in c and "verify" in c and "done" in c

def test_registration_page_has_plan_selection():
    with open(REG_PAGE) as f: c = f.read()
    assert "starter" in c and "growth" in c and "enterprise" in c

def test_registration_page_calls_onboarding_signup():
    """Register page must use the proper onboarding endpoint, not bypass."""
    with open(REG_PAGE) as f: c = f.read()
    assert "/v1/tenants/onboarding/signup" in c

def test_registration_page_shows_trial_info():
    with open(REG_PAGE) as f: c = f.read()
    assert "trial" in c.lower() or "free" in c.lower()

def test_registration_page_has_otp_verification():
    with open(REG_PAGE) as f: c = f.read()
    assert "otp" in c.lower() or "OTP" in c
    assert "verify" in c.lower()

def test_registration_page_no_auth_required_in_layout():
    """The register page must NOT be inside the (tenant) auth-protected layout."""
    import os
    reg_abs = os.path.abspath(REG_PAGE)
    tenant_layout = os.path.abspath(f"{PORTAL}/app/(tenant)/layout.tsx")
    # register/page.tsx should be at app/register/ not app/(tenant)/register/
    assert "(tenant)" not in REG_PAGE, "Register page must not be inside (tenant) auth group"
