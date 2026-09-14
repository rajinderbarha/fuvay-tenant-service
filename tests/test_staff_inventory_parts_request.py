"""Technician part requests come from the provider's inventory and go straight
to the customer.

Before this, the technician typed a free-text part name and price, and the
request sat at `requested` waiting for the provider. The customer was only
messaged if the provider later approved it with a flag the staff app never
set, so a part request never reached the customer's Instagram chat.
"""
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.execution.constants import (
    PARTS_STATUS_CUSTOMER_APPROVAL_PENDING, PARTS_STATUS_REQUESTED,
)
from app.engines.execution.home_service_service import HomeServiceJobExecutionService
from app.engines.execution.models import PartsRequest
from app.exceptions import ServiceOSException


def _first(value):
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    result.scalars.return_value.all.return_value = [value] if value else []
    return result


def _all(rows):
    result = MagicMock()
    result.all.return_value = rows
    result.scalars.return_value.all.return_value = rows
    return result


def _job(staff_id, status="service_started"):
    return MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), assigned_staff_id=staff_id,
                     status=status, customer_id=uuid.uuid4(), booking_id=uuid.uuid4())


def _item(**overrides):
    values = dict(id=uuid.uuid4(), name="AC capacitor 45uF", sku="CAP-45", category="AC",
                  unit="unit", unit_cost=Decimal("300"), selling_price=Decimal("850"),
                  warranty="6 months")
    values.update(overrides)
    return SimpleNamespace(**values)


def _db(*results):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _service():
    svc = HomeServiceJobExecutionService()
    svc._set_status = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_a_part_must_be_picked_from_inventory():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_parts_request(
            _db(_first(job)), job.id, job.tenant_id, staff_id, uuid.uuid4(),
            inventory_item_id=None, quantity=1, reason="Burnt out",
        )
    assert exc.value.error_code == "PARTS_INVENTORY_ITEM_REQUIRED"
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_name_and_price_come_from_the_catalogue_and_the_customer_decides():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    item = _item()
    warehouse, van = uuid.uuid4(), uuid.uuid4()
    stock = _all([(item.id, warehouse, 9, None), (item.id, van, 2, staff_id)])
    db = _db(_first(job), _first(item), stock)
    svc = _service()

    data = await svc.create_parts_request(
        db, job.id, job.tenant_id, staff_id, uuid.uuid4(),
        inventory_item_id=item.id, quantity=2, reason="  Burnt out  ",
    )

    assert data["part_name"] == "AC capacitor 45uF"
    assert data["estimated_cost"] == 850.0
    assert data["unit_price_snapshot"] == 850.0
    assert data["reason"] == "Burnt out"
    assert data["status"] == PARTS_STATUS_CUSTOMER_APPROVAL_PENDING
    assert data["customer_approval_required"] is True
    assert data["business_approval_required"] is False
    assert data["procurement_source"] == "inventory"
    assert data["inventory_item_id"] == str(item.id)
    # The technician's own van holds enough, so it is used before the warehouse.
    assert data["stock_location_id"] == str(van)
    # Stock is held only once the customer approves.
    assert data["stock_reservation_id"] is None
    # Work already started stays started: the pending part blocks finishing
    # work, not the job. quote_required would read as "send an estimate" and
    # offer the technician Start work again.
    svc._set_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_part_found_during_inspection_still_moves_the_job_to_quote_required():
    staff_id = uuid.uuid4()
    job = _job(staff_id, status="inspection_done")
    item = _item()
    stock = _all([(item.id, uuid.uuid4(), 5, None)])
    svc = _service()
    await svc.create_parts_request(
        _db(_first(job), _first(item), stock), job.id, job.tenant_id, staff_id, uuid.uuid4(),
        inventory_item_id=item.id, quantity=1, reason="Needed",
    )
    assert svc._set_status.await_args.args[2] == "quote_required"


@pytest.mark.asyncio
async def test_falls_back_to_the_fullest_location_when_the_van_is_short():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    item = _item()
    small, large, van = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    stock = _all([(item.id, small, 3, None), (item.id, large, 7, None), (item.id, van, 1, staff_id)])
    svc = _service()
    data = await svc.create_parts_request(
        _db(_first(job), _first(item), stock), job.id, job.tenant_id, staff_id, uuid.uuid4(),
        inventory_item_id=item.id, quantity=3, reason="Needed",
    )
    assert data["stock_location_id"] == str(large)


