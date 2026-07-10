"""
Version Audit Tests — confirms all packages are updated to June 2026 latest.
Run: python -m pytest tests/test_versions.py -v
"""
import json, re, os, pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())

# ── Helper ─────────────────────────────────────────────────────────────────────
def req():
    with open(f"{BASE}/requirements.txt", encoding="utf-8") as f:
        return f.read()

def pkg(path):
    with open(f"{BASE}/{path}", encoding="utf-8") as f:
        return json.load(f)

def workflow(name):
    with open(f"{BASE}/.github/workflows/{name}", encoding="utf-8") as f:
        return f.read()

def dockerfile():
    with open(f"{BASE}/Dockerfile", encoding="utf-8") as f:
        return f.read()

def compose(name="docker-compose.yml"):
    with open(f"{BASE}/{name}", encoding="utf-8") as f:
        return f.read()

# ── 1. Backend Python ─────────────────────────────────────────────────────────
def test_fastapi_version():
    assert "fastapi==0.138.0" in req()

def test_uvicorn_version():
    assert "uvicorn[standard]==0.49.0" in req()

def test_alembic_version():
    assert "alembic==1.18.5" in req()

def test_pydantic_version():
    assert "pydantic==2.13.4" in req()

def test_pydantic_settings_version():
    assert "pydantic-settings==2.9.1" in req()

def test_sqlalchemy_version():
    assert "sqlalchemy[asyncio]==2.0.41" in req()

def test_asyncpg_version():
    assert "asyncpg==0.31.0" in req()

def test_redis_version():
    assert "redis[hiredis]==5.3.0" in req()

def test_structlog_version():
    assert "structlog==25.3.0" in req()

def test_httpx_version():
    assert "httpx==0.28.1" in req() or "httpx==0.29.0" in req()

def test_pytest_version():
    assert "pytest==8.4.0" in req()

def test_pytest_asyncio_version():
    assert "pytest-asyncio==0.26.0" in req()

def test_sentry_version():
    assert "sentry-sdk[fastapi]==2.26.0" in req()

def test_prometheus_version():
    assert "prometheus-fastapi-instrumentator==8.0.0" in req()

# ── 2. Frontend portals ───────────────────────────────────────────────────────
def test_super_admin_nextjs():
    assert pkg("frontend/super-admin/package.json")["dependencies"]["next"] == "16.2.9"

def test_super_admin_react():
    assert pkg("frontend/super-admin/package.json")["dependencies"]["react"] == "19.2.0"

def test_super_admin_typescript():
    assert pkg("frontend/super-admin/package.json")["devDependencies"]["typescript"] == "5.8.3"

def test_tenant_portal_nextjs():
    assert pkg("frontend/tenant-portal/package.json")["dependencies"]["next"] == "16.2.9"

def test_tenant_portal_react():
    assert pkg("frontend/tenant-portal/package.json")["dependencies"]["react"] == "19.2.0"

def test_e2e_playwright():
    assert pkg("e2e/package.json")["devDependencies"]["@playwright/test"] == "1.52.0"

def test_e2e_typescript():
    assert pkg("e2e/package.json")["devDependencies"]["typescript"] == "5.8.3"

# ── 3. Mobile apps — Expo SDK 56 ─────────────────────────────────────────────
def test_staff_expo_sdk():
    p = pkg("mobile/staff-app/package.json")
    assert "56.0" in p["dependencies"]["expo"]

def test_staff_react_native():
    p = pkg("mobile/staff-app/package.json")
    assert p["dependencies"]["react-native"] == "0.85.0"

def test_staff_react():
    p = pkg("mobile/staff-app/package.json")
    assert p["dependencies"]["react"] == "19.2.0"

def test_staff_react_navigation_v7():
    p = pkg("mobile/staff-app/package.json")
    assert p["dependencies"]["@react-navigation/native"].startswith("^7")

def test_staff_typescript():
    p = pkg("mobile/staff-app/package.json")
    assert "5.8" in p["devDependencies"]["typescript"]

def test_customer_expo_sdk():
    p = pkg("mobile/customer-app/package.json")
    assert "56.0" in p["dependencies"]["expo"]

def test_customer_react_native():
    p = pkg("mobile/customer-app/package.json")
    assert p["dependencies"]["react-native"] == "0.85.0"

def test_customer_react():
    p = pkg("mobile/customer-app/package.json")
    assert p["dependencies"]["react"] == "19.2.0"

def test_customer_react_navigation_v7():
    p = pkg("mobile/customer-app/package.json")
    assert p["dependencies"]["@react-navigation/native"].startswith("^7")

def test_staff_app_json_sdk_version():
    with open(f"{BASE}/mobile/staff-app/app.json", encoding="utf-8") as f:
        a = json.load(f)
    assert a["expo"]["sdkVersion"] == "56.0.0"

def test_customer_app_json_sdk_version():
    with open(f"{BASE}/mobile/customer-app/app.json", encoding="utf-8") as f:
        a = json.load(f)
    assert a["expo"]["sdkVersion"] == "56.0.0"

# ── 4. Docker images ──────────────────────────────────────────────────────────
def test_dockerfile_python_313():
    assert "python:3.13-slim" in dockerfile()
    assert "python:3.12" not in dockerfile()

def test_compose_postgres_pg17():
    assert "pgvector/pgvector:pg17" in compose()
    assert "pg16" not in compose()

def test_compose_prod_redis8():
    assert "redis:8-alpine" in compose("docker-compose.prod.yml")
    assert "redis:7" not in compose("docker-compose.prod.yml")

def test_compose_prod_nginx_129():
    assert "nginx:1.29-alpine" in compose("docker-compose.prod.yml")

def test_compose_prod_prometheus_v3():
    assert "prom/prometheus:v3.4.0" in compose("docker-compose.prod.yml")

def test_compose_prod_grafana_12():
    assert "grafana/grafana:12.0.0" in compose("docker-compose.prod.yml")

# ── 5. GitHub Actions ─────────────────────────────────────────────────────────
def test_test_yml_python_313():
    w = workflow("test.yml")
    assert '3.13' in w
    assert '3.12' not in w

def test_test_yml_node_22():
    w = workflow("e2e.yml")
    assert "22" in w

def test_build_yml_push_action_v6():
    w = workflow("build.yml")
    assert "docker/build-push-action@v6" in w

def test_build_yml_metadata_action_v6():
    w = workflow("build.yml")
    assert "docker/metadata-action@v6" in w

def test_test_yml_codecov_v5():
    w = workflow("test.yml")
    assert "codecov/codecov-action@v5" in w
