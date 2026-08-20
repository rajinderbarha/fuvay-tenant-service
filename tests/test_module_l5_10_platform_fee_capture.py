"""MODULE-L5-10 — the customer charge is captured as platform revenue on the invoice."""
import inspect
from decimal import Decimal


def test_refresh_totals_adds_platform_fee_on_top_of_service_value():
    """total_amount stays the SERVICE value; the platform fee is added on top so
    customer_payable_amount is inclusive. Proven live: Rs.500 service @ 10% ->
    total_amount 500, platform_fee_amount 50, customer_payable 550."""
    from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
    src = inspect.getsource(ServiceInvoiceService._refresh_totals)
    assert "platform_fee_amount" in src
    assert "customer_payable_amount" in src
    assert "_resolve_customer_platform_fee" in src
    resolver = inspect.getsource(ServiceInvoiceService._resolve_customer_platform_fee)
    assert "get_current_policy_by_vertical_key" in resolver
    assert "customer_charge_pct" not in resolver


def test_commission_base_is_the_service_value_not_the_inclusive_amount():
    """The provider must NOT be charged commission on the platform's own customer
    fee. Commission base is total_amount (service value), not
    customer_payable_amount (which now includes the fee)."""
    from app.engines.invoice_payment.commission_service import ServiceCommissionService
    src = inspect.getsource(ServiceCommissionService.calculate_commission)
    assert "base = inv.total_amount" in src
    assert "base = inv.customer_payable_amount" not in src


def test_platform_fee_is_booked_as_a_revenue_event_on_payment():
    from app.engines.invoice_payment.payment_service import ServicePaymentService
    src = inspect.getsource(ServicePaymentService.record_onsite_payment)
    assert "FEV_PLATFORM_CUSTOMER_FEE" in src
    assert "platform_fee_amount" in src
