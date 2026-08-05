"""BOOKING-CONFIRMATION-RECEIPT (2026-08-01) — `get_my_booking` now
enriches the response with offering_name/category_name/job_type_label
(previously only foreign-key ids), needed for the customer-app receipt to
show a real service name without a second round-trip. Best-effort: a
missing catalog row must never break the response.
"""
import uuid
from types import SimpleNamespace
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
        id=uuid.uuid4(), booking_number="SB-2026-01", draft_id=uuid.uuid4(),
        customer_id=customer_id, tenant_id=uuid.uuid4(),
        category_id=uuid.uuid4(), offering_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
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


@pytest.mark.asyncio
async def test_get_my_booking_enriches_offering_category_job_type_names():
    customer_id = uuid.uuid4()
    booking = _booking(customer_id)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalars([booking]), _scalars([])])  # booking, then no job
    db.get = AsyncMock(side_effect=[
        SimpleNamespace(service_name="AC Repair"),      # MasterService
        SimpleNamespace(name="AC & Cooling"),            # ServiceCategory
        SimpleNamespace(label="Repair"),                 # JobTypeDefinition
    ])
    request = MagicMock()
    request.state.request_id = "req-1"
    user = SimpleNamespace(user_id=str(customer_id))

    result = await get_my_booking(booking_id=booking.id, r=request, user=user, db=db)

    assert result.data["offering_name"] == "AC Repair"
    assert result.data["category_name"] == "AC & Cooling"
    assert result.data["job_type_label"] == "Repair"


@pytest.mark.asyncio
async def test_get_my_booking_enrichment_is_best_effort_when_catalog_row_missing():
    customer_id = uuid.uuid4()
    booking = _booking(customer_id, job_type_id=None)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalars([booking]), _scalars([])])
    db.get = AsyncMock(side_effect=[None, None])  # offering/category rows deleted
    request = MagicMock()
    request.state.request_id = "req-1"
    user = SimpleNamespace(user_id=str(customer_id))

    result = await get_my_booking(booking_id=booking.id, r=request, user=user, db=db)

    assert "offering_name" not in result.data
    assert "category_name" not in result.data
    assert "job_type_label" not in result.data


@pytest.mark.asyncio
async def test_get_my_booking_returns_404_without_querying_catalog():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([]))
    db.get = AsyncMock()
    request = MagicMock()
    request.state.request_id = "req-1"
    user = SimpleNamespace(user_id=str(uuid.uuid4()))

    with pytest.raises(ServiceOSException) as exc_info:
        await get_my_booking(booking_id=uuid.uuid4(), r=request, user=user, db=db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "BOOKING_NOT_FOUND"
    db.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_my_booking_denies_access_for_a_different_customer_with_the_identical_not_found_response():
    """SECURITY: a different customer's booking must be indistinguishable
    from a genuinely nonexistent one -- same status, same error_code, same
    message -- so probing booking IDs cannot reveal whether one exists."""
    other_customer_id = uuid.uuid4()
    booking = _booking(other_customer_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    db.get = AsyncMock()
    request = MagicMock()
    request.state.request_id = "req-1"
    user = SimpleNamespace(user_id=str(uuid.uuid4()))

    with pytest.raises(ServiceOSException) as exc_info:
        await get_my_booking(booking_id=booking.id, r=request, user=user, db=db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "BOOKING_NOT_FOUND"
    assert exc_info.value.detail == "Booking not found"
    db.get.assert_not_called()
    db.get.assert_not_called()
