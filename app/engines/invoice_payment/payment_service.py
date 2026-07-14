"""Sprint 23 — ServicePaymentService: on-site payment recording."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.invoice_payment.constants import (
    PAY_STATUS_PENDING, PAY_STATUS_COLLECTED, PAY_STATUS_VERIFIED, PAY_STATUS_FAILED,
    VALID_PAYMENT_MODES, FEV_PAYMENT_RECORDED, FEV_PAYMENT_VERIFIED,
    ERR_INVOICE_NOT_FOUND, ERR_INVOICE_ACCESS_DENIED, ERR_INVOICE_ALREADY_ISSUED,
    ERR_INVALID_PAYMENT_MODE,
    ERR_PAYMENT_ALREADY_RECORDED, ERR_PAYMENT_RECORD_NOT_FOUND, ERR_PAYMENT_ACCESS_DENIED,
    ERR_PAYMENT_AMOUNT_MISMATCH,
)
from app.engines.invoice_payment.models import (
    ServiceInvoice, ServicePaymentRecord, FinancialEvent,
)
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServicePaymentService:

    def __init__(self):
        self._inv_svc = ServiceInvoiceService()

    async def _best_effort_commission(
        self, db: AsyncSession, invoice_id: str, actor_user_id: str | None,
        request_id: str | None,
    ) -> None:
        """MODULE-L5-02: the service-invoice commission subsystem
        (ServiceCommissionService) was orphaned — nothing in the payment flow
        ever generated or deducted commission, so the platform never collected
        its cut on this whole invoice path and commission-status was perpetually
        null. Attempt generation+deduction here, AFTER the payment is durably
        committed, and never let a commission failure (e.g. insufficient provider
        credit) affect the payment: deduct_commission already records the failure
        state (COM_INSUFFICIENT_CREDIT / COM_FAILED) for admin retry."""
        from app.engines.invoice_payment.commission_service import ServiceCommissionService
        try:
            await ServiceCommissionService().deduct_commission(
                db, invoice_id, idempotency_key=f"auto-{invoice_id}",
                actor_user_id=actor_user_id, request_id=request_id,
            )
        except Exception:
            # Non-fatal: the commission record (if any) is persisted in its own
            # transaction with a failure status the admin can retry. Roll back
            # only the failed commission unit-of-work so the caller's session is
            # clean; the payment commit above is already durable.
            try:
                await db.rollback()
            except Exception:
                pass

    async def _get_payment(self, db: AsyncSession, payment_id: str) -> ServicePaymentRecord:
        res = await db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.id == uuid.UUID(payment_id))
        )
        p = res.scalar_one_or_none()
        if not p:
            raise ValueError(ERR_PAYMENT_RECORD_NOT_FOUND)
        return p

    async def _log_event(
        self, db: AsyncSession, inv: ServiceInvoice, pay: ServicePaymentRecord,
        event_type: str, actor_type: str, actor_user_id: str | None,
        new_value: dict | None = None, request_id: str | None = None,
    ) -> None:
        ev = FinancialEvent(
            id=uuid.uuid4(),
            record_type="payment",
            record_id=pay.id,
            tenant_id=inv.tenant_id,
            customer_id=inv.customer_id,
            actor_type=actor_type,
            actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
            event_type=event_type,
            new_value=new_value,
            request_id=request_id,
        )
        db.add(ev)

    # ── Record on-site payment ─────────────────────────────────────────────────

    async def record_onsite_payment(
        self, db: AsyncSession, invoice_id: str, tenant_id: str,
        payment_mode: str, collected_amount: float,
        proof_media_url: str | None, user_id: str,
        staff_member_id: str | None, request_id: str | None,
    ) -> dict:
        if payment_mode not in VALID_PAYMENT_MODES:
            # MODULE-L5-02 bug #18: this guard raised the wrong constant
            # (ERR_INVOICE_ALREADY_ISSUED) for an invalid payment mode, producing
            # a nonsensical "invoice already issued" message on the payment path.
            raise ValueError(ERR_INVALID_PAYMENT_MODE)
        # Get invoice
        res = await db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == uuid.UUID(invoice_id))
        )
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        if str(inv.tenant_id) != tenant_id:
            raise ValueError(ERR_INVOICE_ACCESS_DENIED)
        # Check for existing payment record
        res2 = await db.execute(
            select(ServicePaymentRecord).where(
                ServicePaymentRecord.invoice_id == inv.id,
                ServicePaymentRecord.payment_status.in_(
                    [PAY_STATUS_COLLECTED, PAY_STATUS_VERIFIED]
                ),
            )
        )
        if res2.scalar_one_or_none():
            raise ValueError(ERR_PAYMENT_ALREADY_RECORDED)
        now = _utcnow()
        pay = ServicePaymentRecord(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            booking_id=inv.booking_id,
            job_id=inv.job_id,
            tenant_id=inv.tenant_id,
            customer_id=inv.customer_id,
            payment_mode=payment_mode,
            payment_status=PAY_STATUS_COLLECTED,
            collected_amount=Decimal(str(collected_amount)),
            collected_by_user_id=uuid.UUID(user_id),
            collected_by_staff_member_id=uuid.UUID(staff_member_id) if staff_member_id else None,
            proof_media_url=proof_media_url,
            provider_confirmed_at=now,
        )
        db.add(pay)
        await db.flush()
        # Update invoice payment status
        await self._inv_svc.update_payment_status(db, inv.id, PAY_STATUS_COLLECTED, paid_at=now)
        await self._log_event(db, inv, pay, FEV_PAYMENT_RECORDED, "staff", user_id,
                              new_value={"payment_mode": payment_mode,
                                         "collected_amount": str(collected_amount)},
                              request_id=request_id)
        # MODULE-L5-10: book the platform's customer charge as revenue. The fee is
        # part of what the customer paid (customer_payable = service value + fee);
        # this records it as an auditable platform-revenue event so the customer
        # side of platform earnings is captured, not just displayed.
        fee = Decimal(str(getattr(inv, "platform_fee_amount", 0) or 0))
        if fee > Decimal("0"):
            from app.engines.invoice_payment.constants import FEV_PLATFORM_CUSTOMER_FEE
            await self._log_event(db, inv, pay, FEV_PLATFORM_CUSTOMER_FEE, "system", user_id,
                                  new_value={"platform_fee": str(fee),
                                             "service_value": str(inv.total_amount),
                                             "customer_payable": str(inv.customer_payable_amount)},
                                  request_id=request_id)
        await db.commit()
        await db.refresh(pay)
        result = pay.to_dict()
        # Generate + deduct platform commission best-effort (non-fatal).
        await self._best_effort_commission(db, invoice_id, user_id, request_id)
        return result

    # ── Customer confirms payment ───────────────────────────────────────────────

    async def customer_confirm_payment(
        self, db: AsyncSession, invoice_id: str, customer_id: str,
        user_id: str, request_id: str | None,
    ) -> dict:
        res = await db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == uuid.UUID(invoice_id))
        )
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        if str(inv.customer_id) != customer_id:
            raise ValueError(ERR_PAYMENT_ACCESS_DENIED)
        res2 = await db.execute(
            select(ServicePaymentRecord).where(
                ServicePaymentRecord.invoice_id == inv.id
            ).order_by(ServicePaymentRecord.created_at.desc())
        )
        pay = res2.scalar_one_or_none()
        if not pay:
            raise ValueError(ERR_PAYMENT_RECORD_NOT_FOUND)
        now = _utcnow()
        await db.execute(
            update(ServicePaymentRecord)
            .where(ServicePaymentRecord.id == pay.id)
            .values(customer_confirmed=True, customer_confirmed_at=now, updated_at=now)
        )
        await self._log_event(db, inv, pay, FEV_PAYMENT_VERIFIED, "customer", user_id,
                              request_id=request_id)
        await db.commit()
        await db.refresh(pay)
        return pay.to_dict()

    # ── Admin verify payment ───────────────────────────────────────────────────

    async def admin_verify_payment(
        self, db: AsyncSession, payment_id: str, admin_id: str, request_id: str | None,
    ) -> dict:
        pay = await self._get_payment(db, payment_id)
        now = _utcnow()
        await db.execute(
            update(ServicePaymentRecord)
            .where(ServicePaymentRecord.id == pay.id)
            .values(payment_status=PAY_STATUS_VERIFIED, admin_verified_at=now, updated_at=now)
        )
        res = await db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == pay.invoice_id)
        )
        inv = res.scalar_one_or_none()
        if inv:
            await self._log_event(db, inv, pay, FEV_PAYMENT_VERIFIED, "admin", admin_id,
                                  request_id=request_id)
        await db.commit()
        await db.refresh(pay)
        return pay.to_dict()

    # ── Get payment timeline ───────────────────────────────────────────────────

    async def get_payment_timeline(
        self, db: AsyncSession, invoice_id: str, tenant_id: str | None = None,
    ) -> list[dict]:
        # MODULE-L5-10: tenant_id was accepted and then IGNORED, so the provider
        # financial-timeline endpoint (which passes user.tenant_id) leaked every
        # other tenant's payment records — amounts, modes, timestamps — for any
        # invoice_id an attacker enumerated: a cross-tenant IDOR. Enforce the
        # tenant scope when a tenant_id is supplied. (The customer path passes
        # None and gates ownership in its router — see bug #22.)
        q = (select(ServicePaymentRecord)
             .where(ServicePaymentRecord.invoice_id == uuid.UUID(invoice_id)))
        if tenant_id is not None:
            q = q.where(ServicePaymentRecord.tenant_id == uuid.UUID(str(tenant_id)))
        q = q.order_by(ServicePaymentRecord.created_at.desc())
        res = await db.execute(q)
        return [p.to_dict() for p in res.scalars().all()]

    async def list_tenant_payments(self, db: AsyncSession, tenant_id: str) -> list[dict]:
        res = await db.execute(
            select(ServicePaymentRecord)
            .where(ServicePaymentRecord.tenant_id == uuid.UUID(tenant_id))
            .order_by(ServicePaymentRecord.created_at.desc())
        )
        return [p.to_dict() for p in res.scalars().all()]

    async def list_all_payments(
        self, db: AsyncSession, tenant_id: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        limit = min(limit, 500)
        q = select(ServicePaymentRecord).order_by(ServicePaymentRecord.created_at.desc())
        if tenant_id:
            q = q.where(ServicePaymentRecord.tenant_id == uuid.UUID(tenant_id))
        q = q.limit(limit).offset(offset)
        res = await db.execute(q)
        return [p.to_dict() for p in res.scalars().all()]
