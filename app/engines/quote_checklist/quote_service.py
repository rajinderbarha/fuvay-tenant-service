"""Sprint 22 — ServiceJobQuoteService: quote lifecycle management."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.quote_checklist.constants import (
    QS_DRAFT, QS_SENT_TO_CUSTOMER, QS_CUSTOMER_APPROVED,
    QS_CUSTOMER_REJECTED, QS_REVISION_REQUESTED, QS_CANCELLED,
    QS_SUBMITTED_TO_PROVIDER, QS_PROVIDER_APPROVED, QS_PROVIDER_REJECTED,
    QS_REVISED, QUOTE_TRANSITIONS, QUOTE_FINAL_STATUSES,
    VALID_QUOTE_TYPES, VALID_ITEM_TYPES, ITEM_TYPE_DISCOUNT,
    QEV_CREATED, QEV_ITEM_ADDED, QEV_ITEM_UPDATED, QEV_ITEM_REMOVED,
    QEV_SENT_TO_CUSTOMER, QEV_CUSTOMER_APPROVED, QEV_CUSTOMER_REJECTED,
    QEV_REVISION_REQUESTED, QEV_CANCELLED, QEV_PROVIDER_APPROVED,
    QEV_PROVIDER_REJECTED, QEV_SUBMITTED_TO_PROVIDER, QEV_REVISED,
    JOB_STATUS_AWAITING_QUOTE_APPROVAL, JOB_STATUS_QUOTE_APPROVED,
    JOB_STATUS_QUOTE_REJECTED, JOB_STATUS_QUOTE_REVISION,
    ERR_QUOTE_NOT_FOUND, ERR_QUOTE_ACCESS_DENIED,
    ERR_QUOTE_INVALID_TRANSITION, ERR_QUOTE_ALREADY_LOCKED,
    ERR_QUOTE_ITEM_REQUIRED, ERR_QUOTE_ITEM_INVALID,
    ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED,
    ERR_QUOTE_REJECTION_REASON_REQUIRED, ERR_QUOTE_REVISION_REASON_REQUIRED,
    ERR_QUOTE_IDEMPOTENCY_CONFLICT, ERR_QUOTE_JOB_NOT_FOUND,
)
from app.engines.quote_checklist.models import (
    ServiceJobQuote, ServiceJobQuoteItem, ServiceJobQuoteEvent,
)
from app.engines.final_records.models import ServiceJob


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _quote_number() -> str:
    suffix = str(uuid.uuid4()).replace("-", "").upper()[:10]
    return f"QT-{suffix}"


class ServiceJobQuoteService:

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_quote(self, db: AsyncSession, quote_id: str) -> ServiceJobQuote:
        res = await db.execute(select(ServiceJobQuote).where(ServiceJobQuote.id == uuid.UUID(quote_id)))
        q = res.scalar_one_or_none()
        if not q:
            raise ValueError(ERR_QUOTE_NOT_FOUND)
        return q

    async def _get_job(self, db: AsyncSession, job_id: str) -> ServiceJob:
        res = await db.execute(select(ServiceJob).where(ServiceJob.id == uuid.UUID(job_id)))
        j = res.scalar_one_or_none()
        if not j:
            raise ValueError(ERR_QUOTE_JOB_NOT_FOUND)
        return j

    def _assert_transition(self, quote: ServiceJobQuote, to_status: str) -> None:
        allowed = QUOTE_TRANSITIONS.get(quote.status, set())
        if to_status not in allowed:
            raise ValueError(ERR_QUOTE_INVALID_TRANSITION)

    def _assert_tenant(self, quote: ServiceJobQuote, tenant_id: str) -> None:
        if str(quote.tenant_id) != tenant_id:
            raise ValueError(ERR_QUOTE_ACCESS_DENIED)

    def _assert_not_locked(self, quote: ServiceJobQuote) -> None:
        if quote.locked_at is not None:
            raise ValueError(ERR_QUOTE_ALREADY_LOCKED)

    async def _log_event(
        self, db: AsyncSession, quote: ServiceJobQuote,
        event_type: str, actor_type: str, actor_user_id: str | None,
        old_status: str | None = None, new_status: str | None = None,
        reason: str | None = None, request_id: str | None = None,
    ) -> None:
        ev = ServiceJobQuoteEvent(
            id=uuid.uuid4(),
            quote_id=quote.id,
            booking_id=quote.booking_id,
            job_id=quote.job_id,
            tenant_id=quote.tenant_id,
            actor_type=actor_type,
            actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            request_id=request_id,
        )
        db.add(ev)

    async def _sync_job_status(self, db: AsyncSession, job_id: uuid.UUID, new_status: str) -> None:
        await db.execute(
            update(ServiceJob)
            .where(ServiceJob.id == job_id)
            .values(status=new_status, updated_at=_utcnow())
        )

    def _recalculate(self, items: list[ServiceJobQuoteItem]) -> dict:
        labour = parts = service = discount = tax = Decimal("0")
        for item in items:
            t = Decimal(str(item.line_total))
            if item.item_type == "labour":      labour   += t
            elif item.item_type in ("part", "material"): parts += t
            elif item.item_type == "service":   service  += t
            elif item.item_type == "discount":  discount += t
            elif item.item_type == "tax":       tax      += t
        total = labour + parts + service - discount + tax
        return {
            "labour_amount":  labour,
            "parts_amount":   parts,
            "service_amount": service,
            "discount_amount": discount,
            "tax_amount":     tax,
            "total_amount":   total,
            "customer_payable_amount": total,
        }

    # ── Create quote ───────────────────────────────────────────────────────────

    async def create_quote(
        self, db: AsyncSession, job_id: str, tenant_id: str,
        quote_type: str, user_id: str, staff_member_id: str | None,
        notes: str | None, request_id: str | None,
    ) -> dict:
        if quote_type not in VALID_QUOTE_TYPES:
            raise ValueError(ERR_QUOTE_ITEM_INVALID)
        job = await self._get_job(db, job_id)
        if str(job.tenant_id) != tenant_id:
            raise ValueError(ERR_QUOTE_ACCESS_DENIED)
        q = ServiceJobQuote(
            id=uuid.uuid4(),
            quote_number=_quote_number(),
            booking_id=job.booking_id,
            job_id=job.id,
            tenant_id=uuid.UUID(tenant_id),
            customer_id=job.customer_id,
            created_by_user_id=uuid.UUID(user_id),
            created_by_staff_member_id=uuid.UUID(staff_member_id) if staff_member_id else None,
            status=QS_DRAFT,
            quote_type=quote_type,
            currency="INR",
            labour_amount=Decimal("0"),
            parts_amount=Decimal("0"),
            service_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("0"),
            customer_payable_amount=Decimal("0"),
            provider_internal_notes=notes,
        )
        db.add(q)
        await db.flush()
        await self._log_event(
            db, q, QEV_CREATED, "staff", user_id,
            new_status=QS_DRAFT, request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()

    # ── Add item ───────────────────────────────────────────────────────────────

    async def add_item(
        self, db: AsyncSession, quote_id: str, tenant_id: str,
        item_type: str, item_name: str, item_description: str | None,
        quantity: float, unit_price: float, is_required: bool,
        is_customer_visible: bool, user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        self._assert_tenant(q, tenant_id)
        self._assert_not_locked(q)
        if item_type not in VALID_ITEM_TYPES:
            raise ValueError(ERR_QUOTE_ITEM_INVALID)
        qty = Decimal(str(quantity))
        up  = Decimal(str(unit_price))
        total = qty * up
        item = ServiceJobQuoteItem(
            id=uuid.uuid4(),
            quote_id=q.id,
            booking_id=q.booking_id,
            job_id=q.job_id,
            tenant_id=q.tenant_id,
            item_type=item_type,
            item_name=item_name,
            item_description=item_description,
            quantity=qty,
            unit_price=up,
            line_total=total,
            is_required=is_required,
            is_customer_visible=is_customer_visible,
        )
        db.add(item)
        await db.flush()
        # recalculate totals
        res = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        items = list(res.scalars().all())
        totals = self._recalculate(items)
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(**totals, updated_at=_utcnow())
        )
        await self._log_event(db, q, QEV_ITEM_ADDED, "staff", user_id, request_id=request_id)
        await db.commit()
        await db.refresh(item)
        return item.to_dict()

    # ── Update item ────────────────────────────────────────────────────────────

    async def update_item(
        self, db: AsyncSession, quote_id: str, item_id: str, tenant_id: str,
        item_name: str | None, item_description: str | None,
        quantity: float | None, unit_price: float | None,
        is_customer_visible: bool | None, user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        self._assert_tenant(q, tenant_id)
        self._assert_not_locked(q)
        res = await db.execute(
            select(ServiceJobQuoteItem).where(
                ServiceJobQuoteItem.id == uuid.UUID(item_id),
                ServiceJobQuoteItem.quote_id == q.id,
            )
        )
        item = res.scalar_one_or_none()
        if not item:
            raise ValueError(ERR_QUOTE_ITEM_INVALID)
        if item_name is not None:        item.item_name = item_name
        if item_description is not None: item.item_description = item_description
        if quantity is not None:         item.quantity = Decimal(str(quantity))
        if unit_price is not None:       item.unit_price = Decimal(str(unit_price))
        if is_customer_visible is not None: item.is_customer_visible = is_customer_visible
        item.line_total = item.quantity * item.unit_price
        await db.flush()
        res2 = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        totals = self._recalculate(list(res2.scalars().all()))
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(**totals, updated_at=_utcnow())
        )
        await self._log_event(db, q, QEV_ITEM_UPDATED, "staff", user_id, request_id=request_id)
        await db.commit()
        await db.refresh(item)
        return item.to_dict()

    # ── Remove item ────────────────────────────────────────────────────────────

    async def remove_item(
        self, db: AsyncSession, quote_id: str, item_id: str,
        tenant_id: str, user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        self._assert_tenant(q, tenant_id)
        self._assert_not_locked(q)
        res = await db.execute(
            select(ServiceJobQuoteItem).where(
                ServiceJobQuoteItem.id == uuid.UUID(item_id),
                ServiceJobQuoteItem.quote_id == q.id,
            )
        )
        item = res.scalar_one_or_none()
        if not item:
            raise ValueError(ERR_QUOTE_ITEM_INVALID)
        await db.delete(item)
        await db.flush()
        res2 = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        totals = self._recalculate(list(res2.scalars().all()))
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(**totals, updated_at=_utcnow())
        )
        await self._log_event(db, q, QEV_ITEM_REMOVED, "staff", user_id, request_id=request_id)
        await db.commit()
        return {"removed": True}

    # ── Send to customer ───────────────────────────────────────────────────────

    async def send_to_customer(
        self, db: AsyncSession, quote_id: str, tenant_id: str,
        customer_notes: str | None, user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        self._assert_tenant(q, tenant_id)
        # must have items
        res = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        items = list(res.scalars().all())
        if not items:
            raise ValueError(ERR_QUOTE_ITEM_REQUIRED)
        old_status = q.status
        self._assert_transition(q, QS_SENT_TO_CUSTOMER)
        now = _utcnow()
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(
                status=QS_SENT_TO_CUSTOMER,
                sent_to_customer_at=now,
                customer_visible_notes=customer_notes or q.customer_visible_notes,
                updated_at=now,
            )
        )
        q.status = QS_SENT_TO_CUSTOMER
        await self._sync_job_status(db, q.job_id, JOB_STATUS_AWAITING_QUOTE_APPROVAL)
        await self._log_event(
            db, q, QEV_SENT_TO_CUSTOMER, "staff", user_id,
            old_status=old_status, new_status=QS_SENT_TO_CUSTOMER,
            request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()

    # ── Customer approve ───────────────────────────────────────────────────────

    async def customer_approve(
        self, db: AsyncSession, quote_id: str, customer_id: str,
        idempotency_key: str, user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        if str(q.customer_id) != customer_id:
            raise ValueError(ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED)
        # idempotency: already approved with same key → return as-is
        if q.status == QS_CUSTOMER_APPROVED and q.idempotency_key == idempotency_key:
            return q.to_dict()
        # conflict: different key but already approved
        if q.status == QS_CUSTOMER_APPROVED:
            raise ValueError(ERR_QUOTE_IDEMPOTENCY_CONFLICT)
        self._assert_transition(q, QS_CUSTOMER_APPROVED)
        now = _utcnow()
        old_status = q.status
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(
                status=QS_CUSTOMER_APPROVED,
                approved_at=now,
                locked_at=now,
                idempotency_key=idempotency_key,
                updated_at=now,
            )
        )
        q.status = QS_CUSTOMER_APPROVED
        await self._sync_job_status(db, q.job_id, JOB_STATUS_QUOTE_APPROVED)
        await self._log_event(
            db, q, QEV_CUSTOMER_APPROVED, "customer", user_id,
            old_status=old_status, new_status=QS_CUSTOMER_APPROVED,
            request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()

    # ── Customer reject ────────────────────────────────────────────────────────

    async def customer_reject(
        self, db: AsyncSession, quote_id: str, customer_id: str,
        reason: str, user_id: str, request_id: str | None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_QUOTE_REJECTION_REASON_REQUIRED)
        q = await self._get_quote(db, quote_id)
        if str(q.customer_id) != customer_id:
            raise ValueError(ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED)
        self._assert_transition(q, QS_CUSTOMER_REJECTED)
        old_status = q.status
        now = _utcnow()
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(
                status=QS_CUSTOMER_REJECTED,
                rejection_reason=reason,
                rejected_at=now,
                updated_at=now,
            )
        )
        q.status = QS_CUSTOMER_REJECTED
        await self._sync_job_status(db, q.job_id, JOB_STATUS_QUOTE_REJECTED)
        await self._log_event(
            db, q, QEV_CUSTOMER_REJECTED, "customer", user_id,
            old_status=old_status, new_status=QS_CUSTOMER_REJECTED,
            reason=reason, request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()

    # ── Customer request revision ──────────────────────────────────────────────

    async def customer_request_revision(
        self, db: AsyncSession, quote_id: str, customer_id: str,
        reason: str, user_id: str, request_id: str | None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_QUOTE_REVISION_REASON_REQUIRED)
        q = await self._get_quote(db, quote_id)
        if str(q.customer_id) != customer_id:
            raise ValueError(ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED)
        self._assert_transition(q, QS_REVISION_REQUESTED)
        old_status = q.status
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(status=QS_REVISION_REQUESTED, revision_reason=reason, updated_at=_utcnow())
        )
        q.status = QS_REVISION_REQUESTED
        await self._sync_job_status(db, q.job_id, JOB_STATUS_QUOTE_REVISION)
        await self._log_event(
            db, q, QEV_REVISION_REQUESTED, "customer", user_id,
            old_status=old_status, new_status=QS_REVISION_REQUESTED,
            reason=reason, request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()

    # ── Cancel quote ───────────────────────────────────────────────────────────

    async def cancel_quote(
        self, db: AsyncSession, quote_id: str, tenant_id: str,
        reason: str | None, user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        self._assert_tenant(q, tenant_id)
        self._assert_transition(q, QS_CANCELLED)
        old_status = q.status
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(status=QS_CANCELLED, updated_at=_utcnow())
        )
        q.status = QS_CANCELLED
        await self._log_event(
            db, q, QEV_CANCELLED, "staff", user_id,
            old_status=old_status, new_status=QS_CANCELLED,
            reason=reason, request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()

    # ── Get quote ──────────────────────────────────────────────────────────────

    async def get_quote(
        self, db: AsyncSession, quote_id: str,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        res = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        items = [i.to_dict() for i in res.scalars().all()]
        data = q.to_dict()
        data["items"] = items
        return data

    # ── List quotes for job ────────────────────────────────────────────────────

    async def list_quotes_for_job(
        self, db: AsyncSession, job_id: str, tenant_id: str,
    ) -> list[dict]:
        res = await db.execute(
            select(ServiceJobQuote).where(
                ServiceJobQuote.job_id == uuid.UUID(job_id),
                ServiceJobQuote.tenant_id == uuid.UUID(tenant_id),
            ).order_by(ServiceJobQuote.created_at.desc())
        )
        return [q.to_dict() for q in res.scalars().all()]

    # ── List customer quotes ───────────────────────────────────────────────────

    async def list_customer_quotes(
        self, db: AsyncSession, customer_id: str, job_id: str,
    ) -> list[dict]:
        res = await db.execute(
            select(ServiceJobQuote).where(
                ServiceJobQuote.job_id == uuid.UUID(job_id),
                ServiceJobQuote.customer_id == uuid.UUID(customer_id),
            ).order_by(ServiceJobQuote.created_at.desc())
        )
        return [q.to_dict() for q in res.scalars().all()]

    # ── Quote events ───────────────────────────────────────────────────────────

    async def list_quote_events(
        self, db: AsyncSession, quote_id: str, tenant_id: str | None = None,
    ) -> list[dict]:
        q = await self._get_quote(db, quote_id)
        if tenant_id and str(q.tenant_id) != tenant_id:
            raise ValueError(ERR_QUOTE_ACCESS_DENIED)
        res = await db.execute(
            select(ServiceJobQuoteEvent)
            .where(ServiceJobQuoteEvent.quote_id == q.id)
            .order_by(ServiceJobQuoteEvent.created_at)
        )
        return [e.to_dict() for e in res.scalars().all()]

    # ── Mark as revised (provider updates draft after revision request) ────────

    async def mark_revised(
        self, db: AsyncSession, quote_id: str, tenant_id: str,
        user_id: str, request_id: str | None,
    ) -> dict:
        q = await self._get_quote(db, quote_id)
        self._assert_tenant(q, tenant_id)
        self._assert_transition(q, QS_REVISED)
        old_status = q.status
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(status=QS_REVISED, updated_at=_utcnow())
        )
        q.status = QS_REVISED
        await self._log_event(
            db, q, QEV_REVISED, "staff", user_id,
            old_status=old_status, new_status=QS_REVISED,
            request_id=request_id,
        )
        await db.commit()
        await db.refresh(q)
        return q.to_dict()
