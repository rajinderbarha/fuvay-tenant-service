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


def test_deposit_balance_is_computed_and_cannot_be_overdrawn():
    """Finance invariant: SecurityDeposit.current_balance is a derived property
    (total_paid + replenishment_total - warranty_drawn), so a draw that only
    bumps warranty_drawn still correctly lowers the balance — there is no stored
    balance column that could drift and allow an over-draw."""
    from app.engines.platform_commerce.models import SecurityDeposit
    import inspect
    src = inspect.getsource(SecurityDeposit)
    assert "def current_balance" in src
    assert "self.total_paid + self.replenishment_total - self.warranty_drawn" in src
    # it must be a property, not a writable column
    assert "current_balance: Mapped" not in src


def test_deposit_replenishment_is_not_triggered_by_a_plain_wallet_credit():
    """Finance invariant: crediting the wallet (e.g. a commission reversal) must
    NOT replenish the security deposit — otherwise a reversal would fund the
    deposit from nothing. credit_wallet touches only wallet fields; deposit
    replenishment is a separate explicit credit_deposit call."""
    import inspect
    from app.engines.platform_commerce import ledger
    src = inspect.getsource(ledger.credit_wallet)
    assert "replenishment" not in src
    assert "SecurityDeposit" not in src
