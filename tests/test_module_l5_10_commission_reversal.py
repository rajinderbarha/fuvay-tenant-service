"""Commission reversal and retired-deposit financial invariants."""
import inspect


def test_reverse_requires_deducted_status():
    from app.engines.invoice_payment.commission_service import ServiceCommissionService
    src = inspect.getsource(ServiceCommissionService.reverse_commission)
    assert "cr.status != COM_DEDUCTED" in src
    assert "ERR_COMMISSION_NOT_REVERSIBLE" in src
    assert src.index("ERR_COMMISSION_NOT_REVERSIBLE") < src.index("credit_wallet")


def test_retired_security_deposit_model_cannot_be_used():
    from app.engines.platform_commerce import models
    assert not hasattr(models, "SecurityDeposit")


def test_commission_reversal_credits_only_usage_credits():
    from app.engines.platform_commerce import ledger
    src = inspect.getsource(ledger.credit_wallet)
    assert "replenishment" not in src
    assert "SecurityDeposit" not in src
    assert "credit_balance" in src
