"""Sprint 21 — Execution lifecycle tests.

Covers:
- Constants / transition rules
- HomeServiceJobExecutionService (15 methods)
- CoachingAppointmentExecutionService (9 methods)
- RealEstateLeadExecutionService (12 methods)
- Swagger route registration (12 routers × N endpoints)
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import ServiceOSException

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

TENANT_ID = uuid.uuid4()
USER_ID   = uuid.uuid4()
STAFF_ID  = uuid.uuid4()
AGENT_ID  = uuid.uuid4()
JOB_ID    = uuid.uuid4()
BOOKING_ID = uuid.uuid4()
APPT_ID   = uuid.uuid4()
LEAD_ID   = uuid.uuid4()


def _mock_job(status="assigned", assigned_staff_id=None):
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id              = JOB_ID
    j.booking_id      = BOOKING_ID
    j.tenant_id       = TENANT_ID
    j.status          = status
    j.assignment_status = "assigned"
    j.assigned_staff_id = assigned_staff_id or STAFF_ID
    j.failure_reason  = None
    j.updated_at      = None
    j.to_dict         = lambda: {"id": str(JOB_ID), "status": j.status}
    return j


def _mock_appt(status="confirmed", staff_member_id=None):
    from app.engines.final_records.models import CoachingAppointment
    a = MagicMock(spec=CoachingAppointment)
    a.id             = APPT_ID
    a.tenant_id      = TENANT_ID
    a.staff_member_id = staff_member_id or STAFF_ID
    a.status         = status
    a.failure_reason = None
    a.updated_at     = None
    a.to_dict        = lambda: {"id": str(APPT_ID), "status": a.status}
    return a


def _mock_lead(status="new", agent_id=None):
    from app.engines.final_records.models import RealEstateLead
    l = MagicMock(spec=RealEstateLead)
    l.id             = LEAD_ID
    l.tenant_id      = TENANT_ID
    l.agent_id       = agent_id or AGENT_ID
    l.status         = status
    l.failure_reason = None
    l.updated_at     = None
    l.to_dict        = lambda: {"id": str(LEAD_ID), "status": l.status}
    return l


def _db_returning(*objs):
    """Build an AsyncMock db where each execute call returns the next obj (or None)."""
    db = AsyncMock()
    db.flush   = AsyncMock()
    db.commit  = AsyncMock()
    db.add     = MagicMock()
    side_effects = []
    for obj in objs:
        res = MagicMock()
        res.scalars.return_value.first.return_value = obj
        side_effects.append(res)
    db.execute = AsyncMock(side_effect=side_effects)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_job_transitions_assigned_to_accepted(self):
        from app.engines.execution.constants import JOB_TRANSITIONS, JS_ASSIGNED, JS_ACCEPTED
        assert JS_ACCEPTED in JOB_TRANSITIONS[JS_ASSIGNED]

    def test_job_transitions_work_done_only_allows_completion(self):
        # HS8B fix: work_done was terminal pre-HS8B (completion via a
        # single validated /complete action didn't exist yet — Sprint 23's
        # comment said "terminal — Sprint 23 handles completion"). Now
        # that HS8B implements it, work_done's only allowed transition is
        # to the new `completed` status, exclusively via complete_job().
        from app.engines.execution.constants import JOB_TRANSITIONS, JS_WORK_DONE
        assert JOB_TRANSITIONS[JS_WORK_DONE] == {"completed"}

    def test_appt_transitions_confirmed_to_accepted(self):
        from app.engines.execution.constants import APPT_TRANSITIONS, AS_CONFIRMED, AS_ACCEPTED
        assert AS_ACCEPTED in APPT_TRANSITIONS[AS_CONFIRMED]

    def test_lead_transitions_new_to_accepted(self):
        from app.engines.execution.constants import LEAD_TRANSITIONS, LS_NEW, LS_ACCEPTED
        assert LS_ACCEPTED in LEAD_TRANSITIONS[LS_NEW]

    def test_lead_transitions_converted_is_terminal(self):
        from app.engines.execution.constants import LEAD_TRANSITIONS, LS_CONVERTED
        assert len(LEAD_TRANSITIONS[LS_CONVERTED]) == 0

    def test_error_codes_defined(self):
        from app.engines.execution.constants import (
            ERR_RECORD_NOT_FOUND, ERR_ACCESS_DENIED, ERR_INVALID_TRANSITION,
            ERR_REASON_REQUIRED, ERR_STAFF_NOT_ASSIGNED,
        )
        assert ERR_RECORD_NOT_FOUND.startswith("EXECUTION_")
        assert ERR_INVALID_TRANSITION.startswith("EXECUTION_")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Models
# ─────────────────────────────────────────────────────────────────────────────

class TestModels:
    def test_service_job_execution_event_to_dict(self):
        from app.engines.execution.models import ServiceJobExecutionEvent
        ev = MagicMock(spec=ServiceJobExecutionEvent)
        ev.id = uuid.uuid4(); ev.job_id = JOB_ID
        ev.event_type = "job_accepted"; ev.old_status = "assigned"
        ev.new_status = "accepted"; ev.notes = None; ev.actor_role = "staff"
        ev.created_at = None
        ev.to_dict = ServiceJobExecutionEvent.to_dict.__get__(ev)
        d = ev.to_dict()
        assert d["event_type"] == "job_accepted"
        assert d["new_status"] == "accepted"

    def test_coaching_appointment_execution_event_to_dict(self):
        from app.engines.execution.models import CoachingAppointmentExecutionEvent
        ev = MagicMock(spec=CoachingAppointmentExecutionEvent)
        ev.id = uuid.uuid4(); ev.appointment_id = APPT_ID
        ev.event_type = "appointment_accepted"; ev.old_status = "confirmed"
        ev.new_status = "accepted"; ev.notes = None; ev.actor_role = "staff"
        ev.created_at = None
        ev.to_dict = CoachingAppointmentExecutionEvent.to_dict.__get__(ev)
        d = ev.to_dict()
        assert d["event_type"] == "appointment_accepted"

    def test_real_estate_lead_execution_event_to_dict(self):
        from app.engines.execution.models import RealEstateLeadExecutionEvent
        ev = MagicMock(spec=RealEstateLeadExecutionEvent)
        ev.id = uuid.uuid4(); ev.lead_id = LEAD_ID
        ev.event_type = "lead_accepted"; ev.old_status = "new"
        ev.new_status = "accepted"; ev.notes = None; ev.actor_role = "agent"
        ev.created_at = None
        ev.to_dict = RealEstateLeadExecutionEvent.to_dict.__get__(ev)
        d = ev.to_dict()
        assert d["event_type"] == "lead_accepted"

    def test_service_job_note_to_dict(self):
        from app.engines.execution.models import ServiceJobExecutionNote
        n = MagicMock(spec=ServiceJobExecutionNote)
        n.id = uuid.uuid4(); n.job_id = JOB_ID; n.note_type = "diagnosis"
        n.note_text = "compressor broken"; n.is_customer_visible = True
        n.created_at = None
        n.to_dict = ServiceJobExecutionNote.to_dict.__get__(n)
        d = n.to_dict()
        assert d["note_type"] == "diagnosis"
        assert d["is_customer_visible"] is True

    def test_service_job_media_to_dict(self):
        from app.engines.execution.models import ServiceJobMediaUpload
        m = MagicMock(spec=ServiceJobMediaUpload)
        m.id = uuid.uuid4(); m.job_id = JOB_ID; m.media_type = "before_photo"
        m.file_url = "https://cdn.example.com/img.jpg"; m.file_name = "img.jpg"
        m.caption = None; m.is_customer_visible = False; m.created_at = None
        m.to_dict = ServiceJobMediaUpload.to_dict.__get__(m)
        d = m.to_dict()
        assert d["media_type"] == "before_photo"


# ─────────────────────────────────────────────────────────────────────────────
# 3. HomeServiceJobExecutionService
# ─────────────────────────────────────────────────────────────────────────────

class TestHomeServiceExecution:
    @pytest.fixture
    def svc(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        return HomeServiceJobExecutionService()

    async def test_accept_job_happy_path(self, svc):
        job = _mock_job(status="assigned")
        booking_res = MagicMock(); booking_res.scalars.return_value.first.return_value = None
        db = _db_returning(job, None)
        result = await svc.accept_job(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "accepted"

    async def test_accept_job_invalid_transition(self, svc):
        # HS8 fix: _assert_transition now raises ServiceOSException (caught
        # by the app's global RFC 7807 handler) instead of a bare
        # ValueError, which no router handler ever caught — every invalid
        # transition surfaced as a raw 500 instead of a clean 422.
        job = _mock_job(status="work_done")
        db = _db_returning(job)
        with pytest.raises(ServiceOSException) as exc:
            await svc.accept_job(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert "INVALID_STATUS_TRANSITION" in exc.value.error_code

    async def test_accept_job_wrong_staff(self, svc):
        job = _mock_job(status="assigned", assigned_staff_id=uuid.uuid4())  # different staff
        db = _db_returning(job)
        with pytest.raises(ServiceOSException) as exc:
            await svc.accept_job(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert "STAFF_NOT_ASSIGNED" in exc.value.error_code

    async def test_reject_job_requires_reason(self, svc):
        job = _mock_job(status="assigned")
        db = _db_returning(job)
        with pytest.raises(ServiceOSException) as exc:
            await svc.reject_job(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID, reason="")
        assert "REASON_REQUIRED" in exc.value.error_code

    async def test_reject_job_happy(self, svc):
        job = _mock_job(status="assigned")
        db = _db_returning(job, None)
        await svc.reject_job(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID, reason="Not available")
        assert job.failure_reason == "Not available"

    async def test_mark_on_the_way(self, svc):
        job = _mock_job(status="scheduled")
        db = _db_returning(job, None)
        result = await svc.mark_on_the_way(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "on_the_way"

    async def test_mark_reached_site(self, svc):
        job = _mock_job(status="on_the_way")
        db = _db_returning(job, None)
        await svc.mark_reached_site(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "reached_site"

    async def test_start_inspection(self, svc):
        job = _mock_job(status="reached_site")
        db = _db_returning(job, None)
        await svc.start_inspection(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "inspection_started"

    async def test_complete_inspection(self, svc):
        job = _mock_job(status="inspection_started")
        db = _db_returning(job, None)
        await svc.complete_inspection(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "inspection_done"

    async def test_start_service(self, svc):
        job = _mock_job(status="inspection_done")
        db = _db_returning(job, None)
        await svc.start_service(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "service_started"

    async def test_work_done(self, svc):
        job = _mock_job(status="service_started")
        db = _db_returning(job, None)
        await svc.mark_work_done(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "work_done"

    async def test_quote_required(self, svc):
        job = _mock_job(status="inspection_done")
        db = _db_returning(job, None)
        await svc.mark_quote_required(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "quote_required"

    async def test_cancel_requires_reason(self, svc):
        job = _mock_job(status="accepted")
        db = _db_returning(job)
        with pytest.raises(ServiceOSException):
            await svc.cancel_job(db, JOB_ID, TENANT_ID, USER_ID, reason="")

    async def test_cancel_job(self, svc):
        job = _mock_job(status="accepted")
        db = _db_returning(job, None)
        await svc.cancel_job(db, JOB_ID, TENANT_ID, USER_ID, reason="Customer cancelled")
        assert job.status == "cancelled"

    async def test_add_work_note(self, svc):
        job = _mock_job(status="service_started")
        db = _db_returning(job)
        note = await svc.add_work_note(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID, "Cleaned filters")
        assert db.add.called

    async def test_upload_media(self, svc):
        job = _mock_job(status="reached_site")
        db = _db_returning(job)
        media = await svc.upload_job_media(
            db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID,
            media_type="before_photo", file_url="https://cdn.example.com/img.jpg",
        )
        assert db.add.called

    async def test_get_timeline_returns_list(self, svc):
        db = AsyncMock()
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=res)
        result = await svc.get_job_timeline(db, JOB_ID, TENANT_ID)
        assert result == []

    async def test_job_not_found(self, svc):
        db = _db_returning(None)
        with pytest.raises(ServiceOSException) as exc:
            await svc.accept_job(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert "NOT_FOUND" in exc.value.error_code


# ─────────────────────────────────────────────────────────────────────────────
# 4. CoachingAppointmentExecutionService
# ─────────────────────────────────────────────────────────────────────────────

class TestCoachingExecution:
    @pytest.fixture
    def svc(self):
        from app.engines.execution.coaching_service import CoachingAppointmentExecutionService
        return CoachingAppointmentExecutionService()

    async def test_accept_happy(self, svc):
        appt = _mock_appt(status="confirmed")
        db = _db_returning(appt)
        await svc.accept_appointment(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert appt.status == "accepted"

    async def test_reject_requires_reason(self, svc):
        appt = _mock_appt(status="confirmed")
        db = _db_returning(appt)
        with pytest.raises(ValueError):
            await svc.reject_appointment(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID, reason="")

    async def test_reject_happy(self, svc):
        appt = _mock_appt(status="confirmed")
        db = _db_returning(appt)
        await svc.reject_appointment(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID, reason="Not free")
        assert appt.status == "rejected"

    async def test_start_appointment(self, svc):
        appt = _mock_appt(status="accepted")
        db = _db_returning(appt)
        await svc.start_appointment(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert appt.status == "started"

    async def test_complete_appointment(self, svc):
        appt = _mock_appt(status="started")
        db = _db_returning(appt)
        await svc.complete_appointment(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert appt.status == "completed"

    async def test_no_show(self, svc):
        appt = _mock_appt(status="started")
        db = _db_returning(appt)
        await svc.mark_no_show(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert appt.status == "no_show"

    async def test_reschedule_request(self, svc):
        appt = _mock_appt(status="accepted")
        db = _db_returning(appt)
        await svc.request_reschedule(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert appt.status == "reschedule_requested"

    async def test_cancel_happy(self, svc):
        appt = _mock_appt(status="accepted")
        db = _db_returning(appt)
        await svc.cancel_appointment(db, APPT_ID, TENANT_ID, USER_ID, reason="Emergency")
        assert appt.status == "cancelled"

    async def test_add_note(self, svc):
        appt = _mock_appt(status="started")
        db = _db_returning(appt)
        await svc.add_note(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID, "Student needs extra practice")
        assert db.add.called

    async def test_get_timeline_empty(self, svc):
        db = AsyncMock()
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=res)
        result = await svc.get_timeline(db, APPT_ID, TENANT_ID)
        assert result == []

    async def test_wrong_staff(self, svc):
        appt = _mock_appt(status="confirmed", staff_member_id=uuid.uuid4())
        db = _db_returning(appt)
        with pytest.raises(ValueError) as exc:
            await svc.accept_appointment(db, APPT_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert "STAFF_NOT_ASSIGNED" in str(exc.value)


# ─────────────────────────────────────────────────────────────────────────────
# 5. RealEstateLeadExecutionService
# ─────────────────────────────────────────────────────────────────────────────

class TestRealEstateExecution:
    @pytest.fixture
    def svc(self):
        from app.engines.execution.real_estate_service import RealEstateLeadExecutionService
        return RealEstateLeadExecutionService()

    async def test_accept_lead(self, svc):
        lead = _mock_lead(status="new")
        db = _db_returning(lead)
        await svc.accept_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "accepted"

    async def test_reject_requires_reason(self, svc):
        lead = _mock_lead(status="new")
        db = _db_returning(lead)
        with pytest.raises(ValueError):
            await svc.reject_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID, reason="")

    async def test_reject_lead(self, svc):
        lead = _mock_lead(status="new")
        db = _db_returning(lead)
        await svc.reject_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID, reason="Out of area")
        assert lead.status == "rejected"

    async def test_mark_contacted(self, svc):
        lead = _mock_lead(status="accepted")
        db = _db_returning(lead)
        await svc.mark_contacted(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "contacted"

    async def test_schedule_follow_up(self, svc):
        lead = _mock_lead(status="contacted")
        db = _db_returning(lead)
        await svc.schedule_follow_up(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "follow_up"

    async def test_plan_site_visit(self, svc):
        lead = _mock_lead(status="contacted")
        db = _db_returning(lead)
        await svc.plan_site_visit(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "site_visit_planned"

    async def test_complete_site_visit(self, svc):
        lead = _mock_lead(status="site_visit_planned")
        db = _db_returning(lead)
        await svc.complete_site_visit(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "site_visit_completed"

    async def test_qualify_lead(self, svc):
        lead = _mock_lead(status="contacted")
        db = _db_returning(lead)
        await svc.qualify_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "qualified"

    async def test_disqualify_requires_reason(self, svc):
        lead = _mock_lead(status="contacted")
        db = _db_returning(lead)
        with pytest.raises(ValueError):
            await svc.disqualify_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID, reason="")

    async def test_convert_lead(self, svc):
        lead = _mock_lead(status="qualified")
        db = _db_returning(lead)
        await svc.convert_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert lead.status == "converted"

    async def test_close_lost(self, svc):
        lead = _mock_lead(status="contacted")
        db = _db_returning(lead)
        await svc.close_lost(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID, reason="Budget issue")
        assert lead.status == "closed_lost"

    async def test_wrong_agent(self, svc):
        lead = _mock_lead(status="new", agent_id=uuid.uuid4())
        db = _db_returning(lead)
        with pytest.raises(ValueError) as exc:
            await svc.accept_lead(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID)
        assert "STAFF_NOT_ASSIGNED" in str(exc.value)

    async def test_add_note(self, svc):
        lead = _mock_lead(status="contacted")
        db = _db_returning(lead)
        await svc.add_note(db, LEAD_ID, TENANT_ID, AGENT_ID, USER_ID, "Very interested in 3BHK")
        assert db.add.called

    async def test_get_timeline(self, svc):
        db = AsyncMock()
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=res)
        result = await svc.get_timeline(db, LEAD_ID)
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# 6. Swagger / router registration
# ─────────────────────────────────────────────────────────────────────────────

class TestSwaggerRoutes:
    @pytest.fixture(scope="class")
    def routes(self):
        import json
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        return set(resp.json()["paths"].keys())

    def test_staff_hs_accept_registered(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/accept" in routes

    def test_staff_hs_reject_registered(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/reject" in routes

    def test_staff_hs_on_the_way_registered(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/on-the-way" in routes

    def test_staff_hs_reached_site(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/reached-site" in routes

    def test_staff_hs_work_done(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/work-done" in routes

    def test_staff_hs_notes(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/notes" in routes

    def test_staff_hs_media(self, routes):
        assert "/v1/staff/service-jobs/{job_id}/media" in routes

    def test_provider_hs_cancel(self, routes):
        assert "/v1/provider/service-jobs/{job_id}/cancel" in routes

    def test_customer_hs_tracking(self, routes):
        assert "/v1/customer/service-jobs/{job_id}/tracking" in routes

    def test_admin_hs_timeline(self, routes):
        assert "/v1/admin/service-jobs/{job_id}/execution-timeline" in routes

    def test_staff_coaching_accept(self, routes):
        assert "/v1/staff/coaching-appointments/{appointment_id}/accept" in routes

    def test_staff_coaching_complete(self, routes):
        assert "/v1/staff/coaching-appointments/{appointment_id}/complete" in routes

    def test_customer_coaching_tracking(self, routes):
        assert "/v1/customer/coaching-appointments/{appointment_id}/tracking" in routes

    def test_admin_coaching_timeline(self, routes):
        assert "/v1/admin/coaching-appointments/{appointment_id}/execution-timeline" in routes

    def test_agent_re_accept(self, routes):
        assert "/v1/staff/real-estate-leads/{lead_id}/accept" in routes

    def test_agent_re_convert(self, routes):
        assert "/v1/staff/real-estate-leads/{lead_id}/convert" in routes

    def test_customer_re_tracking(self, routes):
        assert "/v1/customer/real-estate-leads/{lead_id}/tracking" in routes

    def test_admin_re_timeline(self, routes):
        assert "/v1/admin/real-estate-leads/{lead_id}/execution-timeline" in routes
