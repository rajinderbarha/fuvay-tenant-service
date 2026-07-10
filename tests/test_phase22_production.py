"""
Phase 22 — Production Hardening — Structural Tests (42 tests).
Verifies: GitHub Actions, observability, security, docker config, READMEs, EAS.
"""
import os, re, pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())

# ── 1. GitHub Actions ─────────────────────────────────────────────────────────
WORKFLOWS = [
    ".github/workflows/test.yml",
    ".github/workflows/build.yml",
    ".github/workflows/deploy.yml",
    ".github/workflows/e2e.yml",
]

def test_github_workflows_exist():
    missing = [f for f in WORKFLOWS if not os.path.exists(f"{BASE}/{f}")]
    assert not missing, f"Missing workflows: {missing}"

def test_test_workflow_runs_all_suites():
    with open(f"{BASE}/.github/workflows/test.yml", encoding="utf-8") as f: c = f.read()
    for suite in ["backend", "design-system", "super-admin", "tenant-portal", "mobile-apps"]:
        assert suite in c, f"test.yml missing job: {suite}"

def test_test_workflow_has_postgres_and_redis_services():
    with open(f"{BASE}/.github/workflows/test.yml", encoding="utf-8") as f: c = f.read()
    assert "postgres" in c and "redis" in c

def test_build_workflow_uses_ghcr():
    with open(f"{BASE}/.github/workflows/build.yml", encoding="utf-8") as f: c = f.read()
    assert "ghcr.io" in c

def test_build_workflow_multi_arch():
    with open(f"{BASE}/.github/workflows/build.yml", encoding="utf-8") as f: c = f.read()
    assert "linux/amd64" in c and "linux/arm64" in c

def test_deploy_workflow_runs_migrations():
    with open(f"{BASE}/.github/workflows/deploy.yml", encoding="utf-8") as f: c = f.read()
    assert "alembic upgrade head" in c

def test_deploy_workflow_has_health_check():
    with open(f"{BASE}/.github/workflows/deploy.yml", encoding="utf-8") as f: c = f.read()
    assert "/health" in c

def test_e2e_workflow_installs_playwright():
    with open(f"{BASE}/.github/workflows/e2e.yml", encoding="utf-8") as f: c = f.read()
    assert "playwright install" in c

def test_e2e_workflow_uploads_report():
    with open(f"{BASE}/.github/workflows/e2e.yml", encoding="utf-8") as f: c = f.read()
    assert "upload-artifact" in c

# ── 2. Observability ──────────────────────────────────────────────────────────
def test_observability_module_exists():
    assert os.path.exists(f"{BASE}/app/observability.py")

def test_observability_has_prometheus():
    with open(f"{BASE}/app/observability.py", encoding="utf-8") as f: c = f.read()
    assert "prometheus" in c.lower()
    assert "setup_prometheus" in c

def test_observability_has_sentry():
    with open(f"{BASE}/app/observability.py", encoding="utf-8") as f: c = f.read()
    assert "sentry" in c.lower()
    assert "setup_sentry" in c

def test_sentry_has_pii_scrubber():
    with open(f"{BASE}/app/observability.py", encoding="utf-8") as f: c = f.read()
    assert "_scrub_pii" in c or "scrub" in c
    assert "password" in c or "token" in c

def test_observability_wired_in_main():
    with open(f"{BASE}/app/main.py", encoding="utf-8") as f: c = f.read()
    assert "setup_prometheus" in c or "observability" in c

def test_prometheus_in_requirements():
    with open(f"{BASE}/requirements.txt", encoding="utf-8") as f: c = f.read()
    assert "prometheus" in c

def test_sentry_in_requirements():
    with open(f"{BASE}/requirements.txt", encoding="utf-8") as f: c = f.read()
    assert "sentry" in c

# ── 3. PII Masking ────────────────────────────────────────────────────────────
def test_pii_filter_module_exists():
    assert os.path.exists(f"{BASE}/app/core/pii_filter.py")

def test_pii_filter_masks_sensitive_keys():
    with open(f"{BASE}/app/core/pii_filter.py", encoding="utf-8") as f: c = f.read()
    for key in ["password", "token", "phone", "email", "otp"]:
        assert key in c, f"PII filter missing key: {key}"

def test_pii_filter_masks_api_key_patterns():
    with open(f"{BASE}/app/core/pii_filter.py", encoding="utf-8") as f: c = f.read()
    assert "sk-" in c or "Bearer" in c, "Must mask API key patterns"

# ── 4. Security ────────────────────────────────────────────────────────────────
def test_security_headers_middleware_exists():
    with open(f"{BASE}/app/middleware.py", encoding="utf-8") as f: c = f.read()
    assert "SecurityHeadersMiddleware" in c

