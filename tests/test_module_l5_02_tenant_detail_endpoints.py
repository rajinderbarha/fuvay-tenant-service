"""Admin tenant-detail endpoint resilience contracts.

The provider-wallet endpoint must return a zero balance when a tenant has no
wallet instead of leaking a ValueError as a 500. The retired provider
monetization-status surface is deliberately not covered here: effective
commission now comes from the canonical vertical-monetization and Home
Services finance engines.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WALLET = (ROOT / "app/engines/invoice_payment/admin_router.py").read_text(
    encoding="utf-8"
)


def test_admin_get_wallet_handles_missing_wallet():
    """A missing wallet is an empty state, not an internal-server error."""
    idx = WALLET.index("async def admin_get_wallet(")
    body = WALLET[idx : idx + 900]
    assert "except ValueError" in body
    assert '"current_balance": "0"' in body
