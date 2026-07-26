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
    QEV_PROVIDER_REJECTED, QEV_SUBMITTED_TO_PROVIDER, QEV_REVISED, QEV_EXPIRED,
    ERR_QUOTE_NOT_FOUND, ERR_QUOTE_ACCESS_DENIED,
    ERR_QUOTE_NOT_CURRENT, ERR_APPROVED_ESTIMATE_IMMUTABLE,
    ERR_INVALID_ESTIMATE_REVISION_STATE, ERR_JOB_CLOSED_ESTIMATE_DECLINED,
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
from app.engines.execution.constants import (
    JS_QUOTE_REQUIRED, JS_CLOSED_ESTIMATE_DECLINED, JOB_TRANSITIONS,
)


# Slice 2F-16: add_item/update_item/remove_item previously checked only
# _assert_not_locked (locked_at is set ONLY on customer approval) -- a quote
# already in QS_SENT_TO_CUSTOMER (customer is actively deciding), or any
# terminal status (rejected/expired/cancelled), was NOT "locked" and could
# still have its line items silently mutated after the fact, changing the
# total the customer already saw or decided on. Only these statuses permit
# item mutation -- the same statuses QUOTE_TRANSITIONS treats as still
# provider-editable, mirroring send_to_customer's own legal-source-state list.
ITEM_EDITABLE_QUOTE_STATUSES = {
    QS_DRAFT, QS_SUBMITTED_TO_PROVIDER, QS_PROVIDER_REJECTED,
    QS_REVISION_REQUESTED, QS_REVISED,
}

