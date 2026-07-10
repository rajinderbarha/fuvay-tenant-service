"""Step 9 manual smoke flows — cash/on-site payment closure, and insufficient
wallet balance, end to end at the service layer (no real DB in this sandbox)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.exceptions import ServiceOSException
from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.billing_service import BillingService

utcnow = lambda: datetime.now(timezone.utc)


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.SIGNED_OFF, job_type=JobType.REPAIR,
        job_number="JOB-202607-00099", title="AC Repair", description=None,
        service_type_id="ac_repair", service_category="ac", booking_id=None,
        service_id=uuid.uuid4(), quoted_price=Decimal("1450"), final_price=None,
        credit_applied=Decimal("0"), payable_amount=None,
        commission_deducted=False, commission_amount=None,
        invoice_id=None, payment_id=None, commission_id=None,
        invoice_generated_at=None, payment_pending_at=None, paid_at=None,
        closed_at=None, closed_by_user_id=None, closure_notes=None,
        final_payable_amount=None, status_updated_at=None, current_status_started_at=None,
        updated_at=utcnow(), created_at=utcnow(),
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def db_for(job):
    result = MagicMock(); result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    def _fake_add(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
    db.add = MagicMock(side_effect=_fake_add); db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_cash_payment_full_closure_smoke_flow():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.SIGNED_OFF)
    db = db_for(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)

    # 1. Generate invoice.
    invoice_result = await svc.generate_invoice(job.id, {
        "labour_amount": 800, "parts_amount": 450, "visit_fee": 200})
    assert invoice_result["total_amount"] == 1450.0
    assert job.status == JS.INVOICE_GENERATED

    # Capture the created InvoiceRecord (real ORM object, not a mock) so the
    # next phase can look it up by id, matching what a real DB round-trip does.
    from app.engines.payment.models import InvoiceRecord
    created_invoice = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], InvoiceRecord))
    assert str(created_invoice.id) == invoice_result["invoice_id"]

    invoice_result_obj = MagicMock(); invoice_result_obj.scalar_one_or_none.return_value = created_invoice
    job_result_obj = MagicMock(); job_result_obj.scalar_one_or_none.return_value = job
    db.execute = AsyncMock(side_effect=[job_result_obj, invoice_result_obj])

    fake_commerce_result = {"effective_rate": 10, "commission_amount": 145.0,
                             "wallet_balance_before": 1000.0, "wallet_balance_after": 855.0,
                             "idempotent": False}
    with patch("app.engines.platform_commerce.service.CommerceService.deduct_commission",
               new=AsyncMock(return_value=fake_commerce_result)):
        # 2. Record cash payment — auto-triggers commission deduction.
        commission_rec_result = MagicMock(); commission_rec_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[
            job_result_obj, invoice_result_obj,  # record_payment: job, invoice
            job_result_obj, commission_rec_result,  # deduct_commission: job, commission-record lookup
        ])
        payment_result = await svc.record_payment(job.id, {
            "amount": 1450, "payment_method": "cash", "notes": "Customer paid cash after service."})

    assert payment_result["payment_status"] == "paid"
    assert payment_result["job_status"] == JS.PAID
    assert job.status == JS.PAID
    assert created_invoice.status == "paid"
    assert job.commission_deducted is True
    assert float(job.commission_amount) == 145.0

    # 3. Close job.
    db.execute = AsyncMock(return_value=job_result_obj)
    close_result = await svc.close_job_financial(job.id, "Cash collected and job closed.")
    assert close_result["status"] == JS.CLOSED
    assert job.status == JS.CLOSED
    assert job.closed_by_user_id == svc.actor_id

    # 4. Customer views the invoice.
    customer_svc = BillingService(db=db, actor_id=job.customer_id, actor_role="customer")
    inv_only_result = MagicMock(); inv_only_result.scalar_one_or_none.return_value = created_invoice
    db.execute = AsyncMock(side_effect=[inv_only_result, job_result_obj, MagicMock(scalar_one_or_none=MagicMock(return_value=None))])
    detail = await customer_svc.get_customer_invoice_detail(job.customer_id, created_invoice.id)
    assert detail["status"] == "paid"
    assert detail["total_amount"] == 1450.0


@pytest.mark.asyncio
async def test_insufficient_wallet_smoke_flow():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, invoice_id=uuid.uuid4(), payment_id=uuid.uuid4(),
                    final_payable_amount=Decimal("1450"))
    db = db_for(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)

    async def raise_empty(*a, **kw):
        raise ServiceOSException("COMMISSION_WALLET_EMPTY", "Insufficient wallet balance.", status_code=402)

    with patch("app.engines.platform_commerce.service.CommerceService.deduct_commission", new=raise_empty):
        with pytest.raises(ServiceOSException) as exc:
            await svc.deduct_commission(job.id)
    assert exc.value.error_code == "INSUFFICIENT_WALLET_BALANCE"

    # Job remains paid but not closed/commission-deducted — wallet/job state intact.
    assert job.status == JS.PAID
    assert job.commission_deducted is False

    # Job cannot close while commission is required and not yet deducted.
    with pytest.raises(ServiceOSException) as exc2:
        await svc.close_job_financial(job.id)
    assert exc2.value.error_code == "JOB_NOT_READY_FOR_CLOSE"
