from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.engines.final_records.operations_service import DRAFT_OPERATIONAL_REQUEST_STATUSES
from app.engines.home_service_booking.demand_signal_service import (
    normalize_zipcode,
    record_unserved_area_demand,
)


def test_only_customer_review_ready_drafts_are_operational_requests():
    assert DRAFT_OPERATIONAL_REQUEST_STATUSES == {"ready_for_confirmation"}


def test_zipcode_normalization_does_not_capture_customer_details():
    assert normalize_zipcode(" 140 412 ") == "140412"
    assert normalize_zipcode(None) is None


@pytest.mark.asyncio
async def test_unserved_search_uses_atomic_daily_upsert():
    db = AsyncMock()
    saved = await record_unserved_area_demand(
        db,
        zipcode="140 999",
        channel="instagram",
        category_key="air-conditioning",
        service_key="ac-repair",
    )

    assert saved is True
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_hs_area_demand_daily_dimension" in sql
    assert "check_count" in sql
    # The compact API deliberately has no identity/contact/address inputs.
    assert "customer" not in statement.compile().params
    assert "phone" not in statement.compile().params


@pytest.mark.asyncio
async def test_invalid_zipcode_is_not_written():
    db = AsyncMock()
    assert await record_unserved_area_demand(
        db, zipcode="", channel="customer_app",
    ) is False
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeat_actor_check_is_deduplicated_without_database_write(monkeypatch):
    redis = AsyncMock()
    redis.set.return_value = False
    monkeypatch.setattr("app.redis_client.get_redis", lambda: redis)
    db = AsyncMock()

    saved = await record_unserved_area_demand(
        db,
        zipcode="140412",
        channel="whatsapp",
        category_key="ac",
        dedupe_token="conversation-123",
    )

    assert saved is False
    redis.set.assert_awaited_once()
    db.execute.assert_not_awaited()
