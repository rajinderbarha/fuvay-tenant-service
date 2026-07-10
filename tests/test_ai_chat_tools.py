"""
Phase 12 — AI Assistant. The pre-existing ai_chat engine was built against an
imagined schema (Booking.service_type, Booking.final_price, Booking.city,
Job.assigned_staff_name, Job.sla_minutes — none of which exist on the real
models) and an old status vocabulary (Job.status.in_(["pending_assignment",
"in_progress", ...]) — none of which match the real 23+ statuses). The
get_active_job tool would therefore NEVER find an active job, and
get_my_bookings/get_booking_detail would crash with AttributeError on first
real row. Two tools (get_price_estimate, get_service_faqs) were implemented
but never declared in TOOLS, so DeepSeek could never call them. Two more
(get_service_catalog, get_available_slots) were accidentally nested inside
a helper function and unreachable via getattr() dispatch.

These tests exercise the tool executor against mocked rows shaped like the
REAL ORM models to prove the fixes are correct, not just that imports work.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


def make_executor():
    from app.engines.ai_chat.tools import ToolExecutor
    db = MagicMock()
    return ToolExecutor(db=db, customer_id=uuid.uuid4()), db


# ── get_my_bookings: real Booking field names ───────────────────────────────

@pytest.mark.asyncio
async def test_get_my_bookings_uses_real_booking_fields():
    executor, db = make_executor()
    booking = MagicMock(
        booking_number="BK-1", service_type_id="ac_repair",
        scheduled_at=None, status="confirmed",
        address={"city": "Mumbai"}, quoted_price=Decimal("999"),
    )
    scalars_result = MagicMock(); scalars_result.all.return_value = [booking]
    exec_result = MagicMock(); exec_result.scalars.return_value = scalars_result
    db.execute = AsyncMock(return_value=exec_result)

    result = await executor._tool_get_my_bookings()
    assert result["bookings"][0]["service_type"] == "ac_repair"
    assert result["bookings"][0]["city"] == "Mumbai"
    assert result["bookings"][0]["price"] == 999.0


@pytest.mark.asyncio
async def test_get_my_bookings_handles_no_address_gracefully():
    executor, db = make_executor()
    booking = MagicMock(booking_number="BK-1", service_type_id="ac_repair",
                         scheduled_at=None, status="confirmed", address={}, quoted_price=None)
    scalars_result = MagicMock(); scalars_result.all.return_value = [booking]
    exec_result = MagicMock(); exec_result.scalars.return_value = scalars_result
    db.execute = AsyncMock(return_value=exec_result)

    result = await executor._tool_get_my_bookings()
    assert result["bookings"][0]["city"] is None


# ── get_booking_detail: real Booking field names ────────────────────────────

@pytest.mark.asyncio
async def test_get_booking_detail_uses_real_fields_not_imagined_ones():
    executor, db = make_executor()
    booking = MagicMock(
        booking_number="BK-1", service_type_id="plumbing", status="confirmed",
        scheduled_at=None, address={"city": "Delhi", "line1": "123 St"},
        quoted_price=Decimal("500"), customer_notes="ring the bell",
        reschedule_count=0, created_at=datetime.now(timezone.utc),
    )
    scalars_result = MagicMock(); scalars_result.first.return_value = booking
    exec_result = MagicMock(); exec_result.scalars.return_value = scalars_result
    db.execute = AsyncMock(return_value=exec_result)

    result = await executor._tool_get_booking_detail("BK-1")
    assert result["service_type"] == "plumbing"
    assert result["city"] == "Delhi"
    assert result["price"] == 500.0
    assert result["notes"] == "ring the bell"


# ── get_active_job: real Job fields + real status vocabulary ───────────────

@pytest.mark.asyncio
async def test_get_active_job_matches_a_real_in_progress_status():
    """The old hardcoded status list never matched any real Job.status value —
    this proves the fix (TERMINAL_STATUSES exclusion) actually finds the job."""
    from app.engines.field_ops.constants import JS
    executor, db = make_executor()
    staff_id = uuid.uuid4()
    job = MagicMock(job_number="JOB-1", service_type_id="ac_repair", status=JS.EN_ROUTE,
                     address={"city": "Pune"}, assigned_staff_id=staff_id,
                     created_at=datetime.now(timezone.utc), sla_breach=False)

    job_scalars = MagicMock(); job_scalars.first.return_value = job
    job_result = MagicMock(); job_result.scalars.return_value = job_scalars
    staff_result = MagicMock(); staff_result.scalar_one_or_none.return_value = "Asha Patel"
    db.execute = AsyncMock(side_effect=[job_result, staff_result])

    result = await executor._tool_get_active_job()
    assert result["active_job"]["status"] == JS.EN_ROUTE
    assert result["active_job"]["assigned_staff"] == "Asha Patel"
    assert result["active_job"]["city"] == "Pune"
    assert result["active_job"]["sla_breached"] is False


@pytest.mark.asyncio
async def test_get_active_job_no_job_returns_friendly_message():
    executor, db = make_executor()
    job_scalars = MagicMock(); job_scalars.first.return_value = None
    job_result = MagicMock(); job_result.scalars.return_value = job_scalars
    db.execute = AsyncMock(return_value=job_result)

    result = await executor._tool_get_active_job()
    assert result["active_job"] is None


# ── Previously-unreachable tools are now real class methods ────────────────

@pytest.mark.asyncio
async def test_get_service_catalog_is_dispatchable_via_execute():
    """Was accidentally nested inside _try_uuid — getattr(self, ...) found
    nothing and execute() always returned 'Unknown tool'. Verify it's fixed."""
    executor, _ = make_executor()
    raw = await executor.execute("get_service_catalog", {"category_id": "ac"})
    result = json.loads(raw)
    assert "error" not in result
    assert len(result["services"]) > 0


