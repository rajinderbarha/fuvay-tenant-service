"""Regression coverage for social complaints, SLA closure, health, and badges."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.models import CustomerComplaint
from app.engines.messaging_gateway import flow
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM,
    CMD_COMPLAINT,
    DURABLE_ACTION_PICKS,
    KNOWN_COMMANDS,
    PICK_COMPLAINT,
)


ROOT = Path(__file__).resolve().parents[1]


def _booking() -> dict:
    return {
        "record_type": "service_job",
        "record_id": str(uuid.uuid4()),
        "booking_id": str(uuid.uuid4()),
        "booking_number": "BK-20260913-000001",
        "category_id": str(uuid.uuid4()),
        "offering_id": str(uuid.uuid4()),
        "service": "AC repair",
        "problem": "AC not cooling",
    }


class FakeComplaintIdentity:
    def __init__(self):
        self.booking = _booking()
        self.state = None

    async def complaint_cases(self, _thread):
        return []

    async def complaint_bookings(self, _thread):
        return [self.booking]

    async def begin_social_complaint(self, _thread, booking, complaint_type=None):
        self.state = {"mode": "new", **booking}
        if complaint_type:
            self.state["complaint_type"] = complaint_type
        return self.state

    async def social_complaint_state(self, _thread):
        return self.state


def test_complaint_is_a_known_durable_social_action():
    assert CMD_COMPLAINT in KNOWN_COMMANDS
    assert PICK_COMPLAINT in DURABLE_ACTION_PICKS


@pytest.mark.asyncio
async def test_instagram_complaint_selects_booking_then_type_then_description():
    identity = FakeComplaintIdentity()
    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())

    choose_type = await flow._complaint_step(
        thread, identity, "new", CHANNEL_INSTAGRAM,
    )
    assert choose_type.picker
    ids = [row["id"] for row in choose_type.picker["rows"]]
    assert "cmp|type|service_quality" in ids
    assert identity.state["booking_number"] == "BK-20260913-000001"

    describe = await flow._complaint_step(
        thread, identity, "type|service_quality", CHANNEL_INSTAGRAM,
    )
    assert describe.picker is None
    assert "next message" in describe.text.lower()
    assert identity.state["complaint_type"] == "service_quality"


@pytest.mark.asyncio
async def test_instagram_case_renders_resolution_accept_and_reject_actions():
    identity = FakeComplaintIdentity()
    complaint_id = str(uuid.uuid4())
    resolution_id = str(uuid.uuid4())
    identity.complaint_status_view = AsyncMock(return_value={
        "id": complaint_id,
        "number": "CMP-12345678",
        "type": "service_quality",
        "status": "resolution_proposed",
        "description": "Cooling stopped again after the visit.",
        "sla_status": "on_time",
        "resolution": {
            "id": resolution_id,
            "type": "rework",
            "description": "A technician will revisit at no labour charge.",
            "notes": None,
        },
    })
    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())

    turn = await flow._complaint_step(
        thread, identity, f"case|{complaint_id}", CHANNEL_INSTAGRAM,
    )
    ids = [row["id"] for row in turn.picker["rows"]]
    assert f"cmp|accept|{complaint_id}|{resolution_id}" in ids
    assert f"cmp|reject|{complaint_id}|{resolution_id}" in ids
    assert "PROPOSED RESOLUTION" in turn.text


@pytest.mark.asyncio
async def test_first_response_sla_never_reopens_after_provider_response():
    complaint = CustomerComplaint(
        customer_id=uuid.uuid4(), category_id=uuid.uuid4(),
        record_type="service_job", record_id=uuid.uuid4(),
        complaint_type="service_quality", description="test complaint",
        status="open", sla_status="on_time",
        tenant_first_response_due_at=datetime.now(timezone.utc) - timedelta(days=2),
        provider_responded_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db = AsyncMock()
    result = await ComplaintService().check_and_update_sla(db, complaint)
    assert result.sla_status == "on_time"
    db.flush.assert_not_awaited()


def test_sla_worker_filters_answered_complaints_and_dashboard_returns_badges():
    worker = (ROOT / "app/jobs/complaint_sla.py").read_text(encoding="utf-8")
    dashboard = (ROOT / "app/engines/execution/home_services_dashboard_service.py").read_text(encoding="utf-8")
    provider_page = (ROOT / "frontend/tenant-portal/app/(tenant)/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "CustomerComplaint.provider_responded_at.is_(None)" in worker
    assert '"badges": public_badges' in dashboard
    assert "<TrustBadges badges={data.provider_health.badges}" in provider_page


def test_only_unresolved_complaints_feed_quality_rate():
    single = (ROOT / "app/engines/trust_quality/service.py").read_text(encoding="utf-8")
    batch = (ROOT / "app/engines/trust_quality/recalculation.py").read_text(encoding="utf-8")
    operational = (ROOT / "app/engines/tenant_engine/health.py").read_text(encoding="utf-8")
    for source in (single, batch, operational):
        assert "'resolved','closed','cancelled','rejected','settled'" in source
    assert 'write_health_signal(\n                tenant_id, "customer_satisfaction"' in operational


def test_active_home_service_records_are_complaint_eligible():
    """Late arrival and no-show must be reportable before job completion."""
    from app.engines.complaints.constants import (
        ELIGIBLE_STATUSES, RECORD_SERVICE_BOOKING, RECORD_SERVICE_JOB,
    )

    for status in ("pending_assignment", "assigned", "scheduled", "on_the_way"):
        assert status in ELIGIBLE_STATUSES[RECORD_SERVICE_BOOKING]
        assert status in ELIGIBLE_STATUSES[RECORD_SERVICE_JOB]
    for status in ("reached_site", "inspection_started", "service_started", "work_done"):
        assert status in ELIGIBLE_STATUSES[RECORD_SERVICE_JOB]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("record_type", "status"),
    (("service_booking", "assigned"), ("service_job", "on_the_way")),
)
async def test_active_home_service_complaint_passes_canonical_eligibility(record_type, status):
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    service = ComplaintEligibilityService()
    service._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status=status, customer_id=customer_id, created_at=datetime.now(timezone.utc),
    ))
    service._customer_owns_record = AsyncMock(return_value=True)
    service.get_complaint_policy = AsyncMock(return_value=None)
    service.check_duplicate_open_complaint = AsyncMock(return_value=False)

    result = await service.check_eligible(
        AsyncMock(), customer_id, record_type, uuid.uuid4(),
        complaint_type="late_arrival",
    )
    assert result["eligible"] is True
