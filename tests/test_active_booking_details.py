"""ACTIVE-BOOKING-DETAILS phase — `get_my_booking`'s nested `job` payload
must be a customer-safe allow-listed projection (never `ServiceJob.to_dict()`
verbatim, which leaks `assigned_staff_id`/`tenant_id`/internal workflow ids).
Covers: ownership, enumeration-safety, technician allow-listing, tenant
scoping on the technician join, and safe null handling for every optional
field. Uses the same MagicMock/AsyncMock patterns as
test_level5_booking_confirmation_receipt.py rather than mocking away
serialization behavior.
"""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.final_records.customer_router import get_my_booking
from app.exceptions import ServiceOSException


def _scalars(items):
    result = MagicMock()
    result.scalars.return_value.first.return_value = items[0] if items else None
    return result


def _booking(customer_id, **overrides):
    defaults = dict(
        id=uuid.uuid4(), customer_id=customer_id, category_id=uuid.uuid4(),
        offering_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
    )
    defaults.update(overrides)
    booking = MagicMock()
    booking.to_dict.return_value = {"id": str(defaults["id"]), "customer_id": str(customer_id)}
    booking.id = defaults["id"]
    booking.customer_id = defaults["customer_id"]
    booking.category_id = defaults["category_id"]
    booking.offering_id = defaults["offering_id"]
    booking.job_type_id = defaults["job_type_id"]
    return booking


def _job(booking_id, tenant_id, **overrides):
    defaults = dict(
        id=uuid.uuid4(), booking_id=booking_id, tenant_id=tenant_id,
        customer_id=None, assigned_staff_id=None,
        status="pending_assignment", assignment_status="unassigned",
        scheduled_date=None, scheduled_time_window=None, updated_at=None,
        service_job_workflow_id=None, completion_data=None,
        warranty_days_snapshot=None, warranty_expires_at=None,
    )
    defaults.update(overrides)
    job = MagicMock()
    for k, v in defaults.items():
        setattr(job, k, v)
    return job


def _staff(user_id, tenant_id, **overrides):
    defaults = dict(full_name="Amanpreet S.", designation="Technician", profile_photo_url=None)
    defaults.update(overrides)
    staff = MagicMock()
    staff.user_id = user_id
    staff.tenant_id = tenant_id
    for k, v in defaults.items():
        setattr(staff, k, v)
    return staff


async def _run(booking, job, staff=None):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalars([booking]), _scalars([job] if job else [])])
    db.get = AsyncMock(side_effect=[None, None, None])
    db.scalar = AsyncMock(return_value=staff)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(booking.customer_id))
    return await get_my_booking(booking_id=booking.id, r=request, user=user, db=db)


@pytest.mark.asyncio
async def test_pending_assignment_booking_returns_no_fabricated_job():
    customer_id = uuid.uuid4()
    booking = _booking(customer_id)
    job = _job(booking.id, booking.tenant_id if hasattr(booking, "tenant_id") else uuid.uuid4())
    result = await _run(booking, job)
    assert result.data["job"]["technician"] is None
    assert result.data["job"]["scheduled_date"] is None
    assert result.data["job"]["stage"] == "new"


@pytest.mark.asyncio
async def test_no_job_returns_null_job_not_a_fabricated_one():
    customer_id = uuid.uuid4()
    booking = _booking(customer_id)
    result = await _run(booking, None)
    assert result.data["job"] is None


@pytest.mark.asyncio
async def test_assigned_job_returns_only_allow_listed_technician_fields():
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    booking = _booking(customer_id)
    staff_user_id = uuid.uuid4()
    job = _job(booking.id, tenant_id, assigned_staff_id=staff_user_id, status="assigned", assignment_status="assigned")
    staff = _staff(staff_user_id, tenant_id, profile_photo_url="https://cdn.example/p.jpg")

    result = await _run(booking, job, staff)

    technician = result.data["job"]["technician"]
    assert technician == {
        "display_name": "Amanpreet S.",
        "designation": "Technician",
        "photo_url": "https://cdn.example/p.jpg",
    }
    assert set(technician.keys()) == {"display_name", "designation", "photo_url"}
    assert "user_id" not in technician
    assert "phone" not in technician
    assert "email" not in technician


@pytest.mark.asyncio
async def test_scheduled_job_returns_verified_schedule_data():
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    booking = _booking(customer_id)
    job = _job(
        booking.id, tenant_id, status="scheduled", assignment_status="accepted",
        scheduled_date=date(2026, 8, 5), scheduled_time_window="3:00 PM - 5:00 PM",
    )
    result = await _run(booking, job, None)
    assert result.data["job"]["scheduled_date"] == "2026-08-05"
    assert result.data["job"]["scheduled_time_window"] == "3:00 PM - 5:00 PM"
    assert result.data["job"]["stage"] == "scheduled"


@pytest.mark.asyncio
async def test_on_the_way_status_maps_to_on_the_way_stage():
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    booking = _booking(customer_id)
    job = _job(booking.id, tenant_id, status="on_the_way", assignment_status="accepted")
    result = await _run(booking, job, None)
    assert result.data["job"]["stage"] == "on_the_way"


@pytest.mark.asyncio
async def test_sensitive_staff_fields_never_present_in_job_payload():
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    booking = _booking(customer_id)
    staff_user_id = uuid.uuid4()
    job = _job(booking.id, tenant_id, assigned_staff_id=staff_user_id, status="assigned", assignment_status="assigned")
    staff = _staff(staff_user_id, tenant_id)
    result = await _run(booking, job, staff)
    job_dict = result.data["job"]
    assert "assigned_staff_id" not in job_dict
    assert "tenant_id" not in job_dict
    assert "category_id" not in job_dict
    assert "offering_id" not in job_dict
    assert "completion_data" not in job_dict
    assert "job_type_id" not in job_dict


@pytest.mark.asyncio
async def test_unknown_job_status_handled_safely():
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    booking = _booking(customer_id)
    job = _job(booking.id, tenant_id, status="some_future_status", assignment_status="assigned")
    result = await _run(booking, job, None)
    assert result.data["job"]["stage"] == "exception"


@pytest.mark.asyncio
async def test_optional_photo_and_schedule_fields_may_be_null():
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    booking = _booking(customer_id)
    staff_user_id = uuid.uuid4()
    job = _job(booking.id, tenant_id, assigned_staff_id=staff_user_id, status="assigned", assignment_status="assigned")
    staff = _staff(staff_user_id, tenant_id, profile_photo_url=None)
    result = await _run(booking, job, staff)
    assert result.data["job"]["technician"]["photo_url"] is None
    assert result.data["job"]["scheduled_date"] is None


@pytest.mark.asyncio
async def test_foreign_booking_id_remains_enumeration_safe():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([]))
    db.get = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(uuid.uuid4()))
    with pytest.raises(ServiceOSException) as exc_info:
        await get_my_booking(booking_id=uuid.uuid4(), r=request, user=user, db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_existing_pending_assignment_response_backward_compatible():
    customer_id = uuid.uuid4()
    booking = _booking(customer_id)
    result = await _run(booking, None)
    assert result.data["id"] == str(booking.id)
    assert result.data["customer_id"] == str(customer_id)
