"""MODULE-L5-01 — Identity & Access certification sprint.

Real, live regression test for a CRITICAL cross-tenant IDOR found this
sprint: `GET`/`PUT /v1/tenants/{tenant_id}` accepted ANY tenant_id in the
path without checking it against the caller's own tenant_id. tenant_owner's
real permission bundle includes TENANT_READ/TENANT_UPDATE (self-service),
so any tenant_owner could substitute a different tenant's UUID and read or
write that tenant's profile/billing data.

Fixed in `app/engines/tenant_engine/router.py` via
`_assert_own_tenant_or_super_admin`. This test hits the real running
backend over real HTTP with real seeded accounts -- not mocked -- to prove
the fix holds and that legitimate access (own-tenant self-service,
platform-admin cross-tenant oversight) is preserved.

Requires a real backend running at localhost:8000 with the standard seeded
demo tenants ("Demo AC Services" and "Isolation Test Services"). Skips
cleanly if the backend or those fixtures are unavailable, rather than
failing the whole suite in environments without live seed data.
"""
from __future__ import annotations

import pytest
import requests

BASE = "http://localhost:8000"
TIMEOUT = 30

TENANT_A_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"  # Demo AC Services
TENANT_A_OWNER = ("provider@serviceos.local", "Password123!")
TENANT_B_ID = "f45664c1-50b7-42c5-a115-37fed1bbaf53"  # Isolation Test Services
TENANT_B_OWNER = ("owner@isolation-test-services.local", "CanonicalL5!2026")
SUPER_ADMIN = ("admin@serviceos.local", "Password123!")


def _backend_available() -> bool:
    try:
        r = requests.get(f"{BASE}/health", timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def _login(email: str, password: str) -> str | None:
    try:
        r = requests.post(f"{BASE}/v1/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    return r.json().get("data", {}).get("access_token")


@pytest.fixture(scope="module")
def tokens():
    if not _backend_available():
        pytest.skip("Real backend not reachable at localhost:8000 -- this is a live-HTTP regression test")
    token_a = _login(*TENANT_A_OWNER)
    token_b = _login(*TENANT_B_OWNER)
    token_super = _login(*SUPER_ADMIN)
    if not (token_a and token_b and token_super):
        pytest.skip("Seed accounts for this live cross-tenant test are not available in this environment")
    return {"a": token_a, "b": token_b, "super": token_super}


class TestCrossTenantIDORFix:
    def test_tenant_owner_can_read_own_tenant(self, tokens):
        r = requests.get(f"{BASE}/v1/tenants/{TENANT_A_ID}",
                          headers={"Authorization": f"Bearer {tokens['a']}"}, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["data"]["tenant_id"] == TENANT_A_ID

    def test_tenant_owner_cannot_read_other_tenant(self, tokens):
        r = requests.get(f"{BASE}/v1/tenants/{TENANT_B_ID}",
                          headers={"Authorization": f"Bearer {tokens['a']}"}, timeout=TIMEOUT)
        assert r.status_code == 403
        assert r.json()["error_code"] == "PERMISSION_DENIED"

    def test_tenant_owner_cannot_update_other_tenant(self, tokens):
        r = requests.put(f"{BASE}/v1/tenants/{TENANT_B_ID}",
                          json={"city": "Should Not Be Written"},
                          headers={"Authorization": f"Bearer {tokens['a']}"}, timeout=TIMEOUT)
        assert r.status_code == 403
        # Confirm zero mutation: re-read as the real owner and check city is unchanged.
        check = requests.get(f"{BASE}/v1/tenants/{TENANT_B_ID}",
                              headers={"Authorization": f"Bearer {tokens['b']}"}, timeout=TIMEOUT)
        assert check.status_code == 200
        assert check.json()["data"].get("city") != "Should Not Be Written"

    def test_reverse_direction_also_blocked(self, tokens):
        """Symmetric check -- Tenant B cannot read Tenant A either."""
        r = requests.get(f"{BASE}/v1/tenants/{TENANT_A_ID}",
                          headers={"Authorization": f"Bearer {tokens['b']}"}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_super_admin_retains_cross_tenant_read(self, tokens):
        """Regression guard: the fix must not break legitimate platform-admin access."""
        r = requests.get(f"{BASE}/v1/tenants/{TENANT_B_ID}",
                          headers={"Authorization": f"Bearer {tokens['super']}"}, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["data"]["tenant_id"] == TENANT_B_ID
