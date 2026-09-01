"""MODULE-L5-10 (Finance) — retired security-deposit paths stay retired."""
from pathlib import Path


def test_deposit_refund_path_is_removed():
    """Home Services no longer holds deposits, so no refund API may survive."""
    from app.engines.finance_hub.service import FinanceHubService
    from app.engines.platform_commerce import ledger

    assert not hasattr(FinanceHubService, "refund_deposit")
    assert not hasattr(ledger, "debit_deposit")
    assert not hasattr(ledger, "credit_deposit")


def test_deposit_removal_migrations_remain_present():
    root = Path(__file__).parent.parent / "alembic" / "versions"
    assert (root / "317_topup_seats_remove_security_deposit.py").exists()
    assert (root / "318_dispute_settlement_credit_only.py").exists()
