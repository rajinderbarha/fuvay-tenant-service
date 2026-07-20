"""Phase 2A Slice 2F-16A — Quote Contract, Invoice Lineage, Read Privacy and
Final-State Closure.

Findings and fixes (all directly connected to the quote-checklist ->
invoice_payment lineage 2F-16 discovered but did not fully close):

1. **Same-tenant cross-ServiceJob / cross-customer quote substitution in
   `invoice_payment.create_invoice`.** The 2F-16 fix validated only
   `quote.tenant_id == tenant_id` before copying a quote's items into an
   invoice -- it never checked that the quote actually belonged to the
   SPECIFIC ServiceJob being invoiced, or that the quote's customer matched
   that ServiceJob's customer. A staff member (or a crafted request) could
   supply `job_id=<ServiceJob A>` together with `quote_id=<a DIFFERENT,
   same-tenant ServiceJob B's approved quote>` and have Job B's approved
   quote silently become Job A's invoice -- attributing another customer's
   negotiated price to an unrelated job/customer. Fixed: `quote.job_id ==
   job.id` and `quote.customer_id == job.customer_id` are now both required.

2. **Hidden-item total mismatch shown to the customer.** `ServiceJobQuote`'s
   stored `total_amount`/`customer_payable_amount` (computed by
   `_recalculate`) sums ALL items including hidden (`is_customer_visible=False`)
   ones -- correct for the PROVIDER view. `get_quote`'s 2F-16 fix already
   filtered the `items` list to customer-visible-only for a customer caller,
   but still returned the UNFILTERED total alongside it -- a customer would
   see a total that did not reconcile to the line items shown, effectively
   approving an undisclosed hidden charge. Fixed: the customer-facing
   response now recomputes labour/parts/service/discount/tax/total purely
   from the customer-visible items being returned, so what is displayed
   always reconciles to what is itemized. This also matches what
   `invoice_payment._copy_from_quote` actually invoices (customer-visible
   items only), so the customer-visible total now equals the eventual
   invoice total.

3. **`QUOTE_NOT_FOUND` vs `QUOTE_ACCESS_DENIED` (and the checklist
   equivalent) were externally distinguishable** -- a foreign-tenant or
   foreign-customer quote/checklist raised `*_ACCESS_DENIED`, which the
   app's `ValueError`->HTTP mapping resolves to a different status code than
   `*_NOT_FOUND`, letting a caller infer "this record exists but isn't
   mine" versus "this record doesn't exist" -- disclosing existence of
   another tenant's/customer's data. Fixed: `get_quote`, `list_quote_events`,
   and `get_checklist` all now raise the SAME `*_NOT_FOUND` code for both
   missing and foreign-owned records (mirrors the established Booking-series
   privacy-safe-404 pattern).

4. **Provider-only draft-editing events leaked into customer event
   history.** `list_quote_events` returned every event unfiltered to a
   customer caller, including internal item-added/updated/removed events
   from before the quote was even sent. Fixed: a customer caller now only
   sees `CUSTOMER_VISIBLE_QUOTE_EVENT_TYPES` (sent/approved/rejected/
   revision-requested/revised/expired/cancelled).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


def _db_returning(*results):
    db = MagicMock()
    rs = []
    for res in results:
        r = MagicMock()
        r.scalar_one_or_none.return_value = res
        rs.append(r)
    db.execute = AsyncMock(side_effect=rs)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ── Cross-ServiceJob / cross-customer invoice substitution ─────────────────

@pytest.mark.asyncio
class TestInvoiceQuoteServiceJobCustomerLinkage:
    async def test_quote_from_different_servicejob_same_tenant_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        tenant_id = uuid.uuid4()
        job_a = MagicMock(id=uuid.uuid4(), tenant_id=tenant_id, booking_id=uuid.uuid4(),
                           customer_id=uuid.uuid4(), category_id=None, offering_id=None)
        # quote actually belongs to a DIFFERENT ServiceJob (job B) in the SAME tenant
        quote_for_job_b = MagicMock(tenant_id=tenant_id, job_id=uuid.uuid4(),
                                     customer_id=job_a.customer_id, status="customer_approved")
        db = _db_returning(job_a, None, quote_for_job_b)
        with pytest.raises(ValueError, match="INVOICE_ACCESS_DENIED"):
            await svc.create_invoice(
                db, job_id=str(job_a.id), tenant_id=str(tenant_id),
                source="approved_quote", quote_id=str(uuid.uuid4()), notes=None,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_quote_for_different_customer_same_tenant_same_job_id_rejected(self):
        """Even if job_id somehow coincided (defensive-in-depth), a quote
        whose customer_id does not match the ServiceJob's own customer_id
        must still be rejected."""
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        tenant_id = uuid.uuid4()
        job = MagicMock(id=uuid.uuid4(), tenant_id=tenant_id, booking_id=uuid.uuid4(),
                         customer_id=uuid.uuid4(), category_id=None, offering_id=None)
        quote_wrong_customer = MagicMock(tenant_id=tenant_id, job_id=job.id,
                                          customer_id=uuid.uuid4(), status="customer_approved")
        db = _db_returning(job, None, quote_wrong_customer)
        with pytest.raises(ValueError, match="INVOICE_ACCESS_DENIED"):
            await svc.create_invoice(
                db, job_id=str(job.id), tenant_id=str(tenant_id),
                source="approved_quote", quote_id=str(uuid.uuid4()), notes=None,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_matching_servicejob_and_customer_succeeds(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        tenant_id = uuid.uuid4()
        job = MagicMock(id=uuid.uuid4(), tenant_id=tenant_id, booking_id=uuid.uuid4(),
                         customer_id=uuid.uuid4(), category_id=None, offering_id=None)
        quote = MagicMock(tenant_id=tenant_id, job_id=job.id, customer_id=job.customer_id,
                           status="customer_approved")
        no_items = MagicMock(); no_items.scalars.return_value.all.return_value = []
        db = _db_returning(job, None, quote, no_items, no_items, None)
        result = await svc.create_invoice(
            db, job_id=str(job.id), tenant_id=str(tenant_id),
            source="approved_quote", quote_id=str(uuid.uuid4()), notes=None,
            user_id=str(uuid.uuid4()), request_id=None,
        )
        assert result is not None
        db.add.assert_called()


# ── Hidden-item total reconciliation ────────────────────────────────────────

@pytest.mark.asyncio
class TestHiddenItemTotalReconciliation:
    async def test_customer_total_excludes_hidden_item_amount(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4())
        q.to_dict = lambda: {"id": str(q.id), "total_amount": "600",
                              "customer_payable_amount": "600"}
        visible = MagicMock(is_customer_visible=True, item_type="labour", line_total=Decimal("500"))
        visible.to_dict = lambda: {"item_name": "Labour", "line_total": "500"}
        hidden = MagicMock(is_customer_visible=False, item_type="labour", line_total=Decimal("100"))
        hidden.to_dict = lambda: {"item_name": "hidden markup", "line_total": "100"}
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [visible, hidden]
        db = MagicMock()
        qr = MagicMock(); qr.scalar_one_or_none.return_value = q
        db.execute = AsyncMock(side_effect=[qr, items_result])
        result = await svc.get_quote(db, str(q.id), customer_id=str(q.customer_id))
        # Stored total (600) included the hidden $100 item; the customer-facing
        # total must reconcile to ONLY the $500 visible item shown.
        assert result["total_amount"] == "500"
        assert result["customer_payable_amount"] == "500"
        assert len(result["items"]) == 1

    async def test_provider_total_unaffected_still_includes_hidden_item(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4())
        q.to_dict = lambda: {"id": str(q.id), "total_amount": "600",
                              "customer_payable_amount": "600"}
        hidden = MagicMock(is_customer_visible=False, item_type="labour", line_total=Decimal("100"))
        hidden.to_dict = lambda: {"item_name": "hidden markup"}
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [hidden]
        db = MagicMock()
        qr = MagicMock(); qr.scalar_one_or_none.return_value = q
        db.execute = AsyncMock(side_effect=[qr, items_result])
        result = await svc.get_quote(db, str(q.id), tenant_id=str(q.tenant_id))
        # Provider view is unaffected -- stored total (including hidden items) is authoritative.
        assert result["total_amount"] == "600"
        assert len(result["items"]) == 1


# ── Privacy-equivalent foreign vs missing errors ────────────────────────────

@pytest.mark.asyncio
class TestPrivacyEquivalentErrors:
    async def test_get_quote_missing_and_foreign_tenant_raise_same_code(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        missing_db = _db_returning(None)
        with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
            await svc.get_quote(missing_db, str(uuid.uuid4()))

        q = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4())
        foreign_db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
            await svc.get_quote(foreign_db, str(q.id), tenant_id=str(uuid.uuid4()))

    async def test_get_checklist_missing_and_foreign_tenant_raise_same_code(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        missing_db = _db_returning(None)
        with pytest.raises(ValueError, match="CHECKLIST_NOT_FOUND"):
            await svc.get_checklist(missing_db, str(uuid.uuid4()))

        cl = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        foreign_db = _db_returning(cl)
        with pytest.raises(ValueError, match="CHECKLIST_NOT_FOUND"):
            await svc.get_checklist(foreign_db, str(cl.id), tenant_id=str(uuid.uuid4()))


# ── Provider-only events filtered from customer history ─────────────────────

@pytest.mark.asyncio
class TestCustomerEventHistoryFiltering:
    async def test_customer_does_not_see_draft_editing_events(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4())
        item_added_event = MagicMock(event_type="quote_item_added")
        item_added_event.to_dict = lambda: {"event_type": "quote_item_added"}
        sent_event = MagicMock(event_type="quote_sent_to_customer")
        sent_event.to_dict = lambda: {"event_type": "quote_sent_to_customer"}
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [item_added_event, sent_event]
        db = MagicMock()
        qr = MagicMock(); qr.scalar_one_or_none.return_value = q
        db.execute = AsyncMock(side_effect=[qr, events_result])
        result = await svc.list_quote_events(db, str(q.id), customer_id=str(q.customer_id))
        assert len(result) == 1
        assert result[0]["event_type"] == "quote_sent_to_customer"

    async def test_provider_sees_all_events_including_draft_editing(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4())
        item_added_event = MagicMock(event_type="quote_item_added")
        item_added_event.to_dict = lambda: {"event_type": "quote_item_added"}
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [item_added_event]
        db = MagicMock()
        qr = MagicMock(); qr.scalar_one_or_none.return_value = q
        db.execute = AsyncMock(side_effect=[qr, events_result])
        result = await svc.list_quote_events(db, str(q.id), tenant_id=str(q.tenant_id))
        assert len(result) == 1


# ── Customer-decision response filtering ─────────────────────────────────────

@pytest.mark.asyncio
class TestCustomerDecisionResponseFiltering:
    """customer_approve/reject/request_revision previously returned
    q.to_dict() directly, exposing provider_internal_notes in the DECISION
    RESPONSE even after get_quote's own read-path filtering was fixed."""

    async def test_approve_response_hides_internal_notes(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import QS_SENT_TO_CUSTOMER
        from unittest.mock import patch
        svc = ServiceJobQuoteService()
        customer_id = uuid.uuid4()
        q = MagicMock(id=uuid.uuid4(), customer_id=customer_id, status=QS_SENT_TO_CUSTOMER,
                      idempotency_key=None)
        q.to_dict = lambda: {"id": str(q.id), "provider_internal_notes": "margin: 35%"}
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        r1 = MagicMock(); r1.scalar_one_or_none.return_value = q
        r2 = MagicMock(); r2.scalar_one_or_none.return_value = None
        r3 = MagicMock(); r3.scalar_one_or_none.return_value = None
        db = _db_returning(q, None, None)
        db.execute = AsyncMock(side_effect=[r1, r2, r3, items_result])
        with patch("app.engines.quote_checklist.notifications.notify_provider_quote_decision",
                   new=AsyncMock()):
            result = await svc.customer_approve(
                db, str(q.id), str(customer_id), idempotency_key="k1",
                user_id=str(customer_id), request_id=None,
            )
        assert "provider_internal_notes" not in result

    async def test_reject_response_hides_internal_notes(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import QS_SENT_TO_CUSTOMER
        from unittest.mock import patch
        svc = ServiceJobQuoteService()
        customer_id = uuid.uuid4()
        q = MagicMock(id=uuid.uuid4(), customer_id=customer_id, status=QS_SENT_TO_CUSTOMER)
        q.to_dict = lambda: {"id": str(q.id), "provider_internal_notes": "margin: 35%"}
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        r1 = MagicMock(); r1.scalar_one_or_none.return_value = q
        r2 = MagicMock(); r2.scalar_one_or_none.return_value = None
        r3 = MagicMock(); r3.scalar_one_or_none.return_value = None
        db = _db_returning(q, None, None)
        db.execute = AsyncMock(side_effect=[r1, r2, r3, items_result])
        with patch("app.engines.quote_checklist.notifications.notify_provider_quote_decision",
                   new=AsyncMock()):
            result = await svc.customer_reject(
                db, str(q.id), str(customer_id), reason="too expensive",
                user_id=str(customer_id), request_id=None,
            )
        assert "provider_internal_notes" not in result


# ── Canonical dependency role semantics ──────────────────────────────────────

@pytest.mark.asyncio
class TestCanonicalDependencyRoles:
    async def test_admits_only_canonical_roles(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        for role in ("super_admin", "tenant_owner", "staff"):
            user = MagicMock(role=role, access_scope=None, permission_overrides=None, force_password_change=False)
            result = await require_owner_or_office_staff_mutation(user)
            assert result is user

    async def test_denies_prohibited_aliases(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        for role in ("office_staff", "tenant_manager", "manager", "supervisor"):
            user = MagicMock(role=role, access_scope=None, permission_overrides=None)
            with pytest.raises(ServiceOSException):
                await require_owner_or_office_staff_mutation(user)

    async def test_denies_technician_and_customer(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        for role in ("technician", "customer", "guest"):
            user = MagicMock(role=role, access_scope=None, permission_overrides=None)
            with pytest.raises(ServiceOSException):
                await require_owner_or_office_staff_mutation(user)

    async def test_denies_unknown_role(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        user = MagicMock(role="fabricated_role_xyz", access_scope=None, permission_overrides=None)
        with pytest.raises(ServiceOSException):
            await require_owner_or_office_staff_mutation(user)

    async def test_denies_readonly_access_scope(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        user = MagicMock(role="tenant_owner", access_scope="customer_support_limited",
                          permission_overrides=None)
        with pytest.raises(ServiceOSException):
            await require_owner_or_office_staff_mutation(user)

    async def test_super_admin_exempt_from_readonly_scope(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        user = MagicMock(role="super_admin", access_scope="customer_support_limited",
                          permission_overrides=None, force_password_change=False)
        result = await require_owner_or_office_staff_mutation(user)
        assert result is user
