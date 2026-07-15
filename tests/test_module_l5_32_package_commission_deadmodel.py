"""MODULE-L5-32 — two more live call sites still queried the dead
TenantPackagePurchase model (backed by tenant_package_purchases, a table
never migrated) after MODULE-L5-30 fixed the tenant/admin purchase endpoints.

Confirmed genuinely broken:
- delete_package() queried TenantPackagePurchase to block hard-deleting a
  package with existing purchases -- 500'd on every call instead of ever
  blocking anything, since the table doesn't exist.
- _resolve_commission_rate()'s priority-1 lookup ("active_purchase >
  tenant_settings > platform_default") also queried TenantPackagePurchase --
  500'd whenever invoked, so a per-package commission override could never
  be honored; commission rate always silently fell through to tenant
  settings/platform default (or crashed the caller).

Fix: both now query TenantPackageAssignment (joined to ServicePackage for
the actual commission_rate column, which lives on the package definition,
not the assignment row) -- the same real, live table MODULE-L5-30 already
confirmed is fed by admin approval and read by the working status endpoint.
"""
from __future__ import annotations

import inspect

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def _live_lines(src: str) -> list[str]:
    return [l for l in src.splitlines() if not l.strip().startswith("#")]


def test_delete_package_no_longer_queries_the_dead_model():
    from app.engines.package_commerce import service
    src = inspect.getsource(service.PackageCommerceService.delete_package)
    live = _live_lines(src)
    assert not any("TenantPackagePurchase" in l for l in live)
    assert any("TenantPackageAssignment" in l for l in live)


def test_resolve_commission_rate_no_longer_queries_the_dead_model():
    from app.engines.package_commerce import service
    src = inspect.getsource(service.PackageCommerceService._resolve_commission_rate)
    live = _live_lines(src)
    assert not any("TenantPackagePurchase" in l for l in live)
    assert any("TenantPackageAssignment" in l for l in live)


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_delete_package_does_not_500(self):
        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as admin:
            listing = await admin.get("/v1/admin/packages")
            assert listing.status_code == 200
            pkgs = listing.json()["data"].get("packages") or listing.json()["data"].get("items") or []
            if not pkgs:
                pytest.skip("no packages to exercise delete against")
            pkg_id = pkgs[0]["id"]
            r = await admin.delete(f"/v1/admin/packages/{pkg_id}")
            # Either it succeeds (200/204) or is correctly blocked (409) --
            # the only unacceptable outcome is a 500 from the dead table.
            assert r.status_code != 500, r.text
