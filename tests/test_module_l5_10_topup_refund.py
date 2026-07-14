"""MODULE-L5-10 (Finance) — top-up refund must accumulate and cap."""
import inspect


def test_topup_refund_accumulates_and_caps():
    """refund_topup OVERWROTE refunded_amount (t.refunded_amount = amount), so a
    second partial refund silently lost the first, and there was no cap — an admin
    could record a refund larger than amount_paid, or re-refund a fully-refunded
    order. It must accumulate onto the prior refunded_amount and reject anything
    over amount_paid."""
    from app.engines.finance_hub.service import FinanceHubService
    src = inspect.getsource(FinanceHubService.refund_topup)
    assert "t.refunded_amount = already + amount" in src   # accumulates, not overwrites
    assert "t.refunded_amount = Decimal(str(amount))" not in src
    assert "TOPUP_ALREADY_REFUNDED" in src
    assert "TOPUP_REFUND_EXCEEDS_PAID" in src
    assert 'amount <= Decimal("0")' in src