@pytest.mark.asyncio
async def test_a_request_larger_than_any_one_location_is_refused():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    item = _item()
    stock = _all([(item.id, uuid.uuid4(), 2, None), (item.id, uuid.uuid4(), 1, None)])
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_parts_request(
            _db(_first(job), _first(item), stock), job.id, job.tenant_id, staff_id, uuid.uuid4(),
            inventory_item_id=item.id, quantity=3, reason="Needed",
        )
    assert exc.value.error_code == "PARTS_INSUFFICIENT_STOCK"
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_an_archived_or_foreign_item_cannot_be_requested():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_parts_request(
            _db(_first(job), _first(None)), job.id, job.tenant_id, staff_id, uuid.uuid4(),
            inventory_item_id=uuid.uuid4(), quantity=1, reason="Needed",
        )
    assert exc.value.error_code == "PARTS_INVENTORY_ITEM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_catalogue_shows_customer_price_and_stock_but_never_cost():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    in_stock = _item(name="Capacitor")
    empty = _item(name="Blower motor", selling_price=None, unit_cost=Decimal("1200"))
    stock = _all([(in_stock.id, uuid.uuid4(), 4, None), (in_stock.id, uuid.uuid4(), 6, None)])
    db = _db(_first(job), _all([empty, in_stock]), stock)
    svc = _service()

    data = await svc.list_parts_catalog(db, job.id, job.tenant_id, staff_id)

    names = [part["name"] for part in data["items"]]
    assert names == ["Capacitor", "Blower motor"]
    first, second = data["items"]
    assert first["unit_price"] == 850.0
    assert first["available_qty"] == 10
    assert first["max_request_qty"] == 6
    assert second["unit_price"] == 1200.0
    assert second["max_request_qty"] == 0
    for part in data["items"]:
        assert not {"unit_cost", "margin", "inventory_value"} & part.keys()


@pytest.mark.asyncio
async def test_catalogue_is_only_for_the_assigned_technician():
    job = _job(uuid.uuid4())
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_parts_catalog(_db(_first(job)), job.id, job.tenant_id, uuid.uuid4())
    assert exc.value.status_code == 403


def _session_factory(session):
    @asynccontextmanager
    async def _open():
        yield session
    return MagicMock(return_value=_open)


@pytest.mark.asyncio
async def test_customer_is_asked_in_chat_with_the_price_and_approve_decline_taps():
    job = MagicMock(customer_id=uuid.uuid4(), booking_id=uuid.uuid4())
    booking = MagicMock(booking_number="BK-1044", ai_session_id=uuid.uuid4())
    session = MagicMock()
    session.get = AsyncMock(side_effect=[job, booking])
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    part = {
        "parts_request_id": str(uuid.uuid4()), "job_id": str(uuid.uuid4()),
        "part_name": "AC capacitor 45uF", "quantity": 2, "estimated_cost": 850.0,
        "reason": "Burnt out", "status": PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
    }
    notify = AsyncMock(return_value=True)
    with patch("app.database.get_session_factory", _session_factory(session)), \
            patch("app.engines.messaging_gateway.service.notify_customer", notify):
        sent = await HomeServiceJobExecutionService.notify_customer_parts_pending(part)

    assert sent is True
    args, kwargs = notify.await_args
    assert args[1] == job.customer_id
    text = args[2]
    assert "Booking BK-1044" in text
    assert "AC capacitor 45uF × 2 — ₹1,700" in text
    assert "Why: Burnt out" in text
    assert [row["id"] for row in kwargs["rows"]] == [
        f"pt|{part['parts_request_id']}|approve", f"pt|{part['parts_request_id']}|decline",
    ]
    assert kwargs["source_ai_session_id"] == booking.ai_session_id
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_no_message_for_a_part_not_waiting_on_the_customer():
    notify = AsyncMock(return_value=True)
    with patch("app.engines.messaging_gateway.service.notify_customer", notify):
        sent = await HomeServiceJobExecutionService.notify_customer_parts_pending(
            {"parts_request_id": str(uuid.uuid4()), "job_id": str(uuid.uuid4()),
             "status": PARTS_STATUS_REQUESTED})
    assert sent is False
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_chat_failure_never_raises_into_the_request():
    session = MagicMock()
    session.get = AsyncMock(side_effect=RuntimeError("messaging schema missing"))
    session.rollback = AsyncMock()
    part = {"parts_request_id": str(uuid.uuid4()), "job_id": str(uuid.uuid4()),
            "status": PARTS_STATUS_CUSTOMER_APPROVAL_PENDING}
    with patch("app.database.get_session_factory", _session_factory(session)):
        sent = await HomeServiceJobExecutionService.notify_customer_parts_pending(part)
    assert sent is False
    session.rollback.assert_awaited()


