"""Phase 2A Slice 2F-16 — Quote Checklist Authorization, Customer Decision,
Amount Integrity and Alternate-Route Closure.

Module discovered: app.engines.quote_checklist (Sprint 22 "Quote Approval +
Checklist Engine"). Lineage confirmed via direct import: ServiceJobQuote/
ServiceJobQuoteItem/ServiceJobChecklist etc. all reference `job_id` resolved
against `app.engines.final_records.models.ServiceJob` (NOT field_ops.Job, NOT
Booking directly, though `booking_id` is denormalized from job.booking_id).
field_ops has its own, entirely distinct `JobQuote` model tied to
`field_ops.Job` -- a separate pipeline, not touched or merged by this slice.

Findings and fixes:

1. **provider_router.py's `staff_router`/`checklist_router`/`provider_router`
   mutation routes had ZERO persona/permission checks** -- `Depends(get_current_user)`
   only. Any authenticated user of ANY role/tenant (a customer, a technician,
   a cross-tenant staff member) could create/edit/delete quote items, send
   quotes to customers, cancel quotes, or complete checklists for ANY job in
   ANY tenant. Fixed: all mutation routes now use
   `require_owner_or_office_staff_mutation` (existing dependency -- no new
   role/permission; admits tenant_owner/staff/super_admin, excludes customer
   AND technician since no technician frontend caller exists for these
   routes -- only frontend/tenant-portal's web staff UI calls them; denies
   read-only tenant access_scope).

2. **`get_quote`/`get_checklist`/`list_quote_events` had NO ownership filter
   at all** -- any authenticated user could fetch ANY quote or checklist's
   full detail (including `provider_internal_notes`) by ID alone, regardless
   of tenant or customer. Fixed: `get_quote`/`get_checklist` now accept
   `tenant_id`/`customer_id` and enforce them; every router call site updated
   to pass its own scoping identifier.

3. **`customer_router.py` had no explicit canonical-customer role check** --
   `get_current_user` only (ownership at the service layer made cross-customer
   impersonation impractical since customer_id is always the caller's own
   server-derived user_id, but a non-customer role could still reach these
   routes). Fixed: all customer routes now use `require_customer`.

4. **`create_checklist` trusted client-supplied `job_id`/`tenant_id` with NO
   validation** -- a checklist could be fabricated against a nonexistent
   job_id, or one belonging to a different tenant. Fixed: mirrors
   `create_quote`'s own job-ownership check (job must exist and belong to
   the caller's tenant).

5. **`add_item`/`update_item` had no negative quantity/price validation** --
   a negative unit_price or quantity would silently corrupt the recalculated
   total. Fixed: both reject negative values.

6. **`add_item`/`update_item`/`remove_item` only checked `_assert_not_locked`
   (locked_at is set ONLY on customer approval)** -- a quote already
   `sent_to_customer` (customer actively deciding), or in any terminal status
   (rejected/expired/cancelled), was NOT "locked" and could still have its
   line items silently mutated, changing the total after the customer had
   already seen or decided on it. Fixed: item mutations are now restricted to
   `ITEM_EDITABLE_QUOTE_STATUSES` (draft/submitted_to_provider/
   provider_rejected/revision_requested/revised).

Preserved, re-verified unaffected: `customer_approve`/`customer_reject`/
`customer_request_revision`'s existing `quote.customer_id == customer_id`
ownership check (already correct, already used the server-derived
`user.user_id`, never client-suppliable); `_assert_transition`'s state-machine
enforcement (unchanged); `field_ops.JobQuote` (a distinct model/pipeline, not
touched); `PartsRequest` (no reference exists anywhere in quote_checklist --
item_type="part"/"material" are cost line entries only, never linked to an
actual PartsRequest row).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.quote_checklist.constants import (
    QS_DRAFT, QS_SENT_TO_CUSTOMER, QS_CUSTOMER_APPROVED, QS_CUSTOMER_REJECTED,
)


def _db_returning(*results):
    db = MagicMock()
    rs = []
    for res in results:
        r = MagicMock()
        r.scalar_one_or_none.return_value = res
        rs.append(r)
    db.execute = AsyncMock(side_effect=rs)
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _quote(**overrides):
    q = MagicMock()
    q.id = overrides.get("id", uuid.uuid4())
    q.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    q.customer_id = overrides.get("customer_id", uuid.uuid4())
    q.job_id = overrides.get("job_id", uuid.uuid4())
    q.booking_id = overrides.get("booking_id", uuid.uuid4())
    q.status = overrides.get("status", QS_DRAFT)
    q.locked_at = overrides.get("locked_at", None)
    q.idempotency_key = overrides.get("idempotency_key", None)
    return q


# ── Router-level authorization source proofs ────────────────────────────────

class TestRouterGuardSources:
    def _read(self, relpath):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), *relpath.split("/"))
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_provider_staff_checklist_mutations_use_office_staff_mutation_guard(self):
        src = self._read("app/engines/quote_checklist/provider_router.py")
        for fn in ("provider_cancel_quote", "staff_create_quote", "staff_add_item",
                   "staff_update_item", "staff_remove_item", "staff_send_to_customer",
                   "staff_mark_revised", "staff_cancel_quote", "staff_create_checklist",
                   "staff_update_checklist_item", "staff_complete_checklist"):
            body = src.split(f"async def {fn}(")[1].split("\n\n\n")[0]
            assert "require_owner_or_office_staff_mutation" in body, fn

    def test_customer_router_uses_require_customer(self):
        src = self._read("app/engines/quote_checklist/customer_router.py")
        for fn in ("customer_list_quotes", "customer_get_quote", "customer_approve_quote",
                   "customer_reject_quote", "customer_request_revision", "customer_quote_events"):
            body = src.split(f"async def {fn}(")[1].split("\n\n\n")[0]
            assert "require_customer" in body, fn


# ── get_quote / get_checklist IDOR fix ───────────────────────────────────────

@pytest.mark.asyncio
class TestQuoteChecklistIDORFix:
    async def test_get_quote_denies_wrong_tenant(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        db = _db_returning(q)
        # Slice 2F-16A: foreign-tenant ownership now raises the same
        # privacy-safe QUOTE_NOT_FOUND as a genuinely missing quote.
        with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
            await svc.get_quote(db, str(q.id), tenant_id=str(uuid.uuid4()))

    async def test_get_quote_denies_wrong_customer(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
            await svc.get_quote(db, str(q.id), customer_id=str(uuid.uuid4()))

    async def test_get_quote_correct_tenant_succeeds(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        db = _db_returning(q, None)  # quote, then items query
        result = await svc.get_quote(db, str(q.id), tenant_id=str(q.tenant_id))
        assert result is not None

    async def test_get_quote_hides_internal_notes_and_hidden_items_from_customer(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        q.provider_internal_notes = "cost basis: 40% margin"
        q.to_dict = lambda: {"id": str(q.id), "provider_internal_notes": q.provider_internal_notes,
                              "customer_payable_amount": "500"}
        visible_item = MagicMock(is_customer_visible=True, item_type="labour", line_total=Decimal("500"))
        visible_item.to_dict = lambda: {"item_name": "Labour"}
        hidden_item = MagicMock(is_customer_visible=False, item_type="labour", line_total=Decimal("100"))
        hidden_item.to_dict = lambda: {"item_name": "internal markup"}
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [visible_item, hidden_item]
        db = MagicMock()
        qr = MagicMock(); qr.scalar_one_or_none.return_value = q
        db.execute = AsyncMock(side_effect=[qr, items_result])
        result = await svc.get_quote(db, str(q.id), customer_id=str(q.customer_id))
        assert "provider_internal_notes" not in result
        assert len(result["items"]) == 1
        assert result["items"][0]["item_name"] == "Labour"

    async def test_get_quote_provider_still_sees_internal_notes_and_all_items(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        q.to_dict = lambda: {"id": str(q.id), "provider_internal_notes": "internal", "customer_payable_amount": "500"}
        hidden_item = MagicMock(is_customer_visible=False, item_type="labour", line_total=Decimal("100"))
        hidden_item.to_dict = lambda: {"item_name": "internal markup"}
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [hidden_item]
        db = MagicMock()
        qr = MagicMock(); qr.scalar_one_or_none.return_value = q
        db.execute = AsyncMock(side_effect=[qr, items_result])
        result = await svc.get_quote(db, str(q.id), tenant_id=str(q.tenant_id))
        assert result["provider_internal_notes"] == "internal"
        assert len(result["items"]) == 1

    async def test_get_checklist_denies_wrong_tenant(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        cl = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        db = _db_returning(cl)
        with pytest.raises(ValueError, match="CHECKLIST_NOT_FOUND"):
            await svc.get_checklist(db, str(cl.id), tenant_id=str(uuid.uuid4()))


# ── create_checklist job/tenant ownership fix ────────────────────────────────

@pytest.mark.asyncio
class TestCreateChecklistJobOwnership:
    async def test_nonexistent_job_rejected(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        db = _db_returning(None)
        with pytest.raises(ValueError, match="QUOTE_JOB_NOT_FOUND"):
            await svc.create_checklist(
                db, job_id=str(uuid.uuid4()), booking_id=str(uuid.uuid4()),
                tenant_id=str(uuid.uuid4()), checklist_type="inspection",
                template_id=None, user_id=str(uuid.uuid4()), custom_items=None,
            )
        db.add.assert_not_called()

    async def test_wrong_tenant_job_rejected(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        job = MagicMock(tenant_id=uuid.uuid4())
        db = _db_returning(job)
        with pytest.raises(ValueError, match="CHECKLIST_ACCESS_DENIED"):
            await svc.create_checklist(
                db, job_id=str(uuid.uuid4()), booking_id=str(uuid.uuid4()),
                tenant_id=str(uuid.uuid4()), checklist_type="inspection",
                template_id=None, user_id=str(uuid.uuid4()), custom_items=None,
            )
        db.add.assert_not_called()

    async def test_matching_tenant_job_succeeds(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        tenant_id = uuid.uuid4()
        job = MagicMock(tenant_id=tenant_id)
        db = _db_returning(job)
        result = await svc.create_checklist(
            db, job_id=str(uuid.uuid4()), booking_id=str(uuid.uuid4()),
            tenant_id=str(tenant_id), checklist_type="inspection",
            template_id=None, user_id=str(uuid.uuid4()), custom_items=None,
        )
        assert result is not None


# ── Negative quantity/price rejection ────────────────────────────────────────

@pytest.mark.asyncio
class TestAmountIntegrityNegativeValues:
    async def test_add_item_negative_quantity_rejected(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_ITEM_INVALID"):
            await svc.add_item(
                db, str(q.id), str(q.tenant_id), item_type="labour", item_name="x",
                item_description=None, quantity=-1, unit_price=100,
                is_required=True, is_customer_visible=True,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_add_item_negative_price_rejected(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_ITEM_INVALID"):
            await svc.add_item(
                db, str(q.id), str(q.tenant_id), item_type="labour", item_name="x",
                item_description=None, quantity=1, unit_price=-50,
                is_required=True, is_customer_visible=True,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_update_item_negative_quantity_rejected(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote()
        item = MagicMock(quantity=Decimal("1"), unit_price=Decimal("100"))
        db = _db_returning(q, item)
        with pytest.raises(ValueError, match="QUOTE_ITEM_INVALID"):
            await svc.update_item(
                db, str(q.id), str(uuid.uuid4()), str(q.tenant_id),
                item_name=None, item_description=None, quantity=-5, unit_price=None,
                is_customer_visible=None, user_id=str(uuid.uuid4()), request_id=None,
            )


# ── Post-final / post-send item mutation blocked ────────────────────────────

@pytest.mark.asyncio
class TestFinalQuoteItemMutationBlocked:
    async def test_add_item_after_sent_to_customer_rejected(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote(status=QS_SENT_TO_CUSTOMER)
        db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_ALREADY_LOCKED"):
            await svc.add_item(
                db, str(q.id), str(q.tenant_id), item_type="labour", item_name="x",
                item_description=None, quantity=1, unit_price=100,
                is_required=True, is_customer_visible=True,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_remove_item_after_customer_rejected_status_blocked(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote(status=QS_CUSTOMER_REJECTED)
        db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_ALREADY_LOCKED"):
            await svc.remove_item(db, str(q.id), str(uuid.uuid4()), str(q.tenant_id),
                                   user_id=str(uuid.uuid4()), request_id=None)

    async def test_add_item_while_draft_still_succeeds(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote(status=QS_DRAFT)
        db = _db_returning(q, None, None)  # quote, items-for-recalc, update result
        result = await svc.add_item(
            db, str(q.id), str(q.tenant_id), item_type="labour", item_name="x",
            item_description=None, quantity=1, unit_price=100,
            is_required=True, is_customer_visible=True,
            user_id=str(uuid.uuid4()), request_id=None,
        )
        assert result is not None


# ── Customer decision ownership (pre-existing, re-verified) ─────────────────

@pytest.mark.asyncio
class TestCustomerDecisionOwnershipPreserved:
    async def test_foreign_customer_cannot_approve(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _quote(status=QS_SENT_TO_CUSTOMER)
        db = _db_returning(q)
        with pytest.raises(ValueError, match="QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED"):
            await svc.customer_approve(
                db, str(q.id), str(uuid.uuid4()), idempotency_key="k1",
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_correct_customer_can_approve(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from unittest.mock import patch
        svc = ServiceJobQuoteService()
        q = _quote(status=QS_SENT_TO_CUSTOMER)
        # quote lookup, quote-update, job-status-sync update, then (Slice
        # 2F-16A) _customer_dict's own items-for-total-reconciliation query
        db = _db_returning(q, None, None)
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        r1, r2, r3 = MagicMock(), MagicMock(), MagicMock()
        r1.scalar_one_or_none.return_value = q
        r2.scalar_one_or_none.return_value = None
        r3.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[r1, r2, r3, items_result])
        with patch("app.engines.quote_checklist.notifications.notify_provider_quote_decision",
                   new=AsyncMock()), patch(
            "app.engines.vertical_monetization.charge_service.create_charge_for_quote",
            new=AsyncMock(return_value=None),
        ):
            result = await svc.customer_approve(
                db, str(q.id), str(q.customer_id), idempotency_key="k1",
                user_id=str(q.customer_id), request_id=None,
            )
        assert result is not None


# ── Invoice-from-quote cross-tenant/status bypass fix ───────────────────────

@pytest.mark.asyncio
class TestInvoiceFromQuoteBoundary:
    """app.engines.invoice_payment.invoice_service.ServiceInvoiceService.create_invoice
    previously copied ServiceJobQuoteItem rows from ANY quote_id (source=
    "approved_quote") with NO check that the quote belongs to the caller's
    tenant or is actually in customer_approved status -- and the check (once
    added) had to run BEFORE any db.add/flush to avoid leaving a partial
    invoice row behind on rejection."""

    async def test_wrong_tenant_quote_rejected_before_persistence(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        job = MagicMock(tenant_id=uuid.uuid4(), booking_id=uuid.uuid4(),
                         customer_id=uuid.uuid4(), category_id=None, offering_id=None)
        tenant_id = str(job.tenant_id)
        quote = MagicMock(tenant_id=uuid.uuid4(), status="customer_approved")
        db = _db_returning(job, None, quote)  # job lookup, no existing invoice, quote lookup
        with pytest.raises(ValueError, match="INVOICE_ACCESS_DENIED"):
            await svc.create_invoice(
                db, job_id=str(uuid.uuid4()), tenant_id=tenant_id,
                source="approved_quote", quote_id=str(uuid.uuid4()), notes=None,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()

    async def test_non_approved_quote_rejected_before_persistence(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        job = MagicMock(tenant_id=uuid.uuid4(), booking_id=uuid.uuid4(),
                         customer_id=uuid.uuid4(), category_id=None, offering_id=None)
        tenant_id = str(job.tenant_id)
        quote = MagicMock(tenant_id=job.tenant_id, job_id=job.id,
                           customer_id=job.customer_id, status="draft")
        db = _db_returning(job, None, quote)
        with pytest.raises(ValueError, match="INVOICE_INVALID_STATUS"):
            await svc.create_invoice(
                db, job_id=str(uuid.uuid4()), tenant_id=tenant_id,
                source="approved_quote", quote_id=str(uuid.uuid4()), notes=None,
                user_id=str(uuid.uuid4()), request_id=None,
            )
        db.add.assert_not_called()
