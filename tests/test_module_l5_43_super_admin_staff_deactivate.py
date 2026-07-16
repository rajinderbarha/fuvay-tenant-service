"""MODULE-L5-43 — super-admin's "Deactivate Staff" action (tenant detail page)
called a route that doesn't exist, and even the corrected tenant-scoped route
would 403 for every super_admin caller.

First audit of frontend/super-admin (following the tenant-portal audit that
found L5-39/40/41/42). staffApi.deactivate called
POST /v1/auth/admin/staff/{id}/deactivate -- doesn't exist (404; real route
has no "admin" segment: /v1/auth/staff/{id}/deactivate). But that tenant-
scoped route (auth/router.py deactivate_staff) hard-requires the CALLER's own
tenant_id and always raises PERMISSION_DENIED for a super_admin caller (whose
token carries no tenant_id) -- so simply fixing the URL would still leave the
button broken for every super-admin use.

The real, super_admin-usable endpoint is
POST /v1/admin/platform-users/{user_id}/deactivate (platform_users_router.py,
require_platform_mutate -> require_super_admin), whose service-layer
permission check (_can_admin_manage_user) explicitly allows super_admin to
manage any user regardless of tenant. Body is {reason, revoke_sessions}
(both optional, both defaulted server-side).

staffApi.invite's URL had the same stray "admin/" segment; fixed the literal
route (it has zero callers in this app, so left otherwise unchanged -- it has
its own separate limitation of always scoping to the caller's own tenant_id,
which is out of scope for this fix since nothing calls it).

Verified live: dead route 404s; the fixed tenant-scoped route reaches the
handler but 403s (PERMISSION_DENIED) for a super_admin; the real platform-users
route reaches the handler (domain NOT_FOUND for a nonexistent id, not a route
error).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/super-admin/lib/api.ts"

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def _staff_block(src: str) -> str:
    block = src.split("export const staffApi")[1].split("\nexport const")[0]
    return "\n".join(l for l in block.splitlines() if not l.strip().startswith("//"))


def test_deactivate_uses_the_real_super_admin_usable_route():
    block = _staff_block(API_TS.read_text(encoding="utf-8"))
    assert "/v1/admin/platform-users/${userId}/deactivate" in block
    assert "/v1/auth/admin/staff" not in block


def test_invite_url_typo_fixed():
    block = _staff_block(API_TS.read_text(encoding="utf-8"))
    assert "/v1/auth/staff/invite" in block


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_dead_and_tenant_scoped_and_real_routes(self):
        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")
        fake = "00000000-0000-0000-0000-000000000000"
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as admin:
            dead = await admin.post(f"/v1/auth/admin/staff/{fake}/deactivate")
            assert dead.status_code == 404

            tenant_scoped = await admin.post(f"/v1/auth/staff/{fake}/deactivate", json={})
            assert tenant_scoped.json().get("error_code") == "PERMISSION_DENIED"

            real = await admin.post(f"/v1/admin/platform-users/{fake}/deactivate", json={})
            assert real.json().get("error_code") == "NOT_FOUND"
