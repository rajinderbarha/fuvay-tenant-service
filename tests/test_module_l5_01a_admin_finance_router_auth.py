"""MODULE-L5-01A — Tenant-Scope Enforcement Completion Sprint.

Real, live regression test for a CRITICAL finding this sprint:
`app/engines/invoice_payment/admin_router.py` mounted 14 endpoints under
`/v1/admin/*` (invoices, payments, commissions, provider wallets, subscription
status, financial events) gated ONLY by bare `Depends(get_current_user)` --
no permission or role check anywhere in the file. Any authenticated user of
any role, including `customer`, could list every tenant's financial records,
and could **credit any tenant's wallet with an arbitrary amount**
(`POST /{tenant_id}/credit`) -- a direct financial-fraud vector.

Fixed by replacing every `Depends(get_current_user)` with
`Depends(require_super_admin)`, matching the identical pattern already used
by the sibling `field_ops/admin_finance_router.py` for equivalent
platform-wide wallet operations.

This test hits the real running backend over real HTTP with real seeded
accounts -- not mocked.
"""
from __future__ import annotations

import pytest
import requests

BASE = "http://localhost:8000"
TIMEOUT = 30

TENANT_A_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"  # Demo AC Services
TENANT_OWNER = ("provider@serviceos.local", "Password123!")
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
    token_tenant_owner = _login(*TENANT_OWNER)
    token_super = _login(*SUPER_ADMIN)
    if not (token_tenant_owner and token_super):
        pytest.skip("Seed accounts for this live test are not available in this environment")
    return {"tenant_owner": token_tenant_owner, "super_admin": token_super}


class TestAdminFinanceRouterNoLongerBareAuth:
    def test_tenant_owner_cannot_credit_any_wallet(self, tokens):
        """The core financial-fraud finding: a non-admin role must not be
        able to credit an arbitrary tenant's wallet."""
        r = requests.post(
            f"{BASE}/v1/admin/provider-wallets/{TENANT_A_ID}/credit",
            json={"amount": 999999, "reason": "MODULE-L5-01A exploit-attempt regression test"},
            headers={"Authorization": f"Bearer {tokens['tenant_owner']}"}, timeout=TIMEOUT,
        )
        assert r.status_code == 403

    def test_tenant_owner_cannot_read_any_wallet(self, tokens):
        r = requests.get(f"{BASE}/v1/admin/provider-wallets/{TENANT_A_ID}",
                          headers={"Authorization": f"Bearer {tokens['tenant_owner']}"}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_tenant_owner_cannot_list_all_wallets(self, tokens):
        r = requests.get(f"{BASE}/v1/admin/provider-wallets",
                          headers={"Authorization": f"Bearer {tokens['tenant_owner']}"}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_tenant_owner_cannot_list_all_invoices(self, tokens):
        r = requests.get(f"{BASE}/v1/admin/service-invoices",
                          headers={"Authorization": f"Bearer {tokens['tenant_owner']}"}, timeout=TIMEOUT)
        assert r.status_code == 403

    def test_super_admin_retains_legitimate_access(self, tokens):
        """Regression guard: the fix must not break legitimate platform-admin access."""
        r = requests.get(f"{BASE}/v1/admin/provider-wallets",
                          headers={"Authorization": f"Bearer {tokens['super_admin']}"}, timeout=TIMEOUT)
        assert r.status_code == 200
        r2 = requests.get(f"{BASE}/v1/admin/service-invoices",
                           headers={"Authorization": f"Bearer {tokens['super_admin']}"}, timeout=TIMEOUT)
        assert r2.status_code == 200

    def test_unauthenticated_denied(self, tokens):
        r = requests.get(f"{BASE}/v1/admin/provider-wallets", timeout=TIMEOUT)
        assert r.status_code == 401
