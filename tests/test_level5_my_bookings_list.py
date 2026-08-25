"""MY-BOOKINGS-ROOT-TAB (2026-08-01) — `list_my_bookings` now batch-
enriches each page with real offering/category/job-type NAMES (one query
per catalog type across the whole page), matching `get_my_booking`'s
per-item enrichment without the N+1 query cost on a page of up to 100
bookings.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.final_records.customer_router import list_my_bookings


def _booking(customer_id, **overrides):
    defaults = dict(
        id=uuid.uuid4(), customer_id=customer_id, offering_id=uuid.uuid4(),
        category_id=uuid.uuid4(), job_type_id=uuid.uuid4(), status="pending_assignment",
    )
    defaults.update(overrides)
    booking = MagicMock()
    for k, v in defaults.items():
        setattr(booking, k, v)
    booking.to_dict.return_value = {"id": str(defaults["id"]), "status": defaults["status"]}
    return booking


def _rows(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _pairs(pairs):
    result = MagicMock()
    result.all.return_value = pairs
    return result


@pytest.mark.asyncio
async def test_list_my_bookings_batch_enriches_names_with_one_query_per_catalog_type():
    customer_id = uuid.uuid4()
    b1 = _booking(customer_id)
    b2 = _booking(customer_id)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        _rows([b1, b2]),  # main booking query
        _pairs([(b1.offering_id, "AC Repair"), (b2.offering_id, "Geyser Repair")]),
        _pairs([(b1.category_id, "AC & Cooling"), (b2.category_id, "Water Heating")]),
        _pairs([(b1.job_type_id, "Repair"), (b2.job_type_id, "Repair")]),
        _pairs([]),  # one batched committed-slot/urgency lookup
    ])
    db.scalar = AsyncMock(return_value=2)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(customer_id))

    result = await list_my_bookings(r=request, status=None, limit=20, offset=0, user=user, db=db)

    names = {item["id"]: item.get("offering_name") for item in result.data["items"]}
    assert names[str(b1.id)] == "AC Repair"
    assert names[str(b2.id)] == "Geyser Repair"
    assert db.execute.call_count == 5  # main + 3 catalog + 1 urgency batch, never N+1


@pytest.mark.asyncio
async def test_list_my_bookings_skips_catalog_queries_when_the_page_is_empty():
    customer_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_rows([]))
    db.scalar = AsyncMock(return_value=0)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(customer_id))

    result = await list_my_bookings(r=request, status=None, limit=20, offset=0, user=user, db=db)

    assert result.data["items"] == []
    assert db.execute.call_count == 1
