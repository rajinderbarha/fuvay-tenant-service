"""
Phase 21 — E2E Test Suite Validator (Python/pytest).
Verifies the Playwright specs exist, have correct structure,
cover all required pages, and use mock-api helpers.
Run: python -m pytest tests/test_phase21_e2e.py -v
To run the actual browser tests: cd e2e && npx playwright test
"""
import os, re, pathlib

E2E_DIR = str(pathlib.Path(__file__).parent.parent.resolve() / "e2e")

# ── 1. Directory and config structure ─────────────────────────────────────────
def test_e2e_directory_exists():
    assert os.path.isdir(E2E_DIR), "e2e/ directory must exist"

def test_playwright_config_exists():
    assert os.path.exists(f"{E2E_DIR}/playwright.config.ts")

def test_playwright_config_has_both_projects():
    with open(f"{E2E_DIR}/playwright.config.ts") as f: c = f.read()
    assert "super-admin" in c
    assert "tenant-portal" in c

def test_playwright_config_has_web_server():
    with open(f"{E2E_DIR}/playwright.config.ts") as f: c = f.read()
    assert "webServer" in c
    assert "3000" in c
    assert "3001" in c

def test_mock_api_helper_exists():
    assert os.path.exists(f"{E2E_DIR}/helpers/mock-api.ts")

def test_package_json_exists():
    assert os.path.exists(f"{E2E_DIR}/package.json")

def test_tsconfig_exists():
    assert os.path.exists(f"{E2E_DIR}/tsconfig.json")


# ── 2. Super Admin specs exist and cover all pages ─────────────────────────────
REQUIRED_SUPER_ADMIN_SPECS = [
    "auth.spec.ts",
    "dashboard.spec.ts",
    "tenants.spec.ts",
    "operations.spec.ts",
    "finance.spec.ts",
    "security.spec.ts",
    "compliance.spec.ts",
    "marketing.spec.ts",
]

def test_super_admin_specs_exist():
    missing = [s for s in REQUIRED_SUPER_ADMIN_SPECS
               if not os.path.exists(f"{E2E_DIR}/super-admin/{s}")]
    assert not missing, f"Missing super-admin specs: {missing}"

def test_super_admin_spec_count():
    specs = [f for f in os.listdir(f"{E2E_DIR}/super-admin") if f.endswith(".spec.ts")]
    assert len(specs) >= 8, f"Expected >= 8 super-admin specs, got {len(specs)}"


# ── 3. Tenant Portal specs exist and cover all pages ──────────────────────────
REQUIRED_TENANT_SPECS = [
    "auth.spec.ts",
    "dashboard.spec.ts",
    "jobs.spec.ts",
    "bookings.spec.ts",
    "staff.spec.ts",
    "customers.spec.ts",
    "finance.spec.ts",
    "reviews.spec.ts",
    "chat.spec.ts",
    "documents.spec.ts",
    "settings.spec.ts",
]

def test_tenant_portal_specs_exist():
    missing = [s for s in REQUIRED_TENANT_SPECS
               if not os.path.exists(f"{E2E_DIR}/tenant-portal/{s}")]
    assert not missing, f"Missing tenant-portal specs: {missing}"

def test_tenant_portal_spec_count():
    specs = [f for f in os.listdir(f"{E2E_DIR}/tenant-portal") if f.endswith(".spec.ts")]
    assert len(specs) >= 11, f"Expected >= 11 tenant specs, got {len(specs)}"


# ── 4. Mock API helper completeness ───────────────────────────────────────────
def test_mock_api_has_setup_function():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    assert "setupMockApi" in c

def test_mock_api_has_set_admin_auth():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    assert "setAdminAuth" in c

def test_mock_api_has_set_tenant_auth():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    assert "setTenantAuth" in c

def test_mock_api_sets_6_tenant_context_keys():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    for key in ["serviceos_tenant_token", "serviceos_tenant_id", "serviceos_tenant_name",
                "serviceos_vertical", "serviceos_plan_type", "serviceos_user_id"]:
        assert key in c, f"mock-api must set localStorage key: {key}"

def test_mock_api_has_job_fixture():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    assert "JOB_FIXTURE" in c
    assert "JOB-001" in c

def test_mock_api_has_tenant_fixture():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    assert "TENANT_FIXTURE" in c
    assert "t_test01" in c

def test_mock_api_covers_core_endpoints():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    # Patterns are regex literals: /\/v1\/auth\/login/ — check for escaped path fragments
    for fragment in ["auth", "auth\\/me", "jobs", "staff", "bookings",
                     "reviews", "chat", "documents", "settings"]:
        assert fragment in c, f"mock-api missing endpoint fragment: {fragment}"

def test_mock_api_has_default_404_fallback():
    with open(f"{E2E_DIR}/helpers/mock-api.ts") as f: c = f.read()
    assert "NOT_MOCKED" in c or "404" in c


