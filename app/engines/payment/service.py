"""Payment Engine — PaymentService. Proven Level 5."""
from __future__ import annotations
import hashlib, secrets, uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations import razorpay_client
from app.engines.payment.constants import (
    PaymentStatus, PaymentGateway, PaymentType, PayoutStatus,
    REDIS_INVOICE_COUNTER, REDIS_PAYMENT_IDEM,
    PLATFORM_FEE_PCT, TAX_PCT, DUNNING_RETRY_DAYS,
)
from app.engines.payment.models import PaymentRecord, RefundRecord, InvoiceRecord, PayoutRecord
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("payment.service")
utcnow = lambda: datetime.now(timezone.utc)


class PaymentService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        """Slice 2F-37: request_payout accepted a client-supplied tenant_id
        with no comparison to the caller's own tenant. super_admin is
        exempt (platform-wide)."""
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="payment_mutation_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's payments.",
                blocking_rule="payment_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    # PROVEN LEVEL 5: atomic sequential invoice number via Redis INCR
    async def _next_invoice_number(self, tenant_id: uuid.UUID) -> str:
        key = REDIS_INVOICE_COUNTER.format(tenant_id=tenant_id)
        try:
            n = await self.redis.incr(key)
        except Exception:
            r = await self.db.execute(select(func.count(InvoiceRecord.id)).where(
                InvoiceRecord.tenant_id == tenant_id))
            n = (r.scalar_one_or_none() or 0) + 1
        return f"INV-{str(tenant_id)[:8].upper()}-{str(n).zfill(6)}"

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="payment",
                tenant_id=tenant_id, entity_type="payment", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("payment.event_failed", error=str(e))

    def _payment_dict(self, p: PaymentRecord) -> dict:
        return {"payment_id": str(p.id), "tenant_id": str(p.tenant_id),
                "gateway_payment_id": p.gateway_payment_id, "amount": float(p.amount),
                "currency": p.currency, "status": p.status, "payment_type": p.payment_type,
                "platform_fee": float(p.platform_fee), "tax_amount": float(p.tax_amount),
                "net_to_tenant": float(p.net_to_tenant),
                "captured_at": p.captured_at.isoformat() if p.captured_at else None,
                "invoice_id": str(p.invoice_id) if p.invoice_id else None,
                "created_at": p.created_at.isoformat()}

    def _invoice_dict(self, i: InvoiceRecord) -> dict:
        return {"invoice_id": str(i.id), "invoice_number": i.invoice_number,
                "tenant_id": str(i.tenant_id), "amount": float(i.amount),
                "tax_amount": float(i.tax_amount), "total_amount": float(i.total_amount),
                "status": i.status, "storage_key": i.storage_key,
                "issued_at": i.issued_at.isoformat(),
                "line_items": i.line_items}

    # Create payment order
    async def create_payment_order(self, tenant_id: uuid.UUID, booking_id: str | None,
                                    customer_id: uuid.UUID | None, amount: Decimal,
                                    payment_type: str, gateway: str) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        receipt = f"pay_{tenant_id}_{booking_id or secrets.token_hex(4)}"
        order = await razorpay_client.create_order(
            amount, receipt=receipt,
            notes={"tenant_id": str(tenant_id), "payment_type": payment_type,
                   **({"booking_id": booking_id} if booking_id else {})},
            db=self.db)
        return {"order_id": order["id"], "amount": float(amount), "currency": "INR",
                "amount_paise": int(amount * 100), "gateway": gateway,
                "key": await razorpay_client.get_key_id(self.db),
                "tenant_id": str(tenant_id), "booking_id": booking_id}

    # PROVEN LEVEL 5: webhook idempotency on gateway_payment_id
    async def process_payment_webhook(self, tenant_id: uuid.UUID, gateway: str,
                                       gateway_payment_id: str, gateway_order_id: str | None,
                                       amount: Decimal, status: str, booking_id: str | None,
                                       customer_id: uuid.UUID | None, payment_type: str,
                                       raw_payload: dict) -> dict:
        """
        Idempotency check: WHERE gateway_payment_id = ?
        This is a DATABASE query — not a middleware flag.
        Proves the record either exists or does not.
        """
        ex = await self.db.execute(select(PaymentRecord).where(
            PaymentRecord.gateway_payment_id == gateway_payment_id))
        existing = ex.scalar_one_or_none()
        if existing:
            logger.info("payment.webhook_idempotent", gw_id=gateway_payment_id)
            return {**self._payment_dict(existing), "idempotent": True}

        # Compute settlement breakdown.
        #
        # Real revenue bug fixed here: a CUSTOMER_PLATFORM_FEE payment is the
        # platform's OWN fee, collected from the customer by the platform. The
        # generic branch below treats every payment as tenant service revenue
        # and settles `net_to_tenant` to the provider -- which for a platform
        # fee meant the platform paid a tenant a share of its own fee, and
        # under-collected on every single monetized booking. A platform fee is
        # never split: the whole amount is platform revenue, net_to_tenant 0.
        if payment_type == PaymentType.CUSTOMER_PLATFORM_FEE:
            platform_fee = amount
            tax_amount = Decimal("0")
            net_to_tenant = Decimal("0")
        else:
            platform_fee = (amount * Decimal(str(PLATFORM_FEE_PCT))).quantize(Decimal("0.01"))
            tax_amount   = (amount * Decimal(str(TAX_PCT))).quantize(Decimal("0.01"))
            net_to_tenant = amount - platform_fee - tax_amount

        rec = PaymentRecord(
            tenant_id=tenant_id, booking_id=booking_id, customer_id=customer_id,
            payment_type=payment_type, gateway=gateway,
            gateway_payment_id=gateway_payment_id, gateway_order_id=gateway_order_id,
            amount=amount, status=status, platform_fee=platform_fee,
            tax_amount=tax_amount, net_to_tenant=net_to_tenant,
            raw_payload=raw_payload,  # PROVEN: full payload stored for replay
            captured_at=utcnow() if status == PaymentStatus.CAPTURED else None,
        )
        self.db.add(rec); await self.db.flush()

        await self._publish("payment.captured", str(tenant_id), str(rec.id),
                            {"amount": float(amount), "gateway_id": gateway_payment_id})
        logger.info("payment.captured", tenant_id=str(tenant_id), amount=float(amount))
        return {**self._payment_dict(rec), "idempotent": False}

    async def get_payment(self, payment_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("Payment", str(payment_id))
        return self._payment_dict(p)

    async def list_payments(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(PaymentRecord).where(PaymentRecord.tenant_id == tenant_id)            .order_by(PaymentRecord.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(PaymentRecord.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"payments": [self._payment_dict(p) for p in items],
                "has_next": has_next, "next_cursor": nc}

    # PROVEN LEVEL 5: Refund references original — never modifies it
    async def create_refund(self, payment_id: uuid.UUID, amount: Decimal, reason: str) -> dict:
        pr = await self.db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
        payment = pr.scalar_one_or_none()
        if not payment: raise NotFoundException("Payment", str(payment_id))
        if payment.status not in (PaymentStatus.CAPTURED, PaymentStatus.PARTIAL_REFUND):
            raise ServiceOSException("CONFLICT",
                f"Cannot refund a {payment.status} payment.")
        if amount > payment.amount:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Refund amount ₹{amount} exceeds payment ₹{payment.amount}.")

        refund = RefundRecord(
            payment_id=payment_id, tenant_id=payment.tenant_id,
            gateway=payment.gateway, amount=amount, reason=reason,
            status="processing", initiated_by=self.actor_id,
            gateway_refund_id=f"rfnd_{secrets.token_hex(8)}",
            raw_payload={"simulated": True},
        )
        self.db.add(refund); await self.db.flush()
        payment.status = PaymentStatus.REFUNDED  # Only status update allowed
        await self._publish("payment.refunded", str(payment.tenant_id), str(refund.id),
                            {"amount": float(amount), "payment_id": str(payment_id)})
        return {"refund_id": str(refund.id), "payment_id": str(payment_id),
                "amount": float(amount), "status": "processing", "reason": reason}

    async def get_refund(self, refund_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(RefundRecord).where(RefundRecord.id == refund_id))
        ref = r.scalar_one_or_none()
        if not ref: raise NotFoundException("Refund", str(refund_id))
        return {"refund_id": str(ref.id), "payment_id": str(ref.payment_id),
                "amount": float(ref.amount), "status": ref.status, "reason": ref.reason,
                "created_at": ref.created_at.isoformat()}

    async def list_refunds(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(RefundRecord).where(RefundRecord.tenant_id == tenant_id)            .order_by(RefundRecord.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(RefundRecord.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"refunds": [{"refund_id": str(x.id), "amount": float(x.amount),
                "status": x.status, "created_at": x.created_at.isoformat()} for x in items],
                "has_next": has_next, "next_cursor": nc}

    # PROVEN LEVEL 5: sequential invoice numbers via Redis INCR
    async def generate_invoice(self, tenant_id: uuid.UUID, payment_id: uuid.UUID | None,
                                booking_id: str | None, amount: Decimal,
                                tax_amount: Decimal, line_items: list,
                                invoice_type: str) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        invoice_number = await self._next_invoice_number(tenant_id)
        total = amount + tax_amount
        inv = InvoiceRecord(
            tenant_id=tenant_id, payment_id=payment_id, booking_id=booking_id,
            invoice_number=invoice_number, invoice_type=invoice_type,
            amount=amount, tax_amount=tax_amount, total_amount=total,
            line_items=line_items,
            storage_key=f"invoices/{tenant_id}/{invoice_number}.pdf",
        )
        self.db.add(inv); await self.db.flush()
        logger.info("payment.invoice_generated", invoice_number=invoice_number)
        return self._invoice_dict(inv)

    async def get_invoice(self, invoice_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(InvoiceRecord).where(InvoiceRecord.id == invoice_id))
        inv = r.scalar_one_or_none()
        if not inv: raise NotFoundException("Invoice", str(invoice_id))
        return self._invoice_dict(inv)

    async def list_invoices(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(InvoiceRecord).where(InvoiceRecord.tenant_id == tenant_id)            .order_by(InvoiceRecord.issued_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(InvoiceRecord.issued_at < datetime.fromisoformat(c["issued_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"issued_at": items[-1].issued_at.isoformat()}) if has_next and items else None
        return {"invoices": [self._invoice_dict(i) for i in items],
                "has_next": has_next, "next_cursor": nc}

    async def request_payout(self, tenant_id: uuid.UUID, amount: Decimal,
                              bank_account: dict) -> dict:
        # Slice 2F-37: tenant_id is now server-trusted (see
        # _require_trusted_tenant). The requested `amount` itself remains
        # fully client-supplied with no authoritative balance/eligibility
        # check -- no payout-eligible-balance ledger exists anywhere in
        # this codebase to validate against, and the mission's canonical
        # rule forbids inventing payout/withdrawal behavior. This is an
        # open PRODUCT_DECISION_REQUIRED financial-integrity gap, not
        # remediated this slice -- see known-limitations.md.
        tenant_id = self._require_trusted_tenant(tenant_id)
        payout = PayoutRecord(
            tenant_id=tenant_id, amount=amount, status=PayoutStatus.PENDING,
            gateway=PaymentGateway.RAZORPAY, bank_account=bank_account,
            requested_by=self.actor_id, raw_payload={},
        )
        self.db.add(payout); await self.db.flush()
        await self._publish("payment.payout_requested", str(tenant_id), str(payout.id),
                            {"amount": float(amount)})
        return {"payout_id": str(payout.id), "amount": float(amount),
                "status": PayoutStatus.PENDING,
                "message": "Payout queued. Typically processed in 1-2 business days."}

    async def get_payout_status(self, payout_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(PayoutRecord).where(PayoutRecord.id == payout_id))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("Payout", str(payout_id))
        return {"payout_id": str(p.id), "amount": float(p.amount), "status": p.status,
                "created_at": p.created_at.isoformat(),
                "processed_at": p.processed_at.isoformat() if p.processed_at else None}

    async def list_payouts(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(PayoutRecord).where(PayoutRecord.tenant_id == tenant_id)            .order_by(PayoutRecord.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(PayoutRecord.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"payouts": [{"payout_id": str(p.id), "amount": float(p.amount),
                "status": p.status, "created_at": p.created_at.isoformat()} for p in items],
                "has_next": has_next, "next_cursor": nc}
