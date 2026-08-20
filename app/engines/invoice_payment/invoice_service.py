"""Sprint 23 — ServiceInvoiceService: invoice lifecycle + calculation."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.invoice_payment.constants import (
    INV_DRAFT, INV_ISSUED, INV_PAYMENT_COLLECTED, INV_PAID, INV_CANCELLED,
    INVOICE_TRANSITIONS, VALID_INVOICE_SOURCES,
    INV_SRC_APPROVED_QUOTE, INV_SRC_BOOKING_BASE, INV_SRC_MANUAL_FINAL,
    FEV_INVOICE_CREATED, FEV_INVOICE_ISSUED, FEV_INVOICE_CANCELLED,
    JOB_STATUS_INVOICE_ISSUED,
    ERR_INVOICE_NOT_FOUND, ERR_INVOICE_ACCESS_DENIED,
    ERR_INVOICE_ALREADY_EXISTS, ERR_INVOICE_INVALID_STATUS,
    ERR_INVOICE_ALREADY_ISSUED, ERR_INVOICE_CANCELLED as CERR,
    ERR_INVOICE_ITEM_INVALID, ERR_INVOICE_TOTAL_INVALID,
)
from app.engines.invoice_payment.models import (
    ServiceInvoice, ServiceInvoiceItem, FinancialEvent,
)
from app.engines.final_records.models import ServiceJob, ServiceBooking
from app.engines.quote_checklist.models import ServiceJobQuote, ServiceJobQuoteItem


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _invoice_number() -> str:
    suffix = str(uuid.uuid4()).replace("-", "").upper()[:10]
    return f"INV-{suffix}"


class ServiceInvoiceService:

    async def _add_issue_notification(self, db: AsyncSession, inv: ServiceInvoice) -> None:
        if not inv.customer_id:
            return
        from app.engines.platform_notifications.models import InAppNotification
        db.add(InAppNotification(
            user_id=inv.customer_id,
            tenant_id=inv.tenant_id,
            notification_type="invoice.issued",
            title="Your invoice is ready",
            body=(f"Amount due: {inv.currency}{inv.customer_payable_amount}. "
                  f"Pay your provider directly after the service is complete."),
            action_url=f"/customer/invoices/{inv.id}",
            action_label="View invoice",
            source_record_type="service_invoices",
            source_record_id=inv.id,
            severity="info",
        ))

    async def _get_invoice(self, db: AsyncSession, invoice_id: str) -> ServiceInvoice:
        res = await db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == uuid.UUID(invoice_id))
        )
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        return inv

    async def _get_job(self, db: AsyncSession, job_id: str) -> ServiceJob:
        res = await db.execute(select(ServiceJob).where(ServiceJob.id == uuid.UUID(job_id)))
        j = res.scalar_one_or_none()
        if not j:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        return j

    def _assert_tenant(self, inv: ServiceInvoice, tenant_id: str) -> None:
        if str(inv.tenant_id) != tenant_id:
            raise ValueError(ERR_INVOICE_ACCESS_DENIED)

    def _assert_transition(self, inv: ServiceInvoice, to_status: str) -> None:
        allowed = INVOICE_TRANSITIONS.get(inv.status, set())
        if to_status not in allowed:
            raise ValueError(ERR_INVOICE_INVALID_STATUS)

    async def _log_event(
        self, db: AsyncSession, inv: ServiceInvoice, event_type: str,
        actor_type: str, actor_user_id: str | None,
        old_value: dict | None = None, new_value: dict | None = None,
        reason: str | None = None, request_id: str | None = None,
    ) -> None:
        ev = FinancialEvent(
            id=uuid.uuid4(),
            record_type="invoice",
            record_id=inv.id,
            tenant_id=inv.tenant_id,
            customer_id=inv.customer_id,
            actor_type=actor_type,
            actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            request_id=request_id,
        )
        db.add(ev)

    def _recalculate(self, items: list[ServiceInvoiceItem]) -> dict:
        labour = parts = service = discount = tax = Decimal("0")
        for item in items:
            t = Decimal(str(item.line_total))
            if item.item_type == "labour":             labour   += t
            elif item.item_type in ("part","material"): parts   += t
            elif item.item_type == "service":           service += t
            elif item.item_type == "discount":          discount += t
            elif item.item_type == "tax":               tax     += t
        subtotal = labour + parts + service
        total    = subtotal - discount + tax
        return {
            "subtotal_amount":         subtotal,
            "labour_amount":           labour,
            "parts_amount":            parts,
            "service_amount":          service,
            "discount_amount":         discount,
            "tax_amount":              tax,
            "total_amount":            total,
            "customer_payable_amount": total,
        }

    # ── Create invoice ─────────────────────────────────────────────────────────

    async def create_invoice(
        self, db: AsyncSession, job_id: str, tenant_id: str,
        source: str, quote_id: str | None, notes: str | None,
        user_id: str, request_id: str | None,
    ) -> dict:
        if source not in VALID_INVOICE_SOURCES:
            raise ValueError(ERR_INVOICE_INVALID_STATUS)
        job = await self._get_job(db, job_id)
        if str(job.tenant_id) != tenant_id:
            raise ValueError(ERR_INVOICE_ACCESS_DENIED)
        # Prevent duplicate active invoice per job
        res = await db.execute(
            select(ServiceInvoice).where(
                ServiceInvoice.job_id == job.id,
                ServiceInvoice.status.not_in([INV_CANCELLED]),
            )
        )
        if res.scalar_one_or_none():
            raise ValueError(ERR_INVOICE_ALREADY_EXISTS)

        # Slice 2F-16: validate the referenced quote BEFORE any persistence --
        # previously this check (tenant + customer_approved status) happened
        # AFTER db.add(inv)/db.flush() had already inserted the invoice row,
        # so a rejected call would still leave a partial INV_DRAFT invoice
        # behind. Also previously copied line items from ANY quote_id with no
        # check that the quote belongs to this tenant or is actually
        # customer_approved -- staff could fabricate an invoice from a
        # draft/rejected quote, or (if the UUID were known/guessed) a
        # DIFFERENT tenant's quote entirely.
        quote = None
        if source == INV_SRC_APPROVED_QUOTE and quote_id:
            qres = await db.execute(
                select(ServiceJobQuote).where(ServiceJobQuote.id == uuid.UUID(quote_id))
            )
            quote = qres.scalar_one_or_none()
            if not quote or str(quote.tenant_id) != tenant_id:
                raise ValueError(ERR_INVOICE_ACCESS_DENIED)
            # Slice 2F-16A: tenant match alone is not sufficient -- a quote
            # from a DIFFERENT ServiceJob (or belonging to a different
            # customer) in the SAME tenant previously passed this check
            # unnoticed, letting one job's approved quote be copied into an
            # unrelated job's invoice (or an invoice attributed to the wrong
            # customer). The quote must belong to the EXACT ServiceJob being
            # invoiced, and its customer must match that ServiceJob's customer.
            if quote.job_id != job.id:
                raise ValueError(ERR_INVOICE_ACCESS_DENIED)
            if quote.customer_id != job.customer_id:
                raise ValueError(ERR_INVOICE_ACCESS_DENIED)
            if quote.status != "customer_approved":
                raise ValueError(ERR_INVOICE_INVALID_STATUS)

        inv = ServiceInvoice(
            id=uuid.uuid4(),
            invoice_number=_invoice_number(),
            booking_id=job.booking_id,
            job_id=job.id,
            quote_id=uuid.UUID(quote_id) if quote_id else None,
            tenant_id=uuid.UUID(tenant_id),
            customer_id=job.customer_id,
            category_id=job.category_id,
            offering_id=job.offering_id,
            status=INV_DRAFT,
            invoice_source=source,
            notes=notes,
            created_by_user_id=uuid.UUID(user_id),
        )
        db.add(inv)
        await db.flush()

        # Seed items from approved quote if source = approved_quote
        # (quote tenant/status already validated above, before persistence)
        if source == INV_SRC_APPROVED_QUOTE and quote_id:
            await self._copy_from_quote(db, inv, quote_id, quote=quote)
        elif source == INV_SRC_BOOKING_BASE:
            await self._copy_from_booking(db, inv, str(job.booking_id))

        # Recalculate totals
        await self._refresh_totals(db, inv)
        await self._log_event(db, inv, FEV_INVOICE_CREATED, "staff", user_id,
                              new_value={"status": INV_DRAFT}, request_id=request_id)
        await db.commit()
        await db.refresh(inv)
        return inv.to_dict()

    async def ensure_issued_for_job(
        self, db: AsyncSession, job_id: str, tenant_id: str, user_id: str,
        request_id: str | None = None, *, notify_customer: bool = True,
    ) -> ServiceInvoice:
        """Materialize the one canonical invoice used by native job closure.

        The job row is locked before the existence check, so two concurrent
        completion/payment requests cannot create two active invoices.  This
        method deliberately does not commit and does not change the operational
        job status: callers keep invoice creation in the same transaction as
        proof submission or payment declaration.
        """
        job_uuid = uuid.UUID(str(job_id))
        tenant_uuid = uuid.UUID(str(tenant_id))
        job = (await db.execute(
            select(ServiceJob).where(ServiceJob.id == job_uuid).with_for_update()
        )).scalars().first()
        if job is None:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        if job.tenant_id != tenant_uuid:
            raise ValueError(ERR_INVOICE_ACCESS_DENIED)

        inv = (await db.execute(
            select(ServiceInvoice).where(
                ServiceInvoice.job_id == job.id,
                ServiceInvoice.tenant_id == tenant_uuid,
                ServiceInvoice.status != INV_CANCELLED,
            ).order_by(ServiceInvoice.created_at.desc()).limit(1)
        )).scalars().first()
        if inv is not None:
            if inv.status == INV_DRAFT:
                now = _utcnow()
                inv.status = INV_ISSUED
                inv.issued_at = now
                inv.updated_at = now
                await self._log_event(
                    db, inv, FEV_INVOICE_ISSUED, "system", user_id,
                    old_value={"status": INV_DRAFT},
                    new_value={"status": INV_ISSUED}, request_id=request_id,
                )
                if notify_customer:
                    await self._add_issue_notification(db, inv)
                await db.flush()
            return inv

        quote = (await db.execute(
            select(ServiceJobQuote).where(
                ServiceJobQuote.job_id == job.id,
                ServiceJobQuote.tenant_id == tenant_uuid,
                ServiceJobQuote.customer_id == job.customer_id,
                ServiceJobQuote.is_current.is_(True),
                ServiceJobQuote.status == "customer_approved",
            ).order_by(ServiceJobQuote.version_number.desc()).limit(1)
        )).scalars().first()
        source = INV_SRC_APPROVED_QUOTE if quote is not None else INV_SRC_BOOKING_BASE
        now = _utcnow()
        inv = ServiceInvoice(
            id=uuid.uuid4(), invoice_number=_invoice_number(),
            booking_id=job.booking_id, job_id=job.id,
            quote_id=quote.id if quote is not None else None,
            tenant_id=tenant_uuid, customer_id=job.customer_id,
            category_id=job.category_id, offering_id=job.offering_id,
            status=INV_DRAFT, invoice_source=source,
            notes="Generated from the canonical native job-completion flow.",
            created_by_user_id=uuid.UUID(str(user_id)),
        )
        db.add(inv)
        await db.flush()
        if quote is not None:
            await self._copy_from_quote(db, inv, str(quote.id), quote=quote)
        else:
            await self._copy_from_booking(db, inv, str(job.booking_id))
        await db.flush()
        await self._refresh_totals(db, inv)
        await db.refresh(inv)
        if Decimal(str(inv.customer_payable_amount or 0)) <= Decimal("0"):
            raise ValueError(ERR_INVOICE_TOTAL_INVALID)

        await self._log_event(
            db, inv, FEV_INVOICE_CREATED, "system", user_id,
            new_value={"status": INV_DRAFT, "source": source},
            request_id=request_id,
        )
        inv.status = INV_ISSUED
        inv.issued_at = now
        inv.updated_at = now
        await self._log_event(
            db, inv, FEV_INVOICE_ISSUED, "system", user_id,
            old_value={"status": INV_DRAFT}, new_value={"status": INV_ISSUED},
            request_id=request_id,
        )
        if notify_customer:
            await self._add_issue_notification(db, inv)
        await db.flush()
        await db.refresh(inv)
        return inv

    async def _copy_from_quote(
        self, db: AsyncSession, inv: ServiceInvoice, quote_id: str,
        *, quote: ServiceJobQuote | None = None,
    ) -> None:
        res = await db.execute(
            select(ServiceJobQuoteItem).where(
                ServiceJobQuoteItem.quote_id == uuid.UUID(quote_id),
                ServiceJobQuoteItem.is_customer_visible == True,
            )
        )
        rows = list(res.scalars().all())
        for qi in rows:
            item = ServiceInvoiceItem(
                id=uuid.uuid4(),
                invoice_id=inv.id,
                booking_id=inv.booking_id,
                job_id=inv.job_id,
                tenant_id=inv.tenant_id,
                item_type=qi.item_type,
                item_name=qi.item_name,
                item_description=qi.item_description,
                quantity=qi.quantity,
                unit_price=qi.unit_price,
                line_total=qi.line_total,
                source_quote_item_id=qi.id,
                is_customer_visible=True,
            )
            db.add(item)
        # Older imported quotes can contain an authoritative aggregate but no
        # normalized item rows. Preserve that audited amount as one service
        # line instead of producing a zero-value invoice.
        if not rows:
            if quote is None:
                quote = await db.get(ServiceJobQuote, uuid.UUID(quote_id))
            try:
                amount = Decimal(str(getattr(quote, "total_amount", 0) or 0))
            except (InvalidOperation, ValueError, TypeError):
                amount = Decimal("0")
            if amount > 0:
                db.add(ServiceInvoiceItem(
                    id=uuid.uuid4(), invoice_id=inv.id,
                    booking_id=inv.booking_id, job_id=inv.job_id,
                    tenant_id=inv.tenant_id, item_type="service",
                    item_name="Approved service estimate", quantity=Decimal("1"),
                    unit_price=amount, line_total=amount,
                    is_customer_visible=True,
                ))

    async def _copy_from_booking(self, db: AsyncSession, inv: ServiceInvoice, booking_id: str) -> None:
        res = await db.execute(
            select(ServiceBooking).where(ServiceBooking.id == uuid.UUID(booking_id))
        )
        booking = res.scalar_one_or_none()
        if not booking or not booking.price_snapshot:
            return
        price = booking.price_snapshot
        raw_base = next((price.get(key) for key in (
            "selected_price_amount", "standard_price", "base_price", "min_price"
        ) if price.get(key) not in (None, "")), 0)
        base = Decimal(str(raw_base or 0))
        if base > 0:
            item = ServiceInvoiceItem(
                id=uuid.uuid4(),
                invoice_id=inv.id,
                booking_id=inv.booking_id,
                job_id=inv.job_id,
                tenant_id=inv.tenant_id,
                item_type="service",
                item_name=price.get("service_name", "Service charge"),
                quantity=Decimal("1"),
                unit_price=base,
                line_total=base,
                is_customer_visible=True,
            )
            db.add(item)

    async def _refresh_totals(self, db: AsyncSession, inv: ServiceInvoice) -> None:
        res = await db.execute(
            select(ServiceInvoiceItem).where(ServiceInvoiceItem.invoice_id == inv.id)
        )
        items = list(res.scalars().all())
        totals = self._recalculate(items)
        # Apply the business vertical's published customer platform fee.
        # total_amount stays the SERVICE value (the provider-commission base); the
        # platform fee is added ON TOP so the customer is billed the inclusive
        # amount. The provider is never charged commission on the platform's fee.
        service_value = Decimal(str(totals["total_amount"]))
        platform_fee = None
        if inv.invoice_source == INV_SRC_BOOKING_BASE:
            booking = await db.get(ServiceBooking, inv.booking_id)
            snapshot = (booking.price_snapshot or {}) if booking is not None else {}
            if snapshot.get("platform_fee") is not None:
                platform_fee = Decimal(str(snapshot["platform_fee"] or 0))
        if platform_fee is None:
            platform_fee = await self._resolve_customer_platform_fee(
                db, inv.category_id, inv.job_id, service_value,
            )
        totals["platform_fee_amount"] = platform_fee
        totals["customer_payable_amount"] = service_value + platform_fee
        await db.execute(
            update(ServiceInvoice)
            .where(ServiceInvoice.id == inv.id)
            .values(**totals, updated_at=_utcnow())
        )

    async def _resolve_customer_platform_fee(
        self, db: AsyncSession, category_id, job_id, service_value: Decimal,
    ) -> Decimal:
        """Resolve the category's business vertical, then use that vertical's
        one published Monetization policy. Category finance columns are not
        runtime authorities for Home Services."""
        if category_id is None:
            return Decimal("0")
        from app.engines.admin_catalog.models import ServiceCategory
        from app.engines.vertical_monetization.calculation_service import (
            calculate_customer_platform_fee, get_active_job_type_rule,
            get_current_policy_by_vertical_key, to_minor,
        )
        vertical_key = (await db.execute(
            select(ServiceCategory.vertical_type)
            .where(ServiceCategory.id == category_id)
        )).scalar_one_or_none()
        if not vertical_key:
            return Decimal("0")
        policy = await get_current_policy_by_vertical_key(db, vertical_key)
        if policy is not None:
            from app.engines.final_records.models import ServiceJob
            job_type_id = (await db.execute(
                select(ServiceJob.job_type_id).where(ServiceJob.id == job_id)
            )).scalar_one_or_none()
            job_type_rule = await get_active_job_type_rule(db, policy.id, job_type_id)
            if job_type_rule is not None and not job_type_rule.customer_charge_enabled:
                policy = None
        result = calculate_customer_platform_fee(
            policy=policy,
            service_subtotal_minor=to_minor(service_value),
            calculation_basis="service_invoice",
        )
        return Decimal(str(result["customer_platform_fee"]))

    # ── Add item to draft invoice ──────────────────────────────────────────────

    async def add_item(
        self, db: AsyncSession, invoice_id: str, tenant_id: str,
        item_type: str, item_name: str, item_description: str | None,
        quantity: float, unit_price: float, is_customer_visible: bool,
        user_id: str, request_id: str | None,
    ) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        self._assert_tenant(inv, tenant_id)
        if inv.status != INV_DRAFT:
            raise ValueError(ERR_INVOICE_ALREADY_ISSUED)
        qty = Decimal(str(quantity))
        up  = Decimal(str(unit_price))
        # Slice 2F-6A: previously no validation existed at all -- a negative
        # quantity or unit_price silently produced a negative line_total that
        # was summed into whichever item_type bucket the caller chose (e.g.
        # "part"), letting an ordinary line item masquerade as an undeclared,
        # unbounded discount. No distinct discount type/flag/bound mechanism
        # exists anywhere in this file (item_type == "discount" is only a
        # summing category in _recalculate, not a validated, bounded discount
        # system), so per policy negative values are rejected outright rather
        # than treated as an intentional discount. Zero quantity is rejected
        # (a zero-quantity line has no meaning); zero unit_price is allowed
        # (a legitimate free/no-charge line item, e.g. warranty part).
        if qty <= Decimal("0"):
            raise ValueError(ERR_INVOICE_ITEM_INVALID)
        if up < Decimal("0"):
            raise ValueError(ERR_INVOICE_ITEM_INVALID)
        item = ServiceInvoiceItem(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            booking_id=inv.booking_id,
            job_id=inv.job_id,
            tenant_id=inv.tenant_id,
            item_type=item_type,
            item_name=item_name,
            item_description=item_description,
            quantity=qty,
            unit_price=up,
            line_total=qty * up,
            is_customer_visible=is_customer_visible,
        )
        db.add(item)
        await db.flush()
        await self._refresh_totals(db, inv)
        await db.commit()
        await db.refresh(item)
        return item.to_dict()

    # ── Issue invoice ──────────────────────────────────────────────────────────

    async def issue_invoice(
        self, db: AsyncSession, invoice_id: str, tenant_id: str,
        user_id: str, request_id: str | None,
    ) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        self._assert_tenant(inv, tenant_id)
        if inv.status == INV_ISSUED:
            raise ValueError(ERR_INVOICE_ALREADY_ISSUED)
        self._assert_transition(inv, INV_ISSUED)
        now = _utcnow()
        old_status = inv.status
        await db.execute(
            update(ServiceInvoice)
            .where(ServiceInvoice.id == inv.id)
            .values(status=INV_ISSUED, issued_at=now, updated_at=now)
        )
        inv.status = INV_ISSUED
        # Sync job status
        await db.execute(
            update(ServiceJob)
            .where(ServiceJob.id == inv.job_id)
            .values(status=JOB_STATUS_INVOICE_ISSUED, updated_at=now)
        )
        await self._log_event(db, inv, FEV_INVOICE_ISSUED, "staff", user_id,
                              old_value={"status": old_status},
                              new_value={"status": INV_ISSUED}, request_id=request_id)
        await self._add_issue_notification(db, inv)
        await db.commit()
        await db.refresh(inv)
        return inv.to_dict()

    # ── Cancel invoice ─────────────────────────────────────────────────────────

    async def cancel_invoice(
        self, db: AsyncSession, invoice_id: str, tenant_id: str,
        reason: str | None, user_id: str, request_id: str | None,
    ) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        self._assert_tenant(inv, tenant_id)
        self._assert_transition(inv, INV_CANCELLED)
        now = _utcnow()
        old_status = inv.status
        await db.execute(
            update(ServiceInvoice)
            .where(ServiceInvoice.id == inv.id)
            .values(status=INV_CANCELLED, cancelled_at=now, updated_at=now)
        )
        inv.status = INV_CANCELLED
        await self._log_event(db, inv, FEV_INVOICE_CANCELLED, "staff", user_id,
                              old_value={"status": old_status},
                              new_value={"status": INV_CANCELLED},
                              reason=reason, request_id=request_id)
        await db.commit()
        await db.refresh(inv)
        return inv.to_dict()

    # ── Get / list ─────────────────────────────────────────────────────────────

    async def get_invoice(self, db: AsyncSession, invoice_id: str, include_items: bool = True) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        data = inv.to_dict()
        if include_items:
            res = await db.execute(
                select(ServiceInvoiceItem).where(ServiceInvoiceItem.invoice_id == inv.id)
            )
            data["items"] = [i.to_dict() for i in res.scalars().all()]
        return data

    async def get_invoice_for_tenant(self, db: AsyncSession, invoice_id: str, tenant_id: str) -> dict:
        """Tenant-scoped invoice fetch — asserts record belongs to tenant before returning."""
        inv = await self._get_invoice(db, invoice_id)
        self._assert_tenant(inv, tenant_id)
        data = inv.to_dict()
        res = await db.execute(
            select(ServiceInvoiceItem).where(ServiceInvoiceItem.invoice_id == inv.id)
        )
        data["items"] = [i.to_dict() for i in res.scalars().all()]
        return data

    async def get_invoice_for_customer(self, db: AsyncSession, invoice_id: str, customer_id: str) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        if str(inv.customer_id) != customer_id:
            raise ValueError(ERR_INVOICE_ACCESS_DENIED)
        data = inv.to_customer_dict()
        res = await db.execute(
            select(ServiceInvoiceItem).where(
                ServiceInvoiceItem.invoice_id == inv.id,
                ServiceInvoiceItem.is_customer_visible == True,
            )
        )
        data["items"] = [i.to_dict() for i in res.scalars().all()]
        return data

    async def get_job_invoice(self, db: AsyncSession, job_id: str, tenant_id: str | None = None) -> dict | None:
        q = select(ServiceInvoice).where(
            ServiceInvoice.job_id == uuid.UUID(job_id),
            ServiceInvoice.status.not_in([INV_CANCELLED]),
        )
        res = await db.execute(q)
        inv = res.scalar_one_or_none()
        if not inv:
            return None
        if tenant_id and str(inv.tenant_id) != tenant_id:
            raise ValueError(ERR_INVOICE_ACCESS_DENIED)
        return inv.to_dict()

    async def list_tenant_invoices(
        self, db: AsyncSession, tenant_id: str, status: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        limit = min(limit, 500)
        q = select(ServiceInvoice).where(ServiceInvoice.tenant_id == uuid.UUID(tenant_id))
        if status:
            q = q.where(ServiceInvoice.status == status)
        q = q.order_by(ServiceInvoice.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(q)
        return [inv.to_dict() for inv in res.scalars().all()]

    async def list_customer_invoices(
        self, db: AsyncSession, customer_id: str, status: str | None = None,
        limit: int = 50, offset: int = 0,
    ) -> list[dict]:
        """A customer's own invoices, customer-safe (no wallet/commission).

        MODULE-L5-17/18: the customer invoice router had detail/receipt/confirm but
        no list, so the customer had no invoice history from the canonical engine.
        """
        limit = min(limit, 200)
        q = select(ServiceInvoice).where(ServiceInvoice.customer_id == uuid.UUID(customer_id))
        if status:
            q = q.where(ServiceInvoice.status == status)
        q = q.order_by(ServiceInvoice.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(q)
        return [inv.to_customer_dict() for inv in res.scalars().all()]

    async def list_all_invoices(
        self, db: AsyncSession, tenant_id: str | None = None,
        status: str | None = None, limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        limit = min(limit, 500)
        q = select(ServiceInvoice)
        if tenant_id:
            q = q.where(ServiceInvoice.tenant_id == uuid.UUID(tenant_id))
        if status:
            q = q.where(ServiceInvoice.status == status)
        q = q.order_by(ServiceInvoice.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(q)
        return [inv.to_dict() for inv in res.scalars().all()]

    async def update_payment_status(self, db: AsyncSession, invoice_id: uuid.UUID,
                                     payment_status: str, paid_at: datetime | None = None) -> None:
        vals: dict = {"payment_status": payment_status, "updated_at": _utcnow()}
        if paid_at:
            vals["paid_at"] = paid_at
        if payment_status == "collected":
            vals["status"] = INV_PAYMENT_COLLECTED
        elif payment_status == "verified":
            vals["status"] = INV_PAID
        await db.execute(update(ServiceInvoice).where(ServiceInvoice.id == invoice_id).values(**vals))

    async def update_commission_status(self, db: AsyncSession, invoice_id: uuid.UUID,
                                        commission_status: str) -> None:
        await db.execute(
            update(ServiceInvoice)
            .where(ServiceInvoice.id == invoice_id)
            .values(commission_status=commission_status, updated_at=_utcnow())
        )