def _parts_request(**overrides):
    pr = PartsRequest()
    values = dict(
        id=uuid.uuid4(), job_id=uuid.uuid4(), tenant_id=uuid.uuid4(), technician_id=uuid.uuid4(),
        part_name="AC capacitor 45uF", quantity=1, estimated_cost=Decimal("850"), reason="Needed",
        photo_ids=[], technician_note=None, customer_approval_required=True,
        business_approval_required=False, status=PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
        procurement_source="inventory", inventory_item_id=uuid.uuid4(),
        stock_location_id=uuid.uuid4(), stock_reservation_id=None,
        unit_price_snapshot=Decimal("850"),
    )
    values.update(overrides)
    for key, value in values.items():
        setattr(pr, key, value)
    return pr


@pytest.mark.asyncio
async def test_technician_can_cancel_a_request_nobody_has_decided():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    pr = _parts_request(job_id=job.id, tenant_id=job.tenant_id)
    svc = _service()
    data = await svc.cancel_parts_request(
        _db(_first(job), _first(pr)), job.id, pr.id, job.tenant_id, staff_id, uuid.uuid4(),
    )
    assert data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_a_decided_request_cannot_be_cancelled():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    pr = _parts_request(job_id=job.id, tenant_id=job.tenant_id, status="customer_approved")
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.cancel_parts_request(
            _db(_first(job), _first(pr)), job.id, pr.id, job.tenant_id, staff_id, uuid.uuid4(),
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_a_request_from_another_job_cannot_be_cancelled():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    pr = _parts_request(tenant_id=job.tenant_id)
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.cancel_parts_request(
            _db(_first(job), _first(pr)), job.id, pr.id, job.tenant_id, staff_id, uuid.uuid4(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_work_cannot_be_marked_done_while_a_part_waits_on_the_customer():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    pending = _parts_request(job_id=job.id)
    svc = _service()
    with pytest.raises(ServiceOSException) as exc:
        await svc.mark_work_done(_db(_first(job), _all([pending])), job.id, job.tenant_id, staff_id, uuid.uuid4())
    assert exc.value.error_code == "PARTS_PENDING_BLOCK_WORK_DONE"
    svc._set_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_finishing_work_installs_approved_parts_and_deducts_their_stock():
    staff_id = uuid.uuid4()
    job = _job(staff_id)
    reserved = _parts_request(job_id=job.id, status="customer_approved", stock_reservation_id=uuid.uuid4())
    external = _parts_request(job_id=job.id, status="business_approved", procurement_source="external",
                              inventory_item_id=None, stock_location_id=None)
    legacy = _parts_request(job_id=job.id, status="customer_approved", stock_reservation_id=None)
    svc = _service()
    svc._consume_parts_inventory = AsyncMock()
    db = _db(_first(job), _all([]), _all([reserved, external, legacy]))
    with patch("app.engines.execution.usage_credit_deduction.attempt_charge_at_event", AsyncMock()):
        await svc.mark_work_done(db, job.id, job.tenant_id, staff_id, uuid.uuid4())

    svc._consume_parts_inventory.assert_awaited_once_with(db, reserved)
    assert reserved.status == "installed"
    assert external.status == "installed"
    # No reservation to consume: left for the provider rather than blocking the technician.
    assert legacy.status == "customer_approved"


@pytest.mark.asyncio
async def test_customer_approval_keeps_the_price_they_were_shown():
    pr = PartsRequest()
    for key, value in dict(
        id=uuid.uuid4(), job_id=uuid.uuid4(), tenant_id=uuid.uuid4(), quantity=1,
        procurement_source="inventory", inventory_item_id=uuid.uuid4(),
        stock_location_id=uuid.uuid4(), estimated_cost=Decimal("850"),
        unit_price_snapshot=Decimal("850"),
    ).items():
        setattr(pr, key, value)
    inventory = MagicMock()
    inventory.get_item = AsyncMock(return_value={"selling_price": 999.0})
    inventory.create_reservation = AsyncMock(return_value={"reservation_id": str(uuid.uuid4())})
    with patch("app.engines.inventory.service.InventoryService", return_value=inventory):
        await HomeServiceJobExecutionService()._reserve_parts_inventory(MagicMock(), pr, uuid.uuid4())
    assert pr.estimated_cost == Decimal("850")
    inventory.get_item.assert_not_awaited()
    inventory.create_reservation.assert_awaited_once()