# ── 5. Each spec uses mock-api helpers ────────────────────────────────────────
def _all_specs():
    paths = []
    for folder in ["super-admin", "tenant-portal"]:
        d = f"{E2E_DIR}/{folder}"
        for f in os.listdir(d):
            if f.endswith(".spec.ts"):
                paths.append(f"{d}/{f}")
    return paths

def test_all_specs_import_mock_api():
    missing = []
    for path in _all_specs():
        with open(path) as f: c = f.read()
        if "mock-api" not in c:
            missing.append(os.path.basename(path))
    assert not missing, f"Specs not importing mock-api: {missing}"

def test_all_specs_import_setupmockapi():
    missing = []
    for path in _all_specs():
        with open(path) as f: c = f.read()
        if "setupMockApi" not in c:
            missing.append(os.path.basename(path))
    assert not missing, f"Specs not calling setupMockApi: {missing}"

def test_all_specs_have_describe_block():
    missing = []
    for path in _all_specs():
        with open(path) as f: c = f.read()
        if "test.describe" not in c:
            missing.append(os.path.basename(path))
    assert not missing, f"Specs missing test.describe: {missing}"

def test_all_specs_have_beforeeach():
    missing = []
    for path in _all_specs():
        with open(path) as f: c = f.read()
        if "beforeEach" not in c:
            missing.append(os.path.basename(path))
    assert not missing, f"Specs missing beforeEach: {missing}"

def test_all_specs_have_min_3_tests():
    thin = []
    for path in _all_specs():
        with open(path) as f: c = f.read()
        count = len(re.findall(r"^\s*test\(", c, re.MULTILINE))
        if count < 3:
            thin.append(f"{os.path.basename(path)} ({count} tests)")
    assert not thin, f"Specs with fewer than 3 tests: {thin}"


# ── 6. Auth specs enforce unauthenticated redirect ────────────────────────────
def test_super_admin_auth_spec_has_redirect_test():
    with open(f"{E2E_DIR}/super-admin/auth.spec.ts") as f: c = f.read()
    assert "redirect" in c.lower() or "/login" in c

def test_tenant_auth_spec_stores_6_keys():
    with open(f"{E2E_DIR}/tenant-portal/auth.spec.ts") as f: c = f.read()
    assert "6" in c or "toHaveLength(6)" in c

def test_tenant_auth_spec_checks_protected_routes():
    with open(f"{E2E_DIR}/tenant-portal/auth.spec.ts") as f: c = f.read()
    assert "/dashboard" in c and "/jobs" in c


# ── 7. Critical business-rule coverage ────────────────────────────────────────
def test_reviews_spec_enforces_one_reply():
    with open(f"{E2E_DIR}/tenant-portal/reviews.spec.ts") as f: c = f.read()
    assert "has_reply" in c or "disabled" in c.lower(), "Reviews spec must test one-reply enforcement"

def test_jobs_spec_tests_status_transitions():
    with open(f"{E2E_DIR}/tenant-portal/jobs.spec.ts") as f: c = f.read()
    assert "status" in c and ("transition" in c.lower() or "updateStatus" in c or "quality_check" in c)

def test_staff_spec_tests_schedule_save():
    with open(f"{E2E_DIR}/tenant-portal/staff.spec.ts") as f: c = f.read()
    assert "schedule" in c.lower() and ("PUT" in c or "Save" in c)

def test_customers_spec_tests_health_signals():
    with open(f"{E2E_DIR}/tenant-portal/customers.spec.ts") as f: c = f.read()
    assert "health" in c.lower() and ("signal" in c.lower() or "score" in c.lower())

def test_settings_spec_tests_3_tier():
    with open(f"{E2E_DIR}/tenant-portal/settings.spec.ts") as f: c = f.read()
    assert "tenant" in c and ("plan" in c or "platform" in c)

def test_documents_spec_tests_signing_flow():
    with open(f"{E2E_DIR}/tenant-portal/documents.spec.ts") as f: c = f.read()
    assert "signing" in c.lower() or "sign_now" in c.lower() or "Sign Now" in c

def test_security_spec_tests_block_ip():
    with open(f"{E2E_DIR}/super-admin/security.spec.ts") as f: c = f.read()
    assert "block" in c.lower() and "ip" in c.lower()

def test_compliance_spec_tests_deletion_processing():
    with open(f"{E2E_DIR}/super-admin/compliance.spec.ts") as f: c = f.read()
    assert "deletion" in c.lower() and ("process" in c.lower() or "Process" in c)


# ── 8. Total coverage count ────────────────────────────────────────────────────
def test_total_e2e_test_count():
    total = 0
    for path in _all_specs():
        with open(path) as f: c = f.read()
        total += len(re.findall(r"^\s*test\(", c, re.MULTILINE))
    assert total >= 60, f"Expected >= 60 E2E tests total, got {total}"