def test_owasp_headers_present():
    with open(f"{BASE}/app/middleware.py", encoding="utf-8") as f: c = f.read()
    for header in ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection",
                   "Referrer-Policy", "Permissions-Policy", "Strict-Transport-Security"]:
        assert header in c, f"Missing OWASP header: {header}"

def test_rate_limiting_configured():
    with open(f"{BASE}/app/core/security.py", encoding="utf-8") as f: c = f.read()
    assert "RATE_LIMITS" in c
    assert "auth:login" in c

def test_idempotency_middleware_exists():
    with open(f"{BASE}/app/middleware.py", encoding="utf-8") as f: c = f.read()
    assert "IdempotencyMiddleware" in c

def test_health_endpoint_exists():
    assert os.path.exists(f"{BASE}/app/engines/health_router.py")
    with open(f"{BASE}/app/engines/health_router.py", encoding="utf-8") as f: c = f.read()
    assert "/health" in c

# ── 5. Docker ─────────────────────────────────────────────────────────────────
def test_dockerfile_is_multistage():
    with open(f"{BASE}/Dockerfile", encoding="utf-8") as f: c = f.read()
    assert c.count("FROM ") >= 2, "Dockerfile must be multi-stage"

def test_dockerfile_has_nonroot_user():
    with open(f"{BASE}/Dockerfile", encoding="utf-8") as f: c = f.read()
    assert "USER serviceos" in c or "useradd" in c or "adduser" in c

def test_dockerfile_has_healthcheck():
    with open(f"{BASE}/Dockerfile", encoding="utf-8") as f: c = f.read()
    assert "HEALTHCHECK" in c

def test_docker_compose_has_all_services():
    with open(f"{BASE}/docker-compose.yml", encoding="utf-8") as f: c = f.read()
    for svc in ["postgres", "redis", "api"]:
        assert svc in c, f"docker-compose missing service: {svc}"

def test_docker_compose_prod_exists():
    assert os.path.exists(f"{BASE}/docker-compose.prod.yml")

def test_docker_compose_prod_has_nginx_prometheus_grafana():
    with open(f"{BASE}/docker-compose.prod.yml", encoding="utf-8") as f: c = f.read()
    for svc in ["nginx", "prometheus", "grafana"]:
        assert svc in c, f"prod compose missing: {svc}"

def test_env_example_exists():
    assert os.path.exists(f"{BASE}/.env.example")

def test_env_example_has_all_key_vars():
    with open(f"{BASE}/.env.example", encoding="utf-8") as f: c = f.read()
    for var in ["DATABASE_URL", "REDIS_URL", "SECRET_KEY",
                "DEEPSEEK_API_KEY", "SENTRY_DSN", "APP_ENV"]:
        assert var in c, f".env.example missing: {var}"

# ── 6. Documentation ──────────────────────────────────────────────────────────
README_FILES = [
    "README.md",
    "app/README.md",
    "frontend/super-admin/README.md",
    "frontend/tenant-portal/README.md",
    "mobile/staff-app/README.md",
    "mobile/customer-app/README.md",
]

def test_all_readme_files_exist():
    missing = [f for f in README_FILES if not os.path.exists(f"{BASE}/{f}")]
    assert not missing, f"Missing READMEs: {missing}"

def test_root_readme_has_architecture():
    with open(f"{BASE}/README.md", encoding="utf-8") as f: c = f.read()
    assert "Architecture" in c or "architecture" in c

def test_root_readme_has_quick_start():
    with open(f"{BASE}/README.md", encoding="utf-8") as f: c = f.read()
    assert "Quick Start" in c or "Getting Started" in c

def test_docs_architecture_exists():
    assert os.path.exists(f"{BASE}/docs/architecture.md")

def test_docs_architecture_has_engine_map():
    with open(f"{BASE}/docs/architecture.md", encoding="utf-8") as f: c = f.read()
    assert "Auth Engine" in c
    assert "Dispatch Engine" in c
    assert "AI Chat Engine" in c

# ── 7. Mobile build config ────────────────────────────────────────────────────
def test_eas_json_in_staff_app():
    assert os.path.exists(f"{BASE}/mobile/staff-app/eas.json")

def test_eas_json_in_customer_app():
    assert os.path.exists(f"{BASE}/mobile/customer-app/eas.json")

def test_eas_has_dev_preview_prod_profiles():
    for app in ["staff-app", "customer-app"]:
        with open(f"{BASE}/mobile/{app}/eas.json", encoding="utf-8") as f: c = f.read()
        for profile in ["development", "preview", "production"]:
            assert profile in c, f"eas.json ({app}) missing profile: {profile}"

def test_monitoring_prometheus_config_exists():
    assert os.path.exists(f"{BASE}/monitoring/prometheus.yml")
