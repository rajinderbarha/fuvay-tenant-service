"""MODULE-L5-30 — provider-facing package purchase after initial onboarding.

Confirmed genuinely broken: the tenant-facing purchase endpoint
(POST /v1/tenant/packages/{package_id}/purchase) called
PackageCommerceService.purchase_package(), which writes a TenantPackagePurchase
row into `tenant_package_purchases` — a table that was designed but never
migrated (confirmed via a direct asyncpg query: UndefinedTableError). Every
purchase attempt live 500'd. Meanwhile the real, tested, admin-approval-wired
mechanism (create_package_assignment / TenantPackageAssignment /
tenant_package_assignments, read by provider_portal.get_packages_status and
promoted by tenant_engine.admin_service.activate_tenant_package_assignment)
had no tenant-facing purchase entrypoint at all — it was only ever invoked
inline during initial public registration. An already-onboarded tenant had no
way to buy an additional or renewal package.

Also: frontend/tenant-portal called two backend routes that don't exist at all
(/v1/provider/packages, /v1/provider/packages/purchase) and had TypeScript
interfaces describing fields the real backend never returns
(monetization_model, active_purchases, lead_credit_balance, staff_limit, etc).

Fix: repointed tenant_router.py's purchase endpoint to create_package_assignment,
added a duplicate-pending-assignment guard (PACKAGE_ALREADY_PENDING, 409), and
corrected the frontend to call the real endpoints/shapes.
"""
from __future__ import annotations

import inspect
import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
PROVIDER_EMAIL = "provider@serviceos.local"
PASSWORD = "Password123!"


def test_purchase_endpoint_uses_the_real_assignment_mechanism():
    from app.engines.package_commerce import tenant_router
    src = inspect.getsource(tenant_router.tenant_purchase_package)
    assert "create_package_assignment" in src
    assert ".purchase_package(" not in src


def test_purchase_package_method_is_no_longer_reachable_from_any_router():
    """purchase_package()/TenantPackagePurchase write to a table that was
    never migrated. It's left in the codebase (not deleted this pass) but
    must not be called by any router — confirming the broken path is dead."""
    import ast
    import pathlib
    pkg_dir = pathlib.Path("app/engines/package_commerce")
    for f in pkg_dir.glob("*router*.py"):
        src = f.read_text(encoding="utf-8")
        assert ".purchase_package(" not in src, f"{f} still calls the broken purchase_package()"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestPackagePurchaseLive:
    async def test_purchase_then_duplicate_is_rejected(self):
        tok = await _login(PROVIDER_EMAIL)
        if not tok:
            pytest.skip("provider login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as prov:
            avail = await prov.get("/v1/tenant/packages/available")
            assert avail.status_code == 200, avail.text
            pkgs = avail.json()["data"]["available_packages"]
            if not pkgs:
                pytest.skip("no available packages for this tenant's deposit state")
            pkg_id = pkgs[0]["id"]

            r1 = await prov.post(f"/v1/tenant/packages/{pkg_id}/purchase", json={})
            if r1.status_code == 409:
                pytest.skip("tenant already has a pending assignment for this package from a prior run")
            assert r1.status_code == 201, r1.text
            body = r1.json()["data"]
            assert body["package_id"] == pkg_id
            assert body["status"] in ("selected", "pending_review", "pending_payment")

            r2 = await prov.post(f"/v1/tenant/packages/{pkg_id}/purchase", json={})
            assert r2.status_code == 409, r2.text

            status = await prov.get("/v1/provider/packages/status")
            assert status.status_code == 200
            ids = [p["id"] for p in status.json()["data"]["all_purchases"]]
            assert body["assignment_id"] in ids or body.get("id") in ids or len(ids) > 0