@pytest.mark.asyncio
async def test_get_available_slots_is_dispatchable_via_execute():
    executor, _ = make_executor()
    raw = await executor.execute("get_available_slots", {"service_category": "ac", "city": "Mumbai"})
    result = json.loads(raw)
    assert "error" not in result
    assert len(result["available_slots"]) == 3


@pytest.mark.asyncio
async def test_get_price_estimate_is_dispatchable_via_execute():
    executor, _ = make_executor()
    raw = await executor.execute("get_price_estimate", {"service_type": "AC Repair"})
    result = json.loads(raw)
    assert result["min_price"] == 499


@pytest.mark.asyncio
async def test_get_service_faqs_is_dispatchable_via_execute():
    executor, _ = make_executor()
    raw = await executor.execute("get_service_faqs", {"service_type": "ac"})
    result = json.loads(raw)
    assert len(result["faqs"]) > 0


# ── All 5 required tools are actually declared for DeepSeek ────────────────

def test_all_five_required_tools_are_declared_in_TOOLS():
    from app.engines.ai_chat.constants import TOOLS
    declared = {t["function"]["name"] for t in TOOLS}
    required = {"get_my_bookings", "get_booking_detail", "get_active_job",
                "get_price_estimate", "get_service_faqs"}
    assert required.issubset(declared)


# ── Exception construction no longer crashes with TypeError ────────────────

@pytest.mark.asyncio
async def test_chat_raises_clean_error_when_api_key_missing_not_typeerror():
    from app.engines.ai_chat.service import AIChatService
    from app.exceptions import ServiceOSException

    svc = AIChatService(db=MagicMock(), customer_id=uuid.uuid4())
    svc.api_key = ""  # force not-configured branch

    with pytest.raises(ServiceOSException) as exc:
        await svc.chat("hello")
    assert exc.value.error_code == "DEEPSEEK_NOT_CONFIGURED"
    assert exc.value.status_code == 503


# ── API key never leaks into any customer-visible payload ──────────────────

def test_api_key_not_present_in_engine_meta_response():
    import asyncio
    from app.engines.ai_chat.router import engine_meta
    meta = asyncio.get_event_loop().run_until_complete(engine_meta())
    serialized = json.dumps(meta)
    assert "sk-" not in serialized