# Slice 2F-16A: event types a customer may see in their own quote's history --
# excludes internal draft-editing events (item added/updated/removed) and the
# internal provider-approval-step events, which are provider-side
# administrative history with no customer-facing relevance.
CUSTOMER_VISIBLE_QUOTE_EVENT_TYPES = {
    QEV_SENT_TO_CUSTOMER, QEV_CUSTOMER_APPROVED, QEV_CUSTOMER_REJECTED,
    QEV_REVISION_REQUESTED, QEV_REVISED, QEV_EXPIRED, QEV_CANCELLED,
}


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
        """HOME-SERVICES-RUNTIME-SAFETY Phase 2A fix: this previously wrote
        ServiceJob.status via raw SQL using a string vocabulary
        (JOB_STATUS_AWAITING_QUOTE_APPROVAL etc.) that did not appear
        anywhere in execution/constants.py's JOB_TRANSITIONS graph -- a
        second, unvalidated status-write path that bypassed the execution
        engine's own transition enforcement entirely and could permanently
        strand a job in a status _assert_transition had never heard of.
        Now writes only real JS_* values and validates against the SAME
        JOB_TRANSITIONS graph the execution engine itself enforces -- no
        second job-state machine.
        """
        res = await db.execute(select(ServiceJob.status).where(ServiceJob.id == job_id))
        current = res.scalar_one_or_none()
        if current is None or current == new_status:
            return
        allowed = JOB_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(f"QUOTE_JOB_STATUS_SYNC_INVALID_TRANSITION:{current}->{new_status}")
        await db.execute(
            update(ServiceJob)
            .where(ServiceJob.id == job_id)
            .values(status=new_status, updated_at=_utcnow())
        )

    async def _customer_dict(self, db: AsyncSession, q: ServiceJobQuote) -> dict:
        """Slice 2F-16A: customer_approve/reject/request_revision previously
        returned q.to_dict() directly, exposing provider_internal_notes AND
        the all-items-inclusive stored total in the decision RESPONSE even
        after get_quote's own filtering (2F-16) was fixed -- a customer could
        see internal notes, and a total that did not reconcile to any items
        list they'd been shown, simply by approving/rejecting a quote,
        bypassing the read-path fix entirely. Every customer-decision return
        point now goes through this helper, mirroring get_quote's own
        customer-view logic exactly."""
        data = q.to_dict()
        data.pop("provider_internal_notes", None)
        res = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        visible_rows = [i for i in res.scalars().all() if i.is_customer_visible]
        data.update({k: str(v) for k, v in self._recalculate(visible_rows).items()})
        return data

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
        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 14): a job
        # whose estimate was FINALLY rejected (closed_estimate_declined) is
        # terminal -- creating a replacement quote must fail unless a
        # separate, explicit reopen workflow exists (none does). This is
        # distinct from revision_requested, which stays open and DOES permit
        # a new quote (handled by the is_current-based checks below).
        if job.status == JS_CLOSED_ESTIMATE_DECLINED:
            raise ValueError(ERR_JOB_CLOSED_ESTIMATE_DECLINED)
        # A required pre-estimate checklist (e.g. inspection evidence)
        # complements the quote-approval gate -- it gates *submitting* an
        # estimate, not approving one. Independent of, and does not
        # substitute for, the customer-approval gate enforced elsewhere.
        from app.engines.checklist_catalog.gate import assert_gate_satisfied
        from app.engines.checklist_catalog.constants import GATE_BEFORE_ESTIMATE_SUBMISSION
        await assert_gate_satisfied(db, job, GATE_BEFORE_ESTIMATE_SUBMISSION)
        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A (spec section 7): previously
        # nothing stopped a second, fully independent quote row from being
        # created for a job that already had one in flight -- two rows could
        # both end up "customer_approved" with no notion of which was
        # current. A new quote now supersedes the job's existing current
        # quote (if any), preserving it as read-only history.
        #
        # Phase 2A.1 (spec section 10) hardening: an ORDINARY create_quote
        # call may not silently replace a quote the customer already
        # approved (immutable -- a real amount/scope change needs a
        # dedicated change-order workflow, which does not exist yet in this
        # codebase; fail closed and treat as deferred rather than pretend),
        # nor one currently sent to the customer and awaiting their decision
        # (the canonical replacement path there is cancel_quote() first,
        # which is an explicit, audited action, then create_quote()).
        # Rejected / revision-requested / expired / cancelled are legitimate
        # replacement sources -- nothing is pending or locked in those states.
        prior = (await db.execute(
            select(ServiceJobQuote).where(
                ServiceJobQuote.job_id == job.id, ServiceJobQuote.is_current.is_(True),
            )
        )).scalar_one_or_none()
        if prior is not None and prior.status == QS_CUSTOMER_APPROVED:
            raise ValueError(ERR_APPROVED_ESTIMATE_IMMUTABLE)
        if prior is not None and prior.status == QS_SENT_TO_CUSTOMER:
            raise ValueError(ERR_INVALID_ESTIMATE_REVISION_STATE)
        now = _utcnow()
        if prior is not None:
            await db.execute(
                update(ServiceJobQuote)
                .where(ServiceJobQuote.id == prior.id)
                .values(is_current=False, superseded_at=now, updated_at=now)
            )
            await db.flush()
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
            version_number=(prior.version_number + 1) if prior is not None else 1,
            is_current=True,
            supersedes_quote_id=prior.id if prior is not None else None,
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
        if q.status not in ITEM_EDITABLE_QUOTE_STATUSES:
            raise ValueError(ERR_QUOTE_ALREADY_LOCKED)
        if item_type not in VALID_ITEM_TYPES:
            raise ValueError(ERR_QUOTE_ITEM_INVALID)
        qty = Decimal(str(quantity))
        up  = Decimal(str(unit_price))
        # Slice 2F-16: negative quantity/price were previously unvalidated --
        # a negative unit_price on a non-discount item (or a negative
        # quantity on any item) would silently reduce the quote total below
        # what the visible line items represent. Discount items are
        # intentionally allowed to reduce the total (that's their purpose,
        # subtracted in _recalculate) but must themselves be non-negative
        # inputs -- a "negative discount" is not a supported way to inflate
        # a total; increasing price is done via labour/parts/service items.
        if qty < 0 or up < 0:
            raise ValueError(ERR_QUOTE_ITEM_INVALID)
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
        if q.status not in ITEM_EDITABLE_QUOTE_STATUSES:
            raise ValueError(ERR_QUOTE_ALREADY_LOCKED)
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
        if quantity is not None:
            new_qty = Decimal(str(quantity))
            if new_qty < 0:
                raise ValueError(ERR_QUOTE_ITEM_INVALID)
            item.quantity = new_qty
        if unit_price is not None:
            new_up = Decimal(str(unit_price))
            if new_up < 0:
                raise ValueError(ERR_QUOTE_ITEM_INVALID)
            item.unit_price = new_up
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
        if q.status not in ITEM_EDITABLE_QUOTE_STATUSES:
            raise ValueError(ERR_QUOTE_ALREADY_LOCKED)
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
        await self._sync_job_status(db, q.job_id, JS_QUOTE_REQUIRED)
        await self._log_event(
            db, q, QEV_SENT_TO_CUSTOMER, "staff", user_id,
            old_status=old_status, new_status=QS_SENT_TO_CUSTOMER,
            request_id=request_id,
        )
        # MODULE-L5-21: tell the customer a quote is waiting, or the job silently
        # stalls at "awaiting quote approval" with the customer never informed.
        from app.engines.quote_checklist.notifications import notify_customer_quote_sent
        await notify_customer_quote_sent(db, q)
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
        # Phase 2A: a superseded quote (a newer revision now exists) can
        # never be approved, even by its rightful owner -- approving stale
        # content could never legitimately authorize work against the
        # current job. Checked before idempotency so a superseded-but-
        # previously-approved quote cannot be "re-confirmed" via a matching key.
        if not q.is_current:
            raise ValueError(ERR_QUOTE_NOT_CURRENT)
        # idempotency: already approved with same key → return as-is.
        # Kept as a lightweight, query-free strip (not the full
        # _customer_dict/_recalculate reconciliation) -- an already-approved
        # quote's stored total was already correctly reconciled at the
        # moment of approval (this same method, non-idempotent branch below),
        # so no additional item query is needed here.
        if q.status == QS_CUSTOMER_APPROVED and q.idempotency_key == idempotency_key:
            data = q.to_dict()
            data.pop("provider_internal_notes", None)
            return data
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
                approved_by=uuid.UUID(customer_id),
                updated_at=now,
            )
        )
        q.status = QS_CUSTOMER_APPROVED
        # Phase 2A: no job-status transition on approval -- the job stays at
        # JS_QUOTE_REQUIRED (a graph-valid predecessor of JS_SERVICE_STARTED);
        # the work-start guard (assert_job_can_start_work) resolves whether
        # this specific approved-and-current quote actually authorizes work.
        await self._sync_job_status(db, q.job_id, JS_QUOTE_REQUIRED)
        await self._log_event(
            db, q, QEV_CUSTOMER_APPROVED, "customer", user_id,
            old_status=old_status, new_status=QS_CUSTOMER_APPROVED,
            request_id=request_id,
        )
        from app.engines.quote_checklist.notifications import notify_provider_quote_decision
        await notify_provider_quote_decision(db, q, "approved")
        await db.commit()
        await db.refresh(q)
        return await self._customer_dict(db, q)

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
        if not q.is_current:
            raise ValueError(ERR_QUOTE_NOT_CURRENT)
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
        await self._sync_job_status(db, q.job_id, JS_CLOSED_ESTIMATE_DECLINED)
        await self._log_event(
            db, q, QEV_CUSTOMER_REJECTED, "customer", user_id,
            old_status=old_status, new_status=QS_CUSTOMER_REJECTED,
            reason=reason, request_id=request_id,
        )
        from app.engines.quote_checklist.notifications import notify_provider_quote_decision
        await notify_provider_quote_decision(db, q, "rejected")
        await db.commit()
        await db.refresh(q)
        return await self._customer_dict(db, q)

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
        if not q.is_current:
            raise ValueError(ERR_QUOTE_NOT_CURRENT)
        self._assert_transition(q, QS_REVISION_REQUESTED)
        old_status = q.status
        await db.execute(
            update(ServiceJobQuote)
            .where(ServiceJobQuote.id == q.id)
            .values(status=QS_REVISION_REQUESTED, revision_reason=reason, updated_at=_utcnow())
        )
        q.status = QS_REVISION_REQUESTED
        # Revision-requested must NOT close the job (spec section 9) -- job
        # stays at JS_QUOTE_REQUIRED while the provider sends a new estimate.
        await self._sync_job_status(db, q.job_id, JS_QUOTE_REQUIRED)
        await self._log_event(
            db, q, QEV_REVISION_REQUESTED, "customer", user_id,
            old_status=old_status, new_status=QS_REVISION_REQUESTED,
            reason=reason, request_id=request_id,
        )
        from app.engines.quote_checklist.notifications import notify_provider_quote_decision
        await notify_provider_quote_decision(db, q, "revision")
        await db.commit()
        await db.refresh(q)
        return await self._customer_dict(db, q)

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
        tenant_id: str | None = None, customer_id: str | None = None,
    ) -> dict:
        """Slice 2F-16: previously had NO ownership filter at all -- any
        authenticated user of any tenant could fetch ANY quote's full detail
        (including provider_internal_notes) by ID alone. Callers now pass
        their own scoping identifier: provider/staff/admin pass tenant_id,
        customer passes customer_id.

        Slice 2F-16A: a foreign-owner mismatch now raises the SAME
        ERR_QUOTE_NOT_FOUND code as a genuinely missing quote (previously
        raised ERR_QUOTE_ACCESS_DENIED, which maps to a different HTTP status
        via the app's ValueError->4xx handler -- "exists but isn't yours" was
        externally distinguishable from "doesn't exist", disclosing existence
        of another tenant's/customer's record). Mirrors the established
        privacy-safe 404 pattern used by Booking's _assert_can_access_booking."""
        q = await self._get_quote(db, quote_id)
        if tenant_id is not None and str(q.tenant_id) != tenant_id:
            raise ValueError(ERR_QUOTE_NOT_FOUND)
        if customer_id is not None and str(q.customer_id) != customer_id:
            raise ValueError(ERR_QUOTE_NOT_FOUND)
        res = await db.execute(select(ServiceJobQuoteItem).where(ServiceJobQuoteItem.quote_id == q.id))
        rows = res.scalars().all()
        data = q.to_dict()
        # Slice 2F-16: a customer caller (identified by the presence of
        # customer_id) must never see provider-internal fields or
        # non-customer-visible line items -- previously to_dict() returned
        # provider_internal_notes and ALL items unconditionally to every
        # caller, including the customer.
        if customer_id is not None:
            data.pop("provider_internal_notes", None)
            rows = [i for i in rows if i.is_customer_visible]
            # Slice 2F-16A: q.total_amount/customer_payable_amount (and the
            # per-bucket labour/parts/service/discount/tax amounts) are
            # computed from ALL items including hidden internal ones
            # (_recalculate has no visibility filter -- correct for the
            # PROVIDER view, which needs the true full cost). Returning that
            # SAME total to a customer alongside only the customer-visible
            # items would show a total that does not reconcile to the listed
            # items -- a customer approving that total would be approving an
            # undisclosed hidden charge. The customer-facing totals are
            # recomputed here from ONLY the customer-visible items, so what
            # is displayed always reconciles to what is itemized.
            customer_totals = self._recalculate(rows)
            data.update({k: str(v) for k, v in customer_totals.items()})
        data["items"] = [i.to_dict() for i in rows]
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
        self, db: AsyncSession, quote_id: str,
        tenant_id: str | None = None, customer_id: str | None = None,
    ) -> list[dict]:
        q = await self._get_quote(db, quote_id)
        # Slice 2F-16A: privacy-safe 404 for foreign ownership, matching get_quote.
        if tenant_id and str(q.tenant_id) != tenant_id:
            raise ValueError(ERR_QUOTE_NOT_FOUND)
        if customer_id and str(q.customer_id) != customer_id:
            raise ValueError(ERR_QUOTE_NOT_FOUND)
        res = await db.execute(
            select(ServiceJobQuoteEvent)
            .where(ServiceJobQuoteEvent.quote_id == q.id)
            .order_by(ServiceJobQuoteEvent.created_at)
        )
        events = res.scalars().all()
        # Slice 2F-16A: draft-editing events (item added/updated/removed,
        # internal provider-approval-step events) are provider-internal
        # administrative history -- a customer has no legitimate need to see
        # how many times staff edited a draft before sending it, and this
        # was previously exposed unfiltered to the customer_id caller.
        if customer_id is not None:
            events = [e for e in events if e.event_type in CUSTOMER_VISIBLE_QUOTE_EVENT_TYPES]
        return [e.to_dict() for e in events]

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
