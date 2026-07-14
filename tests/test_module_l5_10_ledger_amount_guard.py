"""MODULE-L5-10 (Finance) — the ledger primitives must reject non-positive amounts."""
import inspect


def test_all_four_primitives_guard_the_amount():
    """debit_wallet / credit_wallet / debit_deposit / credit_deposit had no
    amount validation. A non-positive amount passes the balance check
    (balance < negative is False) and then runs `balance -= negative`, INFLATING
    the balance — i.e. a debit that credits, or a credit that debits. Every
    service-layer fix added its own amount guard, but the primitives themselves
    did not, so any unguarded caller could invert a money movement. Guard added
    at the source."""
    from app.engines.platform_commerce import ledger
    for name in ("debit_wallet", "credit_wallet", "debit_deposit", "credit_deposit"):
        src = inspect.getsource(getattr(ledger, name))
        assert 'amount <= Decimal("0")' in src, name
        assert "INVALID_LEDGER_AMOUNT" in src, name
