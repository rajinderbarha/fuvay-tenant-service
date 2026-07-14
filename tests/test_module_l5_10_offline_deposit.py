"""MODULE-L5-10 (Finance) — recording an offline deposit (money IN) must be guarded."""
import inspect


def test_offline_deposit_validates_amount_and_dedupes_reference():
    """record_offline_deposit had no amount check (a negative would run
    total_paid += negative and reduce the deposit) and no idempotency — recording
    the same bank reference twice double-credited the deposit, even though
    confirm_deposit already dedupes on its reference. Both must be guarded."""
    from app.engines.finance_hub.service import FinanceHubService
    src = inspect.getsource(FinanceHubService.record_offline_deposit)
    assert 'amount <= Decimal("0")' in src
    assert "reference_id == reference" in src            # dedupe query
    assert '"idempotent": True' in src
    # guards precede the credit
    assert src.index('amount <= Decimal("0")') < src.index("await credit_deposit(")
    assert src.index("reference_id == reference") < src.index("await credit_deposit(")
