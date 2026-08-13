"""P0 Sidebar Duplicate Menu Cleanup + Correct Grouping Fix.

Home Services previously showed Brands/Brand Requests/Pricing Tiers/City-Zip
Mapping/Pricing Rules both as global static sidebar items AND again inside its
own vertical catalog section (identical routes rendered twice). Migration 096
soft-disables the redundant home_services `vertical_catalog_modules` rows;
AdminLayout.tsx no longer hardcodes global Brands/Brand Requests items; and
Types & Brands gained a "Brand Requests" tab so nothing was lost, just
consolidated to one canonical location.
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
ADMIN_PASS = "Password123!"

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions", "096_navigation_duplicate_cleanup.py")
ADMIN_LAYOUT = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")
TYPES_BRANDS_PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin", "app", "admin", "types-brands", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def client(token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {token}"}, timeout=30) as c:
        yield c


pytestmark = pytest.mark.anyio


# ═════════════════════════════════════════════════════════════════════════════
# Static file checks
# ═════════════════════════════════════════════════════════════════════════════
class TestFiles:
    def test_migration_exists(self):
        assert os.path.exists(MIGRATION)

    def test_migration_revision_chain(self):
        src = _read(MIGRATION)
        assert 'revision = "096"' in src
        assert 'down_revision = "095"' in src

    def test_migration_disables_all_five_duplicate_keys(self):
        src = _read(MIGRATION)
        for key in ["brands", "brand_requests", "pricing_tiers", "location_mapping", "pricing_rules"]:
            assert f'"{key}"' in src or f"'{key}'" in src

    def test_admin_layout_has_no_global_brands_item(self):
        src = _read(ADMIN_LAYOUT)
        assert '{ id: "brands",          href: "/admin/brands"' not in src
        assert '{ id: "brand-requests",  href: "/admin/brand-requests"' not in src

    def test_types_brands_page_has_brand_requests_tab(self):
        src = _read(TYPES_BRANDS_PAGE)
        assert '"brand-requests"' in src
        assert "BrandRequestsTab" in src
        assert 'label:"Brand Requests"' in src or 'label: "Brand Requests"' in src


# ═════════════════════════════════════════════════════════════════════════════
# Live resolver — no duplicates
# ═════════════════════════════════════════════════════════════════════════════
class TestNoDuplicates:
    async def test_home_services_excludes_brand_and_pricing_modules(self, client):
        r = await client.get("/v1/admin/catalog/navigation/effective-menu")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        hs = next(v for v in d["verticals"] if v["vertical_key"] == "home_services")
        module_keys = {m["key"] for m in hs["modules"]}
        for dup in ["brands", "brand_requests", "pricing_tiers", "location_mapping", "pricing_rules"]:
            assert dup not in module_keys, f"{dup} should not appear under Home Services (duplicate)"

    async def test_home_services_keeps_canonical_items(self, client):
        r = await client.get("/v1/admin/catalog/navigation/effective-menu")
        d = r.json()["data"]
        hs = next(v for v in d["verticals"] if v["vertical_key"] == "home_services")
        module_keys = {m["key"] for m in hs["modules"]}
        for keep in ["categories", "service_groups", "master_services", "types_brands",
                     "checklist_templates"]:
            assert keep in module_keys, f"{keep} should still be present under Home Services"
        # MODULE-L5-56 retired these as standalone nav entries (Job-Type
        # Blueprint consolidation) -- Options & Add-ons and Problems &
        # Questions are now configured only per exact Job Type inside
        # Catalog Workspace. Migration 173 closed the dynamic-module gap
        # that ticket's own test file explicitly deferred.
        for retired in ["service_options", "issue_types", "service_setup"]:
            assert retired not in module_keys, f"{retired} should be retired under Home Services"

    async def test_seed_idempotent_no_duplicates_on_rerun(self, client):
        """Re-fetching the effective menu (equivalent to re-running the resolver) must not
        re-introduce duplicates — the disable is a persisted DB state, not a one-time seed."""
        r1 = await client.get("/v1/admin/catalog/navigation/effective-menu")
        r2 = await client.get("/v1/admin/catalog/navigation/effective-menu")
        hs1 = next(v for v in r1.json()["data"]["verticals"] if v["vertical_key"] == "home_services")
        hs2 = next(v for v in r2.json()["data"]["verticals"] if v["vertical_key"] == "home_services")
        assert {m["key"] for m in hs1["modules"]} == {m["key"] for m in hs2["modules"]}
        assert "brands" not in {m["key"] for m in hs2["modules"]}
