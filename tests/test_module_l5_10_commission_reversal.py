"""MODULE-L5-10 (Finance) — commission reversal must not mint free money."""
import inspect


def test_reverse_requires_deducted_status():
    """reverse_commission credited the provider's wallet back with NO check that
    the commission was ever deducted. A commission in calculated / failed /
    insufficient_credit status never took any money, so 'reversing' it credited
    the wallet for a charge that never happened — free money — and an
    already-reversed one could be reversed again. It must require COM_DEDUCTED."""
    from app.engines.invoice_payment.commission_service import ServiceCommissionService
    src = inspect.getsource(ServiceCommissionService.reverse_commission)
    assert "cr.status != COM_DEDUCTED" in src
    assert "ERR_COMMISSION_NOT_REVERSIBLE" in src
    # the guard must sit BEFORE the wallet credit
    guard = src.index("ERR_COMMISSION_NOT_REVERSIBLE")
    credit = src.index("credit_wallet")
    assert guard < credit, "status guard must precede the wallet credit"
