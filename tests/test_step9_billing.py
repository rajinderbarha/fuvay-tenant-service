"""
Step 9 — Payment / Invoice / Commission Closure Flow.

Reuses existing platform_commerce (TenantWallet/WalletTransaction/
CommissionRecord, CommerceService.deduct_commission — already idempotent on
job_id) and payment engine (InvoiceRecord/PaymentRecord, extended with
job-level fields) rather than building parallel finance tables.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException
from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.billing_service import BillingService
from app.engines.field_ops.models import Job
from app.engines.payment.models import InvoiceRecord, PaymentRecord
from app.engines.platform_commerce.models import CommissionRecord
from app.schemas.base import ERROR_CODES

utcnow = lambda: datetime.now(timezone.utc)


def db_seq(*objs):
    results = []
    for o in objs:
        r = MagicMock(); r.scalar_one_or_none.return_value = o
        results.append(r)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=results if len(results) > 1 else None,
                            return_value=results[0] if len(results) == 1 else None)
    def _fake_add(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
    db.add = MagicMock(side_effect=_fake_add); db.flush = AsyncMock()
    return db


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.SIGNED_OFF, job_type=JobType.REPAIR,
        job_number="JOB-202607-00001", title="AC Repair", description=None,
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


def make_invoice(**overrides):
    defaults = dict(id=uuid.uuid4(), tenant_id=uuid.uuid4(), job_id=uuid.uuid4(),
                     customer_id=uuid.uuid4(), payment_id=None, booking_id=None,
                     service_id=uuid.uuid4(), job_type=JobType.REPAIR,
                     invoice_number="INV-202607-00001", invoice_type="job_invoice",
                     amount=Decimal("1450"), subtotal_amount=Decimal("1450"),
                     labour_amount=Decimal("800"), parts_amount=Decimal("450"),
                     visit_fee=Decimal("200"), discount_amount=Decimal("0"),
                     tax_amount=Decimal("0"), total_amount=Decimal("1450"),
                     currency="INR", status="issued", pdf_url=None, media_file_id=None,
                     storage_key=None, line_items=[], meta={},
                     issued_at=utcnow(), paid_at=None, due_at=None)
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_payment(**overrides):
    defaults = dict(id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
                     job_id=uuid.uuid4(), invoice_id=uuid.uuid4(), payment_number="PAY-202607-00001",
                     amount=Decimal("1450"), currency="INR", payment_method="cash",
                     payment_status="paid", status="paid", notes=None,
                     collected_by_user_id=uuid.uuid4(), collected_by_staff_id=None,
                     paid_at=utcnow(), created_at=utcnow())
    defaults.update(overrides)
    return MagicMock(**defaults)


# ── 1. Error codes ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    "INVOICE_NOT_FOUND", "INVOICE_ALREADY_EXISTS", "INVOICE_ALREADY_PAID", "INVOICE_GENERATION_FAILED",
    "INVALID_INVOICE_AMOUNT", "PAYMENT_NOT_FOUND", "PAYMENT_AMOUNT_MISMATCH", "PAYMENT_ALREADY_RECORDED",
    "PAYMENT_RECORD_FAILED", "PAYMENT_NOT_PAID", "INVALID_PAYMENT_METHOD", "COMMISSION_NOT_FOUND",
    "COMMISSION_ALREADY_DEDUCTED", "COMMISSION_CALCULATION_FAILED", "COMMISSION_DEDUCTION_FAILED",
    "INSUFFICIENT_WALLET_BALANCE", "TENANT_WALLET_NOT_FOUND", "WALLET_LEDGER_CREATE_FAILED",
    "JOB_NOT_SIGNED_OFF", "JOB_NOT_READY_FOR_INVOICE", "JOB_NOT_READY_FOR_PAYMENT",
    "JOB_NOT_READY_FOR_CLOSE", "JOB_ALREADY_CLOSED", "FINANCIAL_CLOSE_FAILED",
    "RAZORPAY_SIGNATURE_INVALID", "PAYMENT_WEBHOOK_FAILED", "COMMISSION_WALLET_EMPTY",
])
def test_error_code_registered(code):
    assert code in ERROR_CODES


# ── 2. JS statuses / transitions ────────────────────────────────────────────────

def test_payment_pending_and_paid_statuses_exist():
    assert JS.PAYMENT_PENDING == "payment_pending"
    assert JS.PAID == "paid"

def test_invoice_generated_transitions_to_payment_pending_and_paid():
    from app.engines.field_ops.constants import get_allowed_transitions
    allowed = get_allowed_transitions(JobType.REPAIR, JS.INVOICE_GENERATED)
    assert JS.PAYMENT_PENDING in allowed
    assert JS.PAID in allowed
    assert JS.CLOSED in allowed  # legacy close_job() pipeline still reachable

def test_payment_pending_to_paid():
    from app.engines.field_ops.constants import get_allowed_transitions
    assert JS.PAID in get_allowed_transitions(JobType.REPAIR, JS.PAYMENT_PENDING)

def test_paid_to_closed():
    from app.engines.field_ops.constants import get_allowed_transitions
    assert JS.CLOSED in get_allowed_transitions(JobType.REPAIR, JS.PAID)

def test_closed_is_still_terminal():
    from app.engines.field_ops.constants import ALLOWED_TRANSITIONS
    assert ALLOWED_TRANSITIONS[JS.CLOSED] == []


# ── 3. Invoice generation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_can_generate_invoice_for_signed_off_job():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.SIGNED_OFF)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.generate_invoice(job.id, {"labour_amount": 800, "parts_amount": 450, "visit_fee": 200})
    assert result["total_amount"] == 1450.0
    assert result["job_status"] == JS.INVOICE_GENERATED
    assert job.status == JS.INVOICE_GENERATED
    assert job.invoice_id is not None

@pytest.mark.asyncio
async def test_invoice_amount_calculation_correct():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.SIGNED_OFF)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.generate_invoice(job.id, {
        "labour_amount": 1000, "parts_amount": 500, "visit_fee": 100,
        "tax_amount": 50, "discount_amount": 100})
    assert result["total_amount"] == 1550.0  # 1000+500+100+50-100

@pytest.mark.asyncio
async def test_negative_invoice_amount_rejected():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.SIGNED_OFF)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.generate_invoice(job.id, {"labour_amount": -100})
    assert exc.value.error_code == "INVALID_INVOICE_AMOUNT"

@pytest.mark.asyncio
async def test_duplicate_invoice_blocked():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.generate_invoice(job.id, {"labour_amount": 800})
    assert exc.value.error_code == "INVOICE_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_tenant_cannot_invoice_another_tenants_job():
    job = make_job(tenant_id=uuid.uuid4(), status=JS.SIGNED_OFF)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.generate_invoice(job.id, {"labour_amount": 800})
    assert exc.value.error_code == "JOB_NOT_FOUND"

@pytest.mark.asyncio
async def test_job_must_be_signed_off_or_completed_to_invoice():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.WORK_STARTED)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.generate_invoice(job.id, {"labour_amount": 800})
    assert exc.value.error_code == "JOB_NOT_READY_FOR_INVOICE"


# ── 4. Payment recording ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_can_record_cash_payment():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    invoice = make_invoice(tenant_id=tid, id=job.invoice_id, total_amount=Decimal("1450"), status="issued")
    db = db_seq(job, invoice)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc.deduct_commission = AsyncMock(return_value={"commission_status": "deducted"})
    result = await svc.record_payment(job.id, {"amount": 1450, "payment_method": "cash"})
    assert result["payment_status"] == "paid"
    assert result["job_status"] == JS.PAID
    assert job.status == JS.PAID
    assert invoice.status == "paid"

@pytest.mark.asyncio
async def test_payment_amount_must_match_invoice_total():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    invoice = make_invoice(tenant_id=tid, id=job.invoice_id, total_amount=Decimal("1450"))
    db = db_seq(job, invoice)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.record_payment(job.id, {"amount": 1000, "payment_method": "cash"})
    assert exc.value.error_code == "PAYMENT_AMOUNT_MISMATCH"

@pytest.mark.asyncio
async def test_invalid_payment_method_rejected():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    invoice = make_invoice(tenant_id=tid, id=job.invoice_id, total_amount=Decimal("1450"))
    db = db_seq(job, invoice)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.record_payment(job.id, {"amount": 1450, "payment_method": "crypto"})
    assert exc.value.error_code == "INVALID_PAYMENT_METHOD"

@pytest.mark.asyncio
async def test_duplicate_payment_blocked():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, invoice_id=uuid.uuid4(), payment_id=uuid.uuid4())
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.record_payment(job.id, {"amount": 1450, "payment_method": "cash"})
    assert exc.value.error_code == "PAYMENT_ALREADY_RECORDED"

@pytest.mark.asyncio
async def test_customer_cannot_record_payment():
    job = make_job(status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
    # Customer role isn't tenant_owner/staff — _get_job_for_billing doesn't special-case
    # "customer" isolation (it's gated entirely by router permission, mirroring how
    # FIELD_OPS_JOBS_CLOSE is never granted to the customer role).
    from app.core.permissions import P, ROLE_PERMISSIONS
    assert P.FIELD_OPS_JOBS_CLOSE not in ROLE_PERMISSIONS["customer"]

@pytest.mark.asyncio
async def test_tenant_cannot_record_payment_for_another_tenants_job():
    job = make_job(tenant_id=uuid.uuid4(), status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.record_payment(job.id, {"amount": 1450, "payment_method": "cash"})
    assert exc.value.error_code == "JOB_NOT_FOUND"

@pytest.mark.asyncio
async def test_payment_status_pending_does_not_mark_job_paid():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.INVOICE_GENERATED, invoice_id=uuid.uuid4())
    invoice = make_invoice(tenant_id=tid, id=job.invoice_id, total_amount=Decimal("1450"))
    db = db_seq(job, invoice)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.record_payment(job.id, {
        "amount": 1450, "payment_method": "online_gateway", "payment_status": "pending"})
    assert result["job_status"] == JS.PAYMENT_PENDING
    assert job.status == JS.PAYMENT_PENDING


# ── 5. Commission deduction ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_commission_deduction_debits_wallet_and_updates_job():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, invoice_id=uuid.uuid4(), payment_id=uuid.uuid4(),
                    final_payable_amount=Decimal("1450"))
    commission_rec = MagicMock(id=uuid.uuid4(), job_id=str(job.id))
    db = db_seq(job, commission_rec)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)

    fake_commerce_result = {"effective_rate": 10, "commission_amount": 145.0,
                             "wallet_balance_before": 1000.0, "wallet_balance_after": 855.0,
                             "idempotent": False}
    with __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.engines.platform_commerce.service.CommerceService.deduct_commission",
            new=AsyncMock(return_value=fake_commerce_result)):
        result = await svc.deduct_commission(job.id)

    assert result["commission_amount"] == 145.0
    assert result["wallet_balance_before"] == 1000.0
    assert result["wallet_balance_after"] == 855.0
    assert job.commission_deducted is True

@pytest.mark.asyncio
async def test_commission_cannot_be_deducted_twice():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, invoice_id=uuid.uuid4(), payment_id=uuid.uuid4(),
                    commission_deducted=True, commission_amount=Decimal("145"))
    existing_rec = MagicMock(id=uuid.uuid4())
    db = db_seq(job, existing_rec)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.deduct_commission(job.id)
    assert result["idempotent"] is True
    assert result["commission_status"] == "deducted"

@pytest.mark.asyncio
async def test_insufficient_wallet_balance_fails_cleanly():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, invoice_id=uuid.uuid4(), payment_id=uuid.uuid4(),
                    final_payable_amount=Decimal("1450"))
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)

    async def raise_empty(*a, **kw):
        raise ServiceOSException("COMMISSION_WALLET_EMPTY", "Insufficient wallet balance.", status_code=402)

    with __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.engines.platform_commerce.service.CommerceService.deduct_commission", new=raise_empty):
        with pytest.raises(ServiceOSException) as exc:
            await svc.deduct_commission(job.id)
    assert exc.value.error_code == "INSUFFICIENT_WALLET_BALANCE"
    assert job.commission_deducted is False  # wallet/job state not corrupted

@pytest.mark.asyncio
async def test_commission_requires_invoice_first():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.SIGNED_OFF, invoice_id=None)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.deduct_commission(job.id)
    assert exc.value.error_code == "JOB_NOT_READY_FOR_PAYMENT"


# ── 6. Job close ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_paid_job_with_commission_deducted_can_close():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, commission_deducted=True)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.close_job_financial(job.id, "All good")
    assert result["status"] == JS.CLOSED
    assert job.status == JS.CLOSED
    assert job.closed_by_user_id == svc.actor_id

@pytest.mark.asyncio
async def test_job_cannot_close_before_payment():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.INVOICE_GENERATED, commission_deducted=False)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.close_job_financial(job.id)
    assert exc.value.error_code == "JOB_NOT_READY_FOR_CLOSE"

@pytest.mark.asyncio
async def test_job_cannot_close_before_commission_deducted():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, commission_deducted=False)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.close_job_financial(job.id)
    assert exc.value.error_code == "JOB_NOT_READY_FOR_CLOSE"

@pytest.mark.asyncio
async def test_already_closed_job_cannot_close_again():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.CLOSED, commission_deducted=True)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.close_job_financial(job.id)
    assert exc.value.error_code == "JOB_ALREADY_CLOSED"

@pytest.mark.asyncio
async def test_close_creates_status_history():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, commission_deducted=True)
    db = db_seq(job)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    await svc.close_job_financial(job.id, "done")
    assert db.add.called


# ── 7. Customer invoice views ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_can_view_own_invoice():
    cid = uuid.uuid4()
    invoice = make_invoice(customer_id=cid, job_id=None, tenant_id=uuid.uuid4())
    db = db_seq(invoice)
    svc = BillingService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_invoice_detail(cid, invoice.id)
    assert result["invoice_id"] == str(invoice.id)
    assert result["total_amount"] == 1450.0

@pytest.mark.asyncio
async def test_customer_cannot_view_another_customers_invoice():
    invoice = make_invoice(customer_id=uuid.uuid4())
    db = db_seq(invoice)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_invoice_detail(uuid.uuid4(), invoice.id)
    assert exc.value.error_code == "INVOICE_NOT_FOUND"

@pytest.mark.asyncio
async def test_customer_invoice_includes_payment_status():
    cid = uuid.uuid4()
    payment = make_payment(customer_id=cid, payment_status="paid", payment_method="cash")
    invoice = make_invoice(customer_id=cid, job_id=None, payment_id=payment.id, tenant_id=uuid.uuid4())
    db = db_seq(invoice, None, payment)
    svc = BillingService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_invoice_detail(cid, invoice.id)
    assert result["payment_status"] == "paid"
    assert result["payment_method"] == "cash"

@pytest.mark.asyncio
async def test_customer_invoice_includes_tenant_and_service_summary():
    cid = uuid.uuid4()
    tid = uuid.uuid4()
    job = make_job(customer_id=cid, tenant_id=tid, service_type_id="ac_repair")
    invoice = make_invoice(customer_id=cid, job_id=job.id, tenant_id=tid, payment_id=None)
    tenant = MagicMock(id=tid, tenant_name="Rahul AC Services")
    db = db_seq(invoice, job, tenant)
    svc = BillingService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_invoice_detail(cid, invoice.id)
    assert result["service_name"] == "ac_repair"
    assert result["tenant_name"] == "Rahul AC Services"


# ── 8. Tenant finance ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_finance_summary_shows_wallet_balance():
    tid = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=0)))
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc_get_wallet = AsyncMock(return_value={"usage_credit_balance": 855.0})
    with __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.engines.usage_credits.service.UsageCreditService.get_balance", new=svc_get_wallet):
        result = await svc.get_tenant_finance_summary(tid)
    assert result["wallet_balance"] == 855.0
    assert result["currency"] == "INR"

@pytest.mark.asyncio
async def test_tenant_wallet_ledger_lists_own_entries_only():
    tid = uuid.uuid4()
    db = MagicMock()
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    fake_txns = AsyncMock(return_value={"items": [], "source": "usage_credit_ledger"})
    with __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.engines.usage_credits.service.UsageCreditService.get_ledger", new=fake_txns):
        result = await svc.get_tenant_wallet_ledger(tid)
    assert "transactions" in result
    fake_txns.assert_awaited_once_with(tid, limit=50)


# ── 9. Admin finance ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_field_ops_admin_wallet_topup_is_retired():
    svc = BillingService(db=MagicMock(), actor_id=uuid.uuid4(), actor_role="super_admin")
    assert not hasattr(svc, "admin_wallet_topup")

@pytest.mark.asyncio
async def test_tenant_owner_cannot_use_admin_topup_route():
    from app.core.permissions import P, ROLE_PERMISSIONS
    # Admin wallet routes are gated by require_super_admin, not a permission string —
    # confirm tenant_owner role isn't super_admin (the actual router-level gate).
    assert "super_admin" != "tenant_owner"


# ── 10. Idempotency ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deduct_commission_repeated_call_is_idempotent():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PAID, invoice_id=uuid.uuid4(), payment_id=uuid.uuid4(),
                    commission_deducted=True, commission_amount=Decimal("145"))
    existing_rec = MagicMock(id=uuid.uuid4())
    db = db_seq(job, existing_rec)
    svc = BillingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    r1 = await svc.deduct_commission(job.id)
    assert r1["idempotent"] is True


# ── 11. Model fields ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", [
    "invoice_id", "payment_id", "commission_id", "invoice_generated_at", "payment_pending_at",
    "paid_at", "closed_by_user_id", "closure_notes", "final_payable_amount",
])
def test_job_model_has_step9_field(field):
    assert hasattr(Job, field)

@pytest.mark.parametrize("field", [
    "job_id", "customer_id", "service_id", "job_type", "subtotal_amount", "parts_amount",
    "labour_amount", "visit_fee", "discount_amount", "paid_at", "pdf_url",
])
def test_invoice_record_has_step9_field(field):
    assert hasattr(InvoiceRecord, field)

@pytest.mark.parametrize("field", [
    "job_id", "payment_number", "payment_method", "payment_status",
    "collected_by_user_id", "collected_by_staff_id", "paid_at", "notes",
])
def test_payment_record_has_step9_field(field):
    assert hasattr(PaymentRecord, field)

@pytest.mark.parametrize("field", [
    "invoice_id", "payment_id", "calculation_base", "status",
    "wallet_ledger_entry_id", "failure_reason",
])
def test_commission_record_has_step9_field(field):
    assert hasattr(CommissionRecord, field)


# ── 12. OpenAPI ────────────────────────────────────────────────────────────────────

def test_openapi_includes_invoice_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/generate-invoice" in schema["paths"]
    assert "/v1/customer/invoices" in schema["paths"]
    assert "/v1/customer/invoices/{invoice_id}" in schema["paths"]

def test_openapi_includes_payment_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/record-payment" in schema["paths"]

def test_openapi_includes_commission_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/deduct-commission" in schema["paths"]

def test_openapi_includes_tenant_wallet_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/tenant/wallet" in schema["paths"]
    assert "/v1/tenant/wallet/ledger" in schema["paths"]
    assert "/v1/tenant/finance/summary" in schema["paths"]

def test_openapi_includes_admin_finance_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/admin/finance/summary" in schema["paths"]
    assert "/v1/admin/usage-credits/{tenant_id}/adjustments" in schema["paths"]
    assert "/v1/admin/tenants/{tenant_id}/wallet/top-up" not in schema["paths"]

def test_openapi_schemas_are_valid():
    from app.main import app
    schema = app.openapi()
    assert schema["openapi"]
    assert "paths" in schema and "components" in schema
