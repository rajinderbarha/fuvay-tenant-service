"""MODULE-L5-43 (part 2) — super-admin's "Bulk Re-evaluate" bookability
action called a route that doesn't exist, and the provider list's total count
was read from a field the backend never returns.

adminBookabilityApi.bulkRefresh called POST /v1/admin/bookability/bulk-refresh
-- no such route exists; the backend only has a per-tenant refresh
(/v1/admin/bookability/providers/{tenant_id}/refresh). Implemented client-side:
list every provider then refresh each in turn, aggregating {refreshed, errors}
into the shape the page already expected -- no backend change needed since
the underlying per-tenant capability is real and live.

Separately, listProviders's TS type claimed {providers, count, page,
page_size}, but the real response is {providers, total} only (the backend
also silently ignores page/search params -- only is_bookable/is_visible/
category_id/limit are read). The page read `.count` for its "N providers"
display, which was always 0/undefined. Fixed the type and the page's field
reference to `.total`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/super-admin/lib/api.ts"
PAGE = ROOT / "frontend/super-admin/app/admin/bookability/providers/page.tsx"

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def _live(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                      if not l.strip().startswith("//") and not l.strip().startswith("*"))


def test_bulk_refresh_no_longer_calls_the_dead_route():
    src = _live(API_TS.read_text(encoding="utf-8"))
    assert "/v1/admin/bookability/bulk-refresh" not in src
    assert "/v1/admin/bookability/providers/${p.tenant_id}/refresh" in src


def test_list_providers_returns_the_real_shape():
    src = API_TS.read_text(encoding="utf-8")
    block = src.split("listProviders:")[1].split("getProvider:")[0]
    assert "total: number" in block
    assert "count: number" not in block


def test_page_reads_total_not_count():
    src = _live(PAGE.read_text(encoding="utf-8"))
    assert "providers.data?.total" in src
    assert "providers.data?.count" not in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_dead_route_404s_and_real_list_plus_refresh_work(self):
        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as admin:
            dead = await admin.post("/v1/admin/bookability/bulk-refresh")
            assert dead.status_code == 404

            listed = await admin.get("/v1/admin/bookability/providers?limit=5")
            assert listed.status_code == 200
            d = listed.json()["data"]
            assert "total" in d and "count" not in d

            if d["providers"]:
                tid = d["providers"][0]["tenant_id"]
                refreshed = await admin.post(f"/v1/admin/bookability/providers/{tid}/refresh")
                assert refreshed.status_code == 200
