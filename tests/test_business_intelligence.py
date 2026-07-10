"""
Phase 13 — Analytics and Business Intelligence.

DSService.get_business_performance() computes 7 metrics via cross-engine
SQLAlchemy queries against Job, JobStatusHistory, Booking, and
StaffPerformanceScore tables. These tests exercise each metric in isolation
using the standard mocked-DB pattern: AsyncMock db.execute() returning
shaped MagicMocks that mirror what SQLAlchemy scalars/rows look like.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock


def make_svc():
    from app.engines.data_science.service import DSService
    db = MagicMock()
    return DSService(db=db), db


def scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def rows_result(rows):
    r = MagicMock()
    r.all.return_value = rows
    return r


# ── 1. Jobs by type ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jobs_by_type_groups_correctly():
    svc, db = make_svc()
    tid = uuid.uuid4()

    row_repair = MagicMock(job_type="repair", cnt=5)
    row_service = MagicMock(job_type="service", cnt=3)
    row_consult = MagicMock(job_type="consultation", cnt=2)

    # The method runs 8 queries; stub them all.
    # Query order in get_business_performance:
    # 1 jobs_by_type, 2 conv_num, 3 conv_den, 4 avg_revenue, 5 total_customers,
    # 6 repeat_customers, 7 qc_jobs, 8 failed_jobs, 9 total_jobs, 10 breach_jobs,
    # 11 staff_rows (returns []), then no name_map query since no staff
    stubs = [
        rows_result([row_repair, row_service, row_consult]),  # 1
        scalar_result(1),   # 2 conv_num
        scalar_result(2),   # 3 conv_den
        rows_result([]),    # 4 avg_revenue
        scalar_result(10),  # 5 total_customers
        scalar_result(3),   # 6 repeat_customers
        scalar_result(4),   # 7 qc_jobs
        scalar_result(1),   # 8 failed_jobs
        scalar_result(10),  # 9 total_jobs
        scalar_result(1),   # 10 breach_jobs
        rows_result([]),    # 11 staff_rows
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid, days=30)
    assert result["jobs_by_type"]["repair"] == 5
    assert result["jobs_by_type"]["service"] == 3
    assert result["jobs_by_type"]["consultation"] == 2


# ── 2. Consultation conversion rate ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_consultation_conversion_rate_50_percent():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),    # jobs_by_type
        scalar_result(1),   # conv_num: 1 consultation spawned a child
        scalar_result(2),   # conv_den: 2 consultations completed quote stage
        rows_result([]),    # avg_revenue
        scalar_result(0),   # total_customers
        scalar_result(0),   # repeat_customers
        scalar_result(0),   # qc_jobs
        scalar_result(0),   # failed_jobs
        scalar_result(0),   # total_jobs
        scalar_result(0),   # breach_jobs
        rows_result([]),    # staff_rows
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["consultation_conversion_rate"] == 0.5


@pytest.mark.asyncio
async def test_consultation_conversion_rate_none_when_no_consultations():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),
        scalar_result(0),   # conv_num
        scalar_result(0),   # conv_den — division by zero must not crash
        rows_result([]),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["consultation_conversion_rate"] is None


# ── 3. Average revenue per job type ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_avg_revenue_by_type_rounded_to_2dp():
    svc, db = make_svc()
    tid = uuid.uuid4()

    rev_row = MagicMock(job_type="repair", avg_rev=Decimal("1234.567"))
    stubs = [
        rows_result([]),            # jobs_by_type
        scalar_result(0),           # conv_num
        scalar_result(0),           # conv_den
        rows_result([rev_row]),     # avg_revenue
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["avg_revenue_by_type"]["repair"] == 1234.57


# ── 4. Repeat booking rate ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repeat_booking_rate_3_of_10():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),
        scalar_result(0), scalar_result(0),
        rows_result([]),
        scalar_result(10),  # total_customers
        scalar_result(3),   # repeat_customers
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["repeat_booking_rate"] == 0.3


@pytest.mark.asyncio
async def test_repeat_booking_rate_none_when_no_bookings():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),
        scalar_result(0), scalar_result(0),
        rows_result([]),
        scalar_result(0),   # total_customers = 0
        scalar_result(0),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["repeat_booking_rate"] is None


# ── 5. Rework / quality failure rate ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_rework_rate_1_in_4_jobs():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),
        scalar_result(0), scalar_result(0),
        rows_result([]),
        scalar_result(0), scalar_result(0),
        scalar_result(4),   # qc_jobs: 4 reached quality check
        scalar_result(1),   # failed_jobs: 1 failed or needed rework
        scalar_result(0), scalar_result(0),
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["rework_quality_failure_rate"] == 0.25


@pytest.mark.asyncio
async def test_rework_rate_none_when_no_jobs_reached_quality_check():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),
        scalar_result(0), scalar_result(0),
        rows_result([]),
        scalar_result(0), scalar_result(0),
        scalar_result(0),   # qc_jobs = 0 — must not crash
        scalar_result(0),
        scalar_result(0), scalar_result(0),
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["rework_quality_failure_rate"] is None


# ── 6. SLA breach rate ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sla_breach_rate_and_count():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [
        rows_result([]),
        scalar_result(0), scalar_result(0),
        rows_result([]),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        scalar_result(20),  # total_jobs
        scalar_result(2),   # breach_jobs
        rows_result([]),
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert result["sla_breaches"] == 2
    assert result["sla_breach_rate"] == 0.1


# ── 7. Staff performance summary ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_performance_includes_name_and_score():
    svc, db = make_svc()
    tid = uuid.uuid4()
    staff_id = uuid.uuid4()

    staff_row = MagicMock(
        staff_id=staff_id, composite_score=Decimal("87.5"), jobs_completed=12,
        avg_customer_rating=Decimal("4.6"), computed_at=datetime.now(timezone.utc),
    )
    name_row = MagicMock(id=staff_id, full_name="Asha Patel")

    stubs = [
        rows_result([]),
        scalar_result(0), scalar_result(0),
        rows_result([]),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        scalar_result(0), scalar_result(0),
        rows_result([staff_row]),       # staff_rows
        rows_result([name_row]),        # name_map lookup
    ]
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid)
    assert len(result["top_staff"]) == 1
    staff = result["top_staff"][0]
    assert staff["name"] == "Asha Patel"
    assert staff["score"] == 87.5
    assert staff["jobs_completed"] == 12
    assert staff["avg_rating"] == 4.6


# ── 8. Response shape completeness ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_response_contains_all_required_keys():
    svc, db = make_svc()
    tid = uuid.uuid4()

    stubs = [rows_result([])] + [scalar_result(0)] * 8 + [rows_result([])] * 2
    db.execute = AsyncMock(side_effect=stubs)

    result = await svc.get_business_performance(tid, days=7)
    expected_keys = {
        "period_days", "jobs_by_type", "consultation_conversion_rate",
        "avg_revenue_by_type", "repeat_booking_rate", "rework_quality_failure_rate",
        "sla_breach_rate", "total_jobs", "sla_breaches", "top_staff", "generated_at",
    }
    assert expected_keys.issubset(result.keys())
    assert result["period_days"] == 7
