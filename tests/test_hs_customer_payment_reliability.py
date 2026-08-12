import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.invoice_payment.models import ServicePaymentRecord
from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.engines.tenant_engine.hs_customer_directory_service import (
    HomeServicesCustomerDirectoryService,
    _payment_reliability_status,
)


@pytest.mark.parametrize(
    ("decisions", "review", "expected"),
    [
        (0, 0, "insufficient_data"),
        (2, 1, "insufficient_data"),
        (3, 0, "reliable"),
        (3, 1, "needs_review"),
        (100, 1, "needs_review"),
    ],
)
def test_payment_reliability_policy(decisions, review, expected):
    assert _payment_reliability_status(decisions, review) == expected


@pytest.mark.asyncio
async def test_payment_reliability_uses_one_grouped_query():
    customer_id = uuid.uuid4()
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = [(customer_id, 4, 1)]
    db.execute.return_value = result

    data = await HomeServicesCustomerDirectoryService(db)._payment_reliability_by_customer(
        [customer_id], tenant_id=uuid.uuid4(),
    )

    assert data[customer_id] == {
        "status": "needs_review",
        "decided_records": 4,
        "review_records": 1,
    }
    db.execute.assert_awaited_once()


def test_payment_reliability_lookup_indexes_are_declared():
    index_names = {index.name for index in ServicePaymentRecord.__table__.indexes}
    assert "ix_spr_customer_reconciliation" in index_names
    assert "ix_spr_tenant_customer_reconciliation" in index_names


def test_customer_directory_history_indexes_are_declared():
    booking_indexes = {index.name for index in ServiceBooking.__table__.indexes}
    job_indexes = {index.name for index in ServiceJob.__table__.indexes}
    assert "ix_sb_customer_created" in booking_indexes
    assert "ix_sb_tenant_customer_created" in booking_indexes
    assert "ix_sj_customer_status_updated" in job_indexes
    assert "ix_sj_tenant_customer_status_updated" in job_indexes


@pytest.mark.asyncio
async def test_customer_aggregates_consume_one_row_per_customer_not_one_row_per_job():
    customer_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    booking_result = MagicMock()
    booking_result.all.return_value = [(customer_id, now)]
    job_result = MagicMock()
    # One PostgreSQL aggregate row represents an arbitrary amount of history.
    job_result.all.return_value = [(customer_id, 250_000, 17, now, 8, 3)]
    db = AsyncMock()
    db.execute.side_effect = [booking_result, job_result]

    data = await HomeServicesCustomerDirectoryService(db)._customer_aggregates()

    assert data[customer_id]["completed_jobs"] == 250_000
    assert data[customer_id]["cancelled_jobs"] == 17
    assert data[customer_id]["services_used_count"] == 8
    assert data[customer_id]["providers_used_count"] == 3
    assert data[customer_id]["multi_service"] is True
    assert data[customer_id]["multi_provider"] is True
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_admin_customer_list_paginates_in_sql_without_materializing_every_customer():
    customer_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    count_result = MagicMock()
    count_result.scalar.return_value = 1_000_000
    page_result = MagicMock()
    page_result.mappings.return_value.all.return_value = [{
        "customer_id": customer_id,
        "first_booking_at": now,
        "completed_jobs": 4,
        "cancelled_jobs": 1,
        "last_job_at": now,
        "last_activity_at": now,
        "services_used_count": 2,
        "providers_used_count": 2,
        "open_complaints": 0,
        "decided_records": 3,
        "review_records": 0,
        "name": "Scale Customer",
        "email": "scale@example.com",
        "phone": None,
    }]
    db = AsyncMock()
    db.execute.side_effect = [count_result, page_result]
    service = HomeServicesCustomerDirectoryService(db)
    service._customer_aggregates = AsyncMock(side_effect=AssertionError("must stay in SQL"))

    result = await service.list_customers(page=50_000, page_size=20)

    assert result["total"] == 1_000_000
    assert len(result["items"]) == 1
    assert result["items"][0]["payment_reliability"] == "reliable"
    assert service._customer_aggregates.await_count == 0
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_customer_summary_aggregates_counts_inside_sql():
    stats_result = MagicMock()
    stats_result.mappings.return_value.one.return_value = {
        "total": 1_000_000, "active": 800_000, "new": 20_000,
        "repeat": 600_000, "one_time": 250_000, "with_completed": 850_000,
        "multi_service": 400_000, "multi_provider": 125_000,
        "avg_completed": 3.5,
    }
    complaint_result = MagicMock(); complaint_result.scalar.return_value = 2_000
    invoice_result = MagicMock(); invoice_result.scalar.return_value = 123456
    payment_result = MagicMock(); payment_result.scalar.return_value = 750
    db = AsyncMock()
    db.execute.side_effect = [stats_result, complaint_result, invoice_result, payment_result]
    service = HomeServicesCustomerDirectoryService(db)
    service._customer_aggregates = AsyncMock(side_effect=AssertionError("must stay in SQL"))

    result = await service.get_summary()

    assert result["total_customers"] == 1_000_000
    assert result["inactive_customers"] == 200_000
    assert result["payment_review"] == 750
    assert result["returning_rate"] == 70.6
    assert service._customer_aggregates.await_count == 0
    assert db.execute.await_count == 4
