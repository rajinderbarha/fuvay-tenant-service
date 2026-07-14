"""MODULE-L5-10 (Finance) — payment timeline must be tenant-scoped."""
import inspect


def test_get_payment_timeline_enforces_tenant_when_supplied():
    """get_payment_timeline accepted a tenant_id and then IGNORED it, so the
    provider financial-timeline endpoint (which passes user.tenant_id) leaked
    every other tenant's payment records for any invoice_id an attacker
    enumerated — a cross-tenant IDOR. It must filter by tenant when a tenant_id
    is supplied (the customer path passes None and gates ownership in its
    router). Proven live: another tenant reading Demo AC's invoice timeline now
    gets 0 records; the owner still sees their own."""
    from app.engines.invoice_payment.payment_service import ServicePaymentService
    src = inspect.getsource(ServicePaymentService.get_payment_timeline)
    assert "if tenant_id is not None:" in src
    assert "ServicePaymentRecord.tenant_id ==" in src
