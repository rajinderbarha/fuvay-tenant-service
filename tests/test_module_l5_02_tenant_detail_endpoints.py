"""MODULE-L5-02 — admin tenant-detail-page endpoint resilience.

Live contract verification of the super-admin tenant detail page found two
endpoints returning 500 for a valid tenant: the provider-wallet tab (tenant
with no wallet -> bare ValueError -> 500) and the monetization tab (queries the
un-provisioned provider_monetization_statuses table -> 500). Both now degrade
gracefully. These tests pin the source-level fixes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WALLET = (ROOT / "app/engines/invoice_payment/admin_router.py").read_text(encoding="utf-8")
MONET = (ROOT / "app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")


def test_admin_get_wallet_handles_missing_wallet():
    # The handler must catch the not-found ValueError and return a default
    # instead of letting it become a 500.
    idx = WALLET.index('async def admin_get_wallet(')
    body = WALLET[idx:idx + 900]
    assert "except ValueError" in body
    assert '"current_balance": "0"' in body


def test_admin_monetization_handles_missing_table():
    idx = MONET.index('async def get_provider_monetization(')
    body = MONET[idx:idx + 1400]
    assert "except Exception" in body
    assert "is_monetization_ready" in body
    assert "rollback" in body
