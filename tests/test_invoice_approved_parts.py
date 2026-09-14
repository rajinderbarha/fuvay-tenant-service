"""Approved-part billing across invoices, payments, and provider charges."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar_one_or_none.return_value = items[0] if items else None
    return result


def _db(*results):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_approved_part_becomes_one_snapshotted_invoice_line():
    from app.engines.execution.models import PartsRequest
    from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
    from app.engines.invoice_payment.models import ServiceInvoice

    existing_id, new_id = uuid.uuid4(), uuid.uuid4()
    inv = MagicMock(spec=ServiceInvoice)
    inv.id, inv.booking_id, inv.job_id, inv.tenant_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )

    existing = MagicMock(spec=PartsRequest)
    existing.id = existing_id
    new = MagicMock(spec=PartsRequest)
    new.id = new_id
    new.part_name = "AC capacitor"
    new.reason = "Burnt out"
    new.quantity = 2
    new.estimated_cost = Decimal("850.00")

    db = _db(_result([existing_id]), _result([existing, new]))
    added = await ServiceInvoiceService()._add_approved_parts(db, inv)

    assert added == 1
    db.add.assert_called_once()
    line = db.add.call_args.args[0]
    assert line.source_parts_request_id == new_id
    assert line.item_type == "part"
    assert line.quantity == Decimal("2")
    assert line.unit_price == Decimal("850.00")
    assert line.line_total == Decimal("1700.00")


@pytest.mark.asyncio
async def test_invoice_totals_include_parts_but_platform_fee_base_does_not():
    from app.engines.invoice_payment.constants import INV_SRC_MANUAL_FINAL
    from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
    from app.engines.invoice_payment.models import ServiceInvoice, ServiceInvoiceItem

    inv = MagicMock(spec=ServiceInvoice)
    inv.id, inv.booking_id, inv.job_id, inv.category_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )
    inv.invoice_source = INV_SRC_MANUAL_FINAL
    service = ServiceInvoiceItem(
        item_type="service", line_total=Decimal("1000.00")
    )
    part = ServiceInvoiceItem(
        item_type="part", line_total=Decimal("200.00"),
        source_parts_request_id=uuid.uuid4(),
    )
    db = _db(_result([service, part]), MagicMock())
    svc = ServiceInvoiceService()

    with patch.object(
        svc, "_resolve_customer_platform_fee", AsyncMock(return_value=Decimal("50.00"))
    ) as fee:
        await svc._refresh_totals(db, inv)

    fee.assert_awaited_once_with(db, inv.category_id, inv.job_id, Decimal("1000.00"))
    values = db.execute.await_args_list[1].args[0].compile().params
    assert values["parts_amount"] == Decimal("200.00")
    assert values["total_amount"] == Decimal("1200.00")
    assert values["platform_fee_amount"] == Decimal("50.00")
    assert values["customer_payable_amount"] == Decimal("1250.00")


@pytest.mark.asyncio
async def test_issuing_an_existing_draft_picks_up_newly_approved_parts():
    from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
    from app.engines.invoice_payment.models import ServiceInvoice

    inv = MagicMock(spec=ServiceInvoice)
    inv.id, inv.job_id, inv.tenant_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    inv.status = "draft"
    inv.to_dict.return_value = {"status": "issued"}
    db = _db(_result([inv]), MagicMock(), MagicMock())
    svc = ServiceInvoiceService()

    with patch.object(svc, "_add_approved_parts", AsyncMock(return_value=1)) as add_parts, \
         patch.object(svc, "_refresh_totals", AsyncMock()) as refresh_totals, \
         patch.object(svc, "_log_event", AsyncMock()), \
         patch.object(svc, "_add_issue_notification", AsyncMock()):
        await svc.issue_invoice(
            db, str(inv.id), str(inv.tenant_id), str(uuid.uuid4()), "request-id"
        )

    add_parts.assert_awaited_once_with(db, inv)
    refresh_totals.assert_awaited_once_with(db, inv)
    assert db.refresh.await_count >= 2


@pytest.mark.asyncio
async def test_preinvoice_visit_fee_also_includes_approved_parts():
    from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService

    tenant_id = uuid.uuid4()
    service = DirectPaymentsService(MagicMock(), tenant_id)
    job = MagicMock(id=uuid.uuid4(), booking_id=uuid.uuid4())
    booking = MagicMock(price_snapshot={"visit_fee": "100.00", "currency": "INR"})

    with patch.object(service, "_invoice_for_job", AsyncMock(return_value=None)), \
         patch.object(service, "_current_quote", AsyncMock(return_value=None)), \
         patch.object(service, "_workflow", AsyncMock(return_value=None)), \
         patch.object(
             service, "_approved_parts_total", AsyncMock(return_value=Decimal("250.00"))
         ):
        amount = await service.resolve_expected_amount(job, booking=booking, invoice=None)

    assert amount["expected_amount_source"] == "visit_fee_only"
    assert amount["approved_parts_amount"] == "250.00"
    assert amount["expected_amount"] == "350.00"


@pytest.mark.asyncio
async def test_provider_commission_excludes_approved_parts():
    from app.engines.invoice_payment.commission_service import ServiceCommissionService
    from app.engines.invoice_payment.models import ServiceInvoice

    inv = MagicMock(spec=ServiceInvoice)
    inv.id, inv.booking_id, inv.job_id, inv.tenant_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )
    inv.category_id = uuid.uuid4()
    inv.total_amount = Decimal("1200.00")
    db = _db(_result([]))
    svc = ServiceCommissionService()

    with patch.object(svc, "_get_invoice", AsyncMock(return_value=inv)), \
         patch.object(svc, "_uses_home_services_completion_ledger", AsyncMock(return_value=False)), \
         patch.object(svc, "_resolve_rate", AsyncMock(return_value=Decimal("10"))), \
         patch.object(svc, "_log_event", AsyncMock()), \
         patch(
             "app.engines.invoice_payment.commission_service.approved_parts_amount",
             AsyncMock(return_value=Decimal("200.00")),
         ):
        result = await svc.calculate_commission(db, str(inv.id))

    assert result["commission_base_amount"] == "1000.00"
    assert result["commission_amount"] == "100.00"
