"""Field Ops Engine — Step 9: Payment / Invoice / Commission Closure Flow.

Reuses existing financial infrastructure rather than duplicating it:
  - InvoiceRecord / PaymentRecord (app.engines.payment.models) — extended
    with job-level fields in this step.
  - CommissionRecord / TenantWallet / WalletTransaction
    (app.engines.platform_commerce.models) — untouched ledger primitives.
  - CommerceService.deduct_commission() — already idempotent on job_id;
    reused as-is, not reimplemented.
This service only adds the job-closure orchestration on top.
"""
from __future__ import annotations
import random, uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.field_ops.constants import JS, JobType, get_allowed_transitions as _resolve_transitions
from app.engines.field_ops.models import Job, JobStatusHistory
from app.engines.payment.models import InvoiceRecord, PaymentRecord
from app.engines.platform_commerce.models import CommissionRecord
from app.exceptions import ServiceOSException, NotFoundException
from app.schemas.base import encode_cursor, decode_cursor

utcnow = lambda: datetime.now(timezone.utc)
VALID_PAYMENT_METHODS = ("cash", "upi", "card", "bank_transfer", "online_gateway", "external")


class BillingService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role; self.actor_tenant_id = actor_tenant_id

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _generate_invoice_number(self) -> str:
        return f"INV-{utcnow().strftime('%Y%m')}-{random.randint(10000, 99999)}"

    def _generate_payment_number(self) -> str:
        return f"PAY-{utcnow().strftime('%Y%m')}-{random.randint(10000, 99999)}"

    async def _write_history(self, job: Job, from_status: str | None, to_status: str, reason: str | None):
        self.db.add(JobStatusHistory(
            job_id=job.id, tenant_id=job.tenant_id, from_status=from_status, to_status=to_status,
            changed_by=self.actor_id, changed_by_role=self.actor_role, reason=reason))

    def _invoice_dict(self, inv: InvoiceRecord) -> dict:
        return {
            "invoice_id": str(inv.id), "invoice_number": inv.invoice_number,
            "job_id": str(inv.job_id) if inv.job_id else None,
            "tenant_id": str(inv.tenant_id), "customer_id": str(inv.customer_id) if inv.customer_id else None,
            "booking_id": inv.booking_id, "service_id": str(inv.service_id) if inv.service_id else None,
            "job_type": inv.job_type, "subtotal_amount": float(inv.subtotal_amount) if inv.subtotal_amount is not None else None,
            "parts_amount": float(inv.parts_amount), "labour_amount": float(inv.labour_amount),
            "visit_fee": float(inv.visit_fee), "discount_amount": float(inv.discount_amount),
            "tax_amount": float(inv.tax_amount), "total_amount": float(inv.total_amount),
            "currency": inv.currency, "status": inv.status, "pdf_url": inv.pdf_url,
            "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "due_at": inv.due_at.isoformat() if inv.due_at else None,
        }

    def _payment_dict(self, pay: PaymentRecord) -> dict:
        return {
            "payment_id": str(pay.id), "payment_number": pay.payment_number,
            "job_id": str(pay.job_id) if pay.job_id else None,
            "invoice_id": str(pay.invoice_id) if pay.invoice_id else None,
            "tenant_id": str(pay.tenant_id), "customer_id": str(pay.customer_id) if pay.customer_id else None,
            "amount": float(pay.amount), "currency": pay.currency,
            "payment_method": pay.payment_method, "payment_status": pay.payment_status,
            "notes": pay.notes, "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
            "created_at": pay.created_at.isoformat() if pay.created_at else None,
        }

    async def _get_job_for_billing(self, job_id: uuid.UUID) -> Job:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        if self.actor_role in ("staff", "technician") and job.assigned_staff_id != self.actor_id:
            raise ServiceOSException("STAFF_NOT_ASSIGNED_TO_JOB",
                "This job is not assigned to you.", status_code=403)
        if (self.actor_role == "tenant_owner" and self.actor_tenant_id is not None
                and job.tenant_id != self.actor_tenant_id):
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        return job

    # ── Invoice generation ────────────────────────────────────────────────────
    async def generate_invoice(self, job_id: uuid.UUID, data: dict) -> dict:
        job = await self._get_job_for_billing(job_id)
        if job.invoice_id is not None:
            raise ServiceOSException("INVOICE_ALREADY_EXISTS",
                "This job already has an active invoice.", status_code=409,
                context={"invoice_id": str(job.invoice_id)})
        if job.status not in (JS.SIGNED_OFF, JS.COMPLETED):
            raise ServiceOSException("JOB_NOT_READY_FOR_INVOICE",
                f"Job must be signed_off or completed to invoice. Current: {job.status}",
                status_code=422, context={"current_status": job.status})

        amounts = {k: Decimal(str(data.get(k, 0))) for k in
                   ("labour_amount", "parts_amount", "visit_fee", "discount_amount", "tax_amount")}
        for name, amt in amounts.items():
            if amt < 0:
                raise ServiceOSException("INVALID_INVOICE_AMOUNT", f"{name} cannot be negative.", status_code=422)
        subtotal = amounts["labour_amount"] + amounts["parts_amount"] + amounts["visit_fee"]
        total = subtotal + amounts["tax_amount"] - amounts["discount_amount"]
        if total < 0:
            raise ServiceOSException("INVALID_INVOICE_AMOUNT", "total_amount cannot be negative.", status_code=422)

        invoice = InvoiceRecord(
            tenant_id=job.tenant_id, job_id=job.id, customer_id=job.customer_id,
            booking_id=job.booking_id, service_id=job.service_id, job_type=job.job_type,
            invoice_number=self._generate_invoice_number(), invoice_type="job_invoice",
            amount=subtotal, subtotal_amount=subtotal,
            labour_amount=amounts["labour_amount"], parts_amount=amounts["parts_amount"],
            visit_fee=amounts["visit_fee"], discount_amount=amounts["discount_amount"],
            tax_amount=amounts["tax_amount"], total_amount=total, status="issued",
            line_items=data.get("line_items", []),
            meta={"notes": data.get("notes")} if data.get("notes") else {},
        )
        self.db.add(invoice)
        await self.db.flush()

        from_status = job.status
        job.invoice_id = invoice.id
        job.invoice_generated_at = utcnow()
        job.final_payable_amount = total
        job.status = JS.INVOICE_GENERATED
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.INVOICE_GENERATED,
                                   data.get("notes") or "Invoice generated")
        return {"invoice_id": str(invoice.id), "invoice_number": invoice.invoice_number,
                "job_id": str(job.id), "status": invoice.status, "total_amount": float(total),
                "currency": invoice.currency, "job_status": job.status,
                "message": "Invoice generated successfully"}

    # ── Payment recording ─────────────────────────────────────────────────────
    async def record_payment(self, job_id: uuid.UUID, data: dict) -> dict:
        job = await self._get_job_for_billing(job_id)
        if job.payment_id is not None:
            raise ServiceOSException("PAYMENT_ALREADY_RECORDED",
                "A payment has already been recorded for this job.", status_code=409,
                context={"payment_id": str(job.payment_id)})
        if not job.invoice_id:
            raise ServiceOSException("JOB_NOT_READY_FOR_PAYMENT",
                "Job must have an invoice before a payment can be recorded.", status_code=422)

        ir = await self.db.execute(select(InvoiceRecord).where(InvoiceRecord.id == job.invoice_id))
        invoice = ir.scalar_one_or_none()
        if not invoice:
            raise ServiceOSException("INVOICE_NOT_FOUND", "Invoice not found for this job.", status_code=404)
        if invoice.status == "paid":
            raise ServiceOSException("INVOICE_ALREADY_PAID", "Invoice already paid.", status_code=409)

        method = data.get("payment_method")
        if method not in VALID_PAYMENT_METHODS:
            raise ServiceOSException("INVALID_PAYMENT_METHOD",
                f"payment_method must be one of {VALID_PAYMENT_METHODS}.", status_code=422)

        amount = Decimal(str(data.get("amount", 0)))
        if amount != invoice.total_amount:
            raise ServiceOSException("PAYMENT_AMOUNT_MISMATCH",
                f"Payment amount {amount} does not match invoice total {invoice.total_amount}.",
                status_code=422, context={"expected": float(invoice.total_amount), "received": float(amount)})
        # Customer Service Credit rule: technician must collect only payable_amount
        # (quoted_price minus any credit applied) — never the full quoted price.
        if job.payable_amount is not None and amount != job.payable_amount:
            raise ServiceOSException("PAYMENT_AMOUNT_MISMATCH",
                "Amount collected must match payable-to-provider amount.",
                status_code=422, context={"expected": float(job.payable_amount), "received": float(amount)})

        payment_status = data.get("payment_status", "paid")
        payment = PaymentRecord(
            tenant_id=job.tenant_id, customer_id=job.customer_id, job_id=job.id,
            invoice_id=invoice.id, payment_number=self._generate_payment_number(),
            payment_type="final", gateway=method if method == "online_gateway" else "manual",
            gateway_payment_id=f"manual:{job.id}:{uuid.uuid4()}",
            amount=amount, payment_method=method, payment_status=payment_status,
            status=payment_status, notes=data.get("notes"),
            collected_by_user_id=self.actor_id,
            collected_by_staff_id=self.actor_id if self.actor_role in ("staff", "technician") else None,
        )
        self.db.add(payment)
        await self.db.flush()

        job.payment_id = payment.id
        from_status = job.status
        if payment_status == "paid":
            payment.paid_at = utcnow()
            invoice.status = "paid"
            invoice.paid_at = utcnow()
            job.status = JS.PAID
            job.paid_at = utcnow()
        else:
            job.status = JS.PAYMENT_PENDING
            job.payment_pending_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, job.status,
                                   data.get("notes") or "Payment recorded")

        if payment_status == "paid" and not job.commission_deducted:
            try:
                await self.deduct_commission(job.id)
            except ServiceOSException:
                pass  # payment stays recorded even if commission deduction fails

        return {"payment_id": str(payment.id), "payment_number": payment.payment_number,
                "invoice_id": str(invoice.id), "job_id": str(job.id), "amount": float(amount),
                "payment_status": payment.payment_status, "payment_method": method,
                "job_status": job.status, "message": "Payment recorded successfully"}

    # ── Commission deduction (wraps CommerceService — already idempotent) ────
    async def deduct_commission(self, job_id: uuid.UUID) -> dict:
        job = await self._get_job_for_billing(job_id)
        if not job.invoice_id:
            raise ServiceOSException("JOB_NOT_READY_FOR_PAYMENT",
                "Job must have an invoice before commission can be deducted.", status_code=422)
        if job.commission_deducted:
            cr = await self.db.execute(select(CommissionRecord).where(CommissionRecord.job_id == str(job.id)))
            existing = cr.scalar_one_or_none()
            return {"job_id": str(job.id), "commission_id": str(existing.id) if existing else None,
                    "commission_amount": float(job.commission_amount or 0),
                    "commission_status": "deducted", "idempotent": True,
                    "message": "Commission already deducted"}

        from app.engines.platform_commerce.service import CommerceService
        commerce = CommerceService(self.db, actor_id=self.actor_id, actor_role=self.actor_role)
        try:
            result = await commerce.deduct_commission(
                tid=job.tenant_id, job_id=str(job.id),
                job_value=job.final_payable_amount or job.final_price or job.quoted_price or Decimal("0"),
                description=f"Commission: {job.job_number}")
        except ServiceOSException as e:
            if e.error_code == "COMMISSION_WALLET_EMPTY":
                raise ServiceOSException("INSUFFICIENT_WALLET_BALANCE",
                    "Tenant wallet has insufficient credits to deduct commission for this job.",
                    status_code=402, context={"job_id": str(job.id)})
            raise

        cr = await self.db.execute(select(CommissionRecord).where(CommissionRecord.job_id == str(job.id)))
        rec = cr.scalar_one_or_none()
        if rec:
            rec.invoice_id = job.invoice_id
            rec.payment_id = job.payment_id

        job.commission_deducted = True
        job.commission_amount = Decimal(str(result["commission_amount"]))
        job.commission_id = rec.id if rec else None

        return {"job_id": str(job.id), "commission_id": str(rec.id) if rec else None,
                "commission_rate": float(result.get("effective_rate", 0)),
                "commission_amount": float(result["commission_amount"]),
                "wallet_balance_before": float(result["wallet_balance_before"]),
                "wallet_balance_after": float(result["wallet_balance_after"]),
                "commission_status": "deducted", "idempotent": result.get("idempotent", False),
                "message": "Commission deducted successfully"}

    # ── Job close (financial) ─────────────────────────────────────────────────
    async def close_job_financial(self, job_id: uuid.UUID, closure_notes: str | None = None) -> dict:
        job = await self._get_job_for_billing(job_id)
        if job.status == JS.CLOSED:
            raise ServiceOSException("JOB_ALREADY_CLOSED", "Job is already closed.", status_code=409)
        if job.status != JS.PAID:
            raise ServiceOSException("JOB_NOT_READY_FOR_CLOSE",
                f"Job must be paid before it can close. Current: {job.status}", status_code=422,
                context={"current_status": job.status})
        if not job.commission_deducted:
            raise ServiceOSException("JOB_NOT_READY_FOR_CLOSE",
                "Commission must be deducted before the job can close.", status_code=422)

        from_status = job.status
        job.status = JS.CLOSED
        job.closed_at = utcnow()
        job.closed_by_user_id = self.actor_id
        job.closure_notes = closure_notes
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.CLOSED, closure_notes or "Job closed")

        # Propagate completion back to the originating Booking — previously the
        # booking stayed at "converted_to_job" forever once the job financially
        # closed, so admin/tenant/customer booking views never showed "completed"
        # even though the job itself was fully done and paid.
        if job.booking_id:
            from app.engines.booking.models import Booking, BookingStatusHistory
            from app.engines.booking.constants import BS
            br = await self.db.execute(select(Booking).where(Booking.id == job.booking_id))
            booking = br.scalar_one_or_none()
            if booking and booking.status != BS.COMPLETED:
                booking_from_status = booking.status
                booking.status = BS.COMPLETED
                booking.status_updated_at = utcnow()
                self.db.add(BookingStatusHistory(
                    booking_id=booking.id, tenant_id=booking.tenant_id,
                    from_status=booking_from_status, to_status=BS.COMPLETED,
                    changed_by=self.actor_id, changed_by_role=self.actor_role,
                    reason="Job financially closed",
                    meta={"job_id": str(job.id)},
                ))

        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type="job.closed", engine_id="field_ops",
                tenant_id=str(job.tenant_id), entity_type="job", entity_id=str(job.id),
                payload={"job_number": job.job_number}, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception:
            pass
        return {"job_id": str(job.id), "status": job.status,
                "closed_at": job.closed_at.isoformat(), "message": "Job closed successfully"}

    # ── One-step atomic financial close ───────────────────────────────────────
    async def financial_close(self, job_id: uuid.UUID, data: dict) -> dict:
        invoice_result = await self.generate_invoice(job_id, data)
        payment_result = await self.record_payment(job_id, {
            "amount": invoice_result["total_amount"],
            "payment_method": data.get("payment_method"),
            "payment_status": data.get("payment_status", "paid"),
            "notes": data.get("closure_notes"),
        })
        commission_result = None
        if payment_result["payment_status"] == "paid":
            try:
                commission_result = await self.deduct_commission(job_id)
            except ServiceOSException:
                commission_result = {"commission_status": "failed"}
        close_result = None
        if payment_result["job_status"] == JS.PAID:
            close_result = await self.close_job_financial(job_id, data.get("closure_notes"))
        return {"invoice": invoice_result, "payment": payment_result,
                "commission": commission_result, "close": close_result}

    # ── Customer invoice views ────────────────────────────────────────────────
    async def get_customer_invoices(self, customer_id: uuid.UUID, limit: int = 50,
                                     cursor: str | None = None) -> dict:
        q = select(InvoiceRecord).where(InvoiceRecord.customer_id == customer_id).order_by(
            InvoiceRecord.issued_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(InvoiceRecord.issued_at < datetime.fromisoformat(c["issued_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        rows = r.scalars().all()
        has_next = len(rows) > limit; rows = rows[:limit]
        nc = encode_cursor({"issued_at": rows[-1].issued_at.isoformat()}) if has_next and rows else None
        return {"invoices": [self._invoice_dict(i) for i in rows], "has_next": has_next, "next_cursor": nc}

    async def get_customer_invoice_detail(self, customer_id: uuid.UUID, invoice_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(InvoiceRecord).where(InvoiceRecord.id == invoice_id))
        inv = r.scalar_one_or_none()
        if not inv or inv.customer_id != customer_id:
            raise ServiceOSException("INVOICE_NOT_FOUND", f"Invoice '{invoice_id}' not found.", status_code=404)
        d = self._invoice_dict(inv)
        if inv.job_id:
            jr = await self.db.execute(select(Job).where(Job.id == inv.job_id))
            job = jr.scalar_one_or_none()
            if job:
                d["service_name"] = job.service_type_id
        if inv.tenant_id:
            from app.engines.tenant_engine.models import Tenant
            tr = await self.db.execute(select(Tenant).where(Tenant.id == inv.tenant_id))
            tenant = tr.scalar_one_or_none()
            if tenant:
                d["tenant_name"] = tenant.tenant_name
        if inv.payment_id:
            pr = await self.db.execute(select(PaymentRecord).where(PaymentRecord.id == inv.payment_id))
            payment = pr.scalar_one_or_none()
            if payment:
                d["payment_status"] = payment.payment_status
                d["payment_method"] = payment.payment_method
        return d

    async def get_customer_job_invoice(self, customer_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        jr = await self.db.execute(select(Job).where(Job.id == job_id))
        job = jr.scalar_one_or_none()
        if not job or job.customer_id != customer_id:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        if not job.invoice_id:
            raise ServiceOSException("INVOICE_NOT_FOUND", "No invoice has been generated for this job yet.",
                                      status_code=404)
        return await self.get_customer_invoice_detail(customer_id, job.invoice_id)

    # ── Tenant finance views ──────────────────────────────────────────────────
    async def get_tenant_finance_summary(self, tenant_id: uuid.UUID) -> dict:
        from app.engines.usage_credits.service import UsageCreditService
        credit = await UsageCreditService(self.db, actor_id=self.actor_id).get_balance(tenant_id)

        inv_count = await self.db.execute(select(func.count(InvoiceRecord.id)).where(
            InvoiceRecord.tenant_id == tenant_id))
        inv_total = await self.db.execute(select(func.sum(InvoiceRecord.total_amount)).where(
            InvoiceRecord.tenant_id == tenant_id))
        paid_total = await self.db.execute(select(func.sum(InvoiceRecord.total_amount)).where(
            InvoiceRecord.tenant_id == tenant_id, InvoiceRecord.status == "paid"))
        commission_total = await self.db.execute(select(func.sum(CommissionRecord.commission_amount)).where(
            CommissionRecord.tenant_id == tenant_id))

        return {"wallet_balance": credit["usage_credit_balance"],
                "total_invoices": inv_count.scalar_one_or_none() or 0,
                "total_invoice_amount": float(inv_total.scalar_one_or_none() or 0),
                "total_paid_amount": float(paid_total.scalar_one_or_none() or 0),
                "total_commission_deducted": float(commission_total.scalar_one_or_none() or 0),
                "pending_commission": 0, "currency": "INR"}

    async def get_tenant_invoices(self, tenant_id: uuid.UUID, status: str | None = None,
                                   limit: int = 50, cursor: str | None = None) -> dict:
        q = select(InvoiceRecord).where(InvoiceRecord.tenant_id == tenant_id).order_by(
            InvoiceRecord.issued_at.desc())
        if status: q = q.where(InvoiceRecord.status == status)
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        rows = r.scalars().all()
        has_next = len(rows) > limit; rows = rows[:limit]
        return {"invoices": [self._invoice_dict(i) for i in rows], "has_next": has_next}

    async def get_tenant_payments(self, tenant_id: uuid.UUID, limit: int = 50) -> dict:
        q = select(PaymentRecord).where(PaymentRecord.tenant_id == tenant_id).order_by(
            PaymentRecord.created_at.desc()).limit(limit)
        r = await self.db.execute(q)
        rows = r.scalars().all()
        return {"payments": [self._payment_dict(p) for p in rows]}

    async def get_tenant_commissions(self, tenant_id: uuid.UUID, limit: int = 50) -> dict:
        from app.engines.platform_commerce.service import CommerceService
        return await CommerceService(self.db, actor_id=self.actor_id).get_commission_history(
            tenant_id, limit, None)

    async def get_tenant_wallet(self, tenant_id: uuid.UUID) -> dict:
        from app.engines.usage_credits.service import UsageCreditService
        credit = await UsageCreditService(self.db, actor_id=self.actor_id).get_balance(tenant_id)
        return {
            "tenant_id": str(tenant_id),
            "credit_balance": credit["usage_credit_balance"],
            "source": credit["source"],
        }

    async def get_tenant_wallet_ledger(self, tenant_id: uuid.UUID, limit: int = 50,
                                        cursor: str | None = None) -> dict:
        from app.engines.usage_credits.service import UsageCreditService
        ledger = await UsageCreditService(self.db, actor_id=self.actor_id).get_ledger(
            tenant_id, limit=limit,
        )
        return {
            "transactions": ledger["items"],
            "has_next": False,
            "next_cursor": None,
            "source": ledger["source"],
        }

    # ── Admin (super_admin, platform-wide) ────────────────────────────────────
    async def admin_finance_summary(self) -> dict:
        inv_total = await self.db.execute(select(func.sum(InvoiceRecord.total_amount)))
        commission_total = await self.db.execute(select(func.sum(CommissionRecord.commission_amount)))
        payment_count = await self.db.execute(select(func.count(PaymentRecord.id)))
        return {"total_invoice_amount": float(inv_total.scalar_one_or_none() or 0),
                "total_commission_collected": float(commission_total.scalar_one_or_none() or 0),
                "total_payments": payment_count.scalar_one_or_none() or 0, "currency": "INR"}

    async def admin_list_invoices(self, limit: int = 50) -> dict:
        r = await self.db.execute(select(InvoiceRecord).order_by(InvoiceRecord.issued_at.desc()).limit(limit))
        return {"invoices": [self._invoice_dict(i) for i in r.scalars().all()]}

    async def admin_list_payments(self, limit: int = 50) -> dict:
        r = await self.db.execute(select(PaymentRecord).order_by(PaymentRecord.created_at.desc()).limit(limit))
        return {"payments": [self._payment_dict(p) for p in r.scalars().all()]}

    async def admin_list_commissions(self, limit: int = 50) -> dict:
        from app.engines.platform_commerce.service import CommerceService
        svc = CommerceService(self.db, actor_id=self.actor_id)
        r = await self.db.execute(select(CommissionRecord).order_by(
            CommissionRecord.deducted_at.desc()).limit(limit))
        return {"commissions": [svc._rec_dict(c) for c in r.scalars().all()]}
