"""MODULE-L5-10 (Finance) — the deposit refund path (money OUT) must be guarded."""
import inspect


def test_refund_deposit_guards_amount_and_double_refund():
    """refund_deposit had no guards. A negative amount would run
    warranty_drawn += negative and INFLATE the deposit balance; and a deposit
    already 'refunded' could be refunded again — a partial refund leaves
    status='refunded' with balance > 0, so a second call draws more money to the
    tenant. Both must be blocked before debit_deposit runs."""
    from app.engines.finance_hub.service import FinanceHubService
    src = inspect.getsource(FinanceHubService.refund_deposit)
    assert 'amount <= Decimal("0")' in src
    assert 'DEPOSIT_ALREADY_REFUNDED' in src
    # guards must precede the money movement
    assert src.index("DEPOSIT_ALREADY_REFUNDED") < src.index("await debit_deposit(")
    assert src.index('amount <= Decimal("0")') < src.index("await debit_deposit(")
