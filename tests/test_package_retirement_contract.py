"""Current architecture contract for retired tenant subscription packages.

Home Services onboarding is free of plan/package gating. Providers fund a
technician-based security deposit and purchase spendable usage-credit top-ups
through the category finance system after setup.
"""
from pathlib import Path

import httpx


ROOT = Path(__file__).parent.parent


def test_legacy_package_runtime_module_is_removed():
    module_dir = ROOT / "app" / "engines" / "package_commerce"
    assert not any(module_dir.glob("*.py"))


def test_legacy_subscription_runtime_and_pages_are_removed():
    module_dir = ROOT / "app" / "engines" / "subscription"
    assert not any(module_dir.glob("*.py"))
    assert not (ROOT / "app" / "engines" / "invoice_payment" / "subscription_service.py").exists()
    assert not (
        ROOT
        / "frontend"
        / "tenant-portal"
        / "app"
        / "(tenant)"
        / "provider"
        / "subscription-status"
        / "page.tsx"
    ).exists()
    assert not (
        ROOT / "frontend" / "super-admin" / "app" / "admin" / "packages" / "page.tsx"
    ).exists()


def test_main_mounts_only_the_no_payment_signup_router():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "public_registration.signup_router" in source
    assert "public_registration.router" not in source


def test_engine_resolution_has_no_package_layer():
    source = (ROOT / "app" / "engines" / "engine_mgmt" / "service.py").read_text(
        encoding="utf-8"
    )
    method = source.split("async def get_tenant_effective_engines", 1)[1]
    method = method.split("async def create_tenant_override", 1)[0]
    assert "package_id" not in method
    assert "PackageEngineEntitlement" not in method
    assert 'source = "category"' in method
    assert 'source = "tenant_override"' in method
    assert "runtime_registry.all()" in method
    assert '"legacy_package_entitlements_used": False' in method


def test_home_services_template_uses_only_canonical_runtime_engine_keys():
    source = (ROOT / "app" / "engines" / "engine_mgmt" / "service.py").read_text(
        encoding="utf-8"
    )
    template = source.split('"home_services_default":', 1)[1].split(
        '"real_estate_default":', 1
    )[0]
    for retired_alias in (
        "auth_iam",
        "finance",
        "package_credit",
        "customer_svc_credit",
        "job_dispatch",
        "media_vault",
        "review_rating",
    ):
        assert f'"{retired_alias}"' not in template
    assert '"platform_commerce"' in template
    assert '"dispatch"' in template


def test_live_route_graph_uses_signup_and_category_finance_only():
    response = httpx.get("http://127.0.0.1:8000/openapi.json", timeout=60)
    response.raise_for_status()
    paths = set(response.json()["paths"])

    retired_prefixes = (
        "/v1/admin/packages",
        "/v1/tenant/packages",
        "/v1/public/packages",
        "/v1/public/register",
        "/v1/subscriptions",
        "/v1/provider/subscription-status",
        "/v1/admin/subscription-status",
        "/v1/tenants/{tenant_id}/plan",
        "/v1/tenants/{tenant_id}/trial/convert",
        "/v1/tenants/{tenant_id}/billing/invoices",
        "/v1/tenants/{tenant_id}/billing/dunning",
        "/v1/admin/tenants/{tenant_id}/change-plan",
    )
    assert not any(path.startswith(retired_prefixes) for path in paths)
    assert "/v1/public/signup/owner-account" in paths
    assert "/v1/public/signup/complete" in paths
    assert "/v1/admin/engines/tenants/{tenant_id}/effective" in paths
    assert "/v1/tenant/engines/effective" in paths
    assert "/v1/tenant/home-services/finance/credit-packages" in paths
    assert "/v1/tenant/home-services/activation/credit-package/order" in paths


def test_live_tenant_effective_engine_policy_is_canonical():
    login = httpx.post(
        "http://127.0.0.1:8000/v1/auth/login",
        json={"email": "provider@serviceos.in", "password": "Password123!"},
        timeout=60,
    )
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    response = httpx.get(
        "http://127.0.0.1:8000/v1/tenant/engines/effective",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()["data"]

    assert data["category"]["name"] == "Home Services"
    assert data["policy"] == {
        "configured": True,
        "source": "category_matrix",
        "legacy_package_entitlements_used": False,
    }
    keys = [row["engine_key"] for row in data["engines"]]
    assert len(keys) == len(set(keys))
    assert "platform_commerce" in keys
    assert not set(keys).intersection({
        "finance", "package_credit", "customer_svc_credit", "job_dispatch",
    })
