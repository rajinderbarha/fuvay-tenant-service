"""Sprint 19 — Booking Confirmation → Final Record Creation tests.

Tests FinalCreationService (home_service, coaching, real_estate),
number generation, idempotency, constants, models, and API routers.

No real DB, no HTTP — all mocked.
asyncio_mode = 'auto' via pyproject.toml.
"""
import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Phase 2A.2: finalize() now independently revalidates Job Type/Blueprint
# context via HomeServiceChatbotBookingService._validate_job_type_context.
# This entire test module predates that concept -- its mocked drafts don't
# set up the catalog queries that check would need, and its own purpose is
# proving Booking/Job record CREATION shape, not job-type validation
# (covered by tests/test_module_l5_54_customer_job_type_contract.py).
# Short-circuit it to "valid" for every test in this module.
@pytest.fixture(autouse=True)
def _bypass_job_type_context_validation():
    with patch(
        "app.engines.home_service_booking.service.HomeServiceChatbotBookingService._validate_job_type_context",
        AsyncMock(return_value=None),
    ):
        yield

from app.engines.final_records.constants import (
    DRAFT_TYPE_HOME_SERVICE, DRAFT_TYPE_COACHING, DRAFT_TYPE_REAL_ESTATE,
    VALID_DRAFT_TYPES,
    RESULT_TYPE_SERVICE_BOOKING, RESULT_TYPE_COACHING_APPOINTMENT,
    RESULT_TYPE_REAL_ESTATE_LEAD,
    CONFIRM_STATUS_CREATED, CONFIRM_STATUS_FAILED,
    BOOKING_STATUS_PENDING_ASSIGNMENT,
    JOB_STATUS_PENDING_ASSIGNMENT,
    APPT_STATUS_CONFIRMED,
    LEAD_STATUS_NEW,
    AUDIT_BOOKING_CREATED, AUDIT_APPOINTMENT_CREATED, AUDIT_LEAD_CREATED,
    AUDIT_CONFIRMATION_DUPLICATE,
    NUMBER_PREFIX_BOOKING, NUMBER_PREFIX_JOB,
    NUMBER_PREFIX_APPOINTMENT, NUMBER_PREFIX_LEAD,
    ERR_DRAFT_NOT_FOUND, ERR_DRAFT_NOT_READY, ERR_ACCESS_DENIED,
    ERR_DUPLICATE_CONFIRMATION,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestSprint19Constants:
    def test_draft_types_all_present(self):
        assert DRAFT_TYPE_HOME_SERVICE in VALID_DRAFT_TYPES
        assert DRAFT_TYPE_COACHING in VALID_DRAFT_TYPES
        assert DRAFT_TYPE_REAL_ESTATE in VALID_DRAFT_TYPES

    def test_result_types(self):
        assert RESULT_TYPE_SERVICE_BOOKING     == "service_booking"
        assert RESULT_TYPE_COACHING_APPOINTMENT == "coaching_appointment"
        assert RESULT_TYPE_REAL_ESTATE_LEAD     == "real_estate_lead"

    def test_number_prefixes(self):
        assert NUMBER_PREFIX_BOOKING     == "BK"
        assert NUMBER_PREFIX_JOB         == "JOB"
        assert NUMBER_PREFIX_APPOINTMENT == "APPT"
        assert NUMBER_PREFIX_LEAD        == "LEAD"

    def test_statuses(self):
        assert BOOKING_STATUS_PENDING_ASSIGNMENT == "pending_assignment"
        assert JOB_STATUS_PENDING_ASSIGNMENT     == "pending_assignment"
        assert APPT_STATUS_CONFIRMED             == "confirmed"
        assert LEAD_STATUS_NEW                   == "new"

    def test_confirmation_statuses(self):
        assert CONFIRM_STATUS_CREATED == "created"
        assert CONFIRM_STATUS_FAILED  == "failed"

    def test_audit_actions(self):
        assert AUDIT_BOOKING_CREATED        == "booking_created"
        assert AUDIT_APPOINTMENT_CREATED    == "appointment_created"
        assert AUDIT_LEAD_CREATED           == "lead_created"
        assert AUDIT_CONFIRMATION_DUPLICATE == "confirmation_duplicate"

    def test_error_codes_present(self):
        assert ERR_DRAFT_NOT_FOUND  is not None
        assert ERR_DRAFT_NOT_READY  is not None
        assert ERR_ACCESS_DENIED    is not None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Number Format
# ─────────────────────────────────────────────────────────────────────────────

class TestNumberFormat:
    def test_booking_number_format(self):
        from app.engines.final_records.number_service import _format_number, NUMBER_PREFIX_BOOKING
        num = _format_number("BK", "20260702", 1)
        assert num == "BK-20260702-000001"

    def test_job_number_format(self):
        from app.engines.final_records.number_service import _format_number
        num = _format_number("JOB", "20260702", 42)
        assert num == "JOB-20260702-000042"

    def test_appointment_number_format(self):
        from app.engines.final_records.number_service import _format_number
        num = _format_number("APPT", "20260702", 100)
        assert num == "APPT-20260702-000100"

    def test_lead_number_format(self):
        from app.engines.final_records.number_service import _format_number
        num = _format_number("LEAD", "20260702", 999999)
        assert num == "LEAD-20260702-999999"

    def test_today_str_format(self):
        from app.engines.final_records.number_service import _today_str
        s = _today_str()
        assert len(s) == 8
        assert s.isdigit()

    @pytest.mark.asyncio
    async def test_generate_booking_number_queries_db(self):
        from app.engines.final_records.number_service import generate_booking_number
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))
        num = await generate_booking_number(db)
        assert num.startswith("BK-")
        assert num.endswith("-000001")

    @pytest.mark.asyncio
    async def test_generate_booking_number_increments(self):
        from app.engines.final_records.number_service import generate_booking_number
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=5)))
        num = await generate_booking_number(db)
        assert num.endswith("-000006")

    @pytest.mark.asyncio
    async def test_generate_lead_number(self):
        from app.engines.final_records.number_service import generate_lead_number
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))
        num = await generate_lead_number(db)
        assert num.startswith("LEAD-")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Models
# ─────────────────────────────────────────────────────────────────────────────

class TestFinalRecordModels:
    def test_service_booking_to_dict(self):
        from app.engines.final_records.models import ServiceBooking
        b = ServiceBooking()
        b.id             = uuid.uuid4()
        b.booking_number = "BK-20260702-000001"
        b.draft_id       = uuid.uuid4()
        b.customer_id    = uuid.uuid4()
        b.tenant_id      = uuid.uuid4()
        b.category_id    = uuid.uuid4()
        b.offering_id    = uuid.uuid4()
        b.status         = "pending_assignment"
        b.created_at     = None
        b.updated_at     = None
        d = b.to_dict()
        assert d["booking_number"] == "BK-20260702-000001"
        assert d["status"] == "pending_assignment"

    def test_service_job_to_dict(self):
        from app.engines.final_records.models import ServiceJob
        j = ServiceJob()
        j.id         = uuid.uuid4()
        j.job_number = "JOB-20260702-000001"
        j.booking_id = uuid.uuid4()
        j.category_id = uuid.uuid4()
        j.offering_id = uuid.uuid4()
        j.status     = "pending_assignment"
        j.created_at = None
        j.updated_at = None
        d = j.to_dict()
        assert d["job_number"] == "JOB-20260702-000001"

    def test_coaching_appointment_to_dict(self):
        from app.engines.final_records.models import CoachingAppointment
        a = CoachingAppointment()
        a.id                 = uuid.uuid4()
        a.appointment_number = "APPT-20260702-000001"
        a.draft_id           = uuid.uuid4()
        a.category_id        = uuid.uuid4()
        a.offering_id        = uuid.uuid4()
        a.status             = "confirmed"
        a.created_at         = None
        a.updated_at         = None
        d = a.to_dict()
        assert d["appointment_number"] == "APPT-20260702-000001"
        assert d["status"] == "confirmed"

    def test_real_estate_lead_to_dict(self):
        from app.engines.final_records.models import RealEstateLead
        l = RealEstateLead()
        l.id          = uuid.uuid4()
        l.lead_number = "LEAD-20260702-000001"
        l.draft_id    = uuid.uuid4()
        l.category_id = uuid.uuid4()
        l.offering_id = uuid.uuid4()
        l.status      = "new"
        l.budget_min  = None
        l.budget_max  = None
        l.rent_min    = None
        l.rent_max    = None
        l.created_at  = None
        l.updated_at  = None
        d = l.to_dict()
        assert d["lead_number"] == "LEAD-20260702-000001"
        assert d["status"] == "new"

    def test_customer_booking_confirmation_to_dict(self):
        from app.engines.final_records.models import CustomerBookingConfirmation
        c = CustomerBookingConfirmation()
        c.id            = uuid.uuid4()
        c.draft_type    = "home_service"
        c.draft_id      = uuid.uuid4()
        c.result_type   = "service_booking"
        c.result_id     = uuid.uuid4()
        c.result_number = "BK-20260702-000001"
        c.status        = "created"
        c.created_at    = None
        d = c.to_dict()
        assert d["draft_type"]    == "home_service"
        assert d["result_number"] == "BK-20260702-000001"

    def test_final_creation_audit_log_to_dict(self):
        from app.engines.final_records.models import FinalCreationAuditLog
        l = FinalCreationAuditLog()
        l.id         = uuid.uuid4()
        l.action     = "booking_created"
        l.draft_type = "home_service"
        l.created_at = None
        d = l.to_dict()
        assert d["action"]     == "booking_created"
        assert d["draft_type"] == "home_service"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Idempotency
# ─────────────────────────────────────────────────────────────────────────────

class TestConfirmationLockService:
    @pytest.mark.asyncio
    async def test_get_existing_returns_none_when_no_record(self):
        from app.engines.final_records.idempotency import ConfirmationLockService
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        svc = ConfirmationLockService(db)
        result = await svc.get_existing("home_service", uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_existing_returns_record_when_found(self):
        from app.engines.final_records.idempotency import ConfirmationLockService
        from app.engines.final_records.models import CustomerBookingConfirmation
        existing = MagicMock(spec=CustomerBookingConfirmation)
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing
        db.execute = AsyncMock(return_value=mock_result)
        svc = ConfirmationLockService(db)
        result = await svc.get_existing("home_service", uuid.uuid4())
        assert result is existing

    @pytest.mark.asyncio
    async def test_check_and_raise_delegates_to_get_existing(self):
        from app.engines.final_records.idempotency import ConfirmationLockService
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        svc = ConfirmationLockService(db)
        result = await svc.check_and_raise_if_duplicate("home_service", uuid.uuid4())
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. HomeService FinalCreationService
# ─────────────────────────────────────────────────────────────────────────────

def _make_hs_draft():
    from app.engines.home_service_booking.models import HomeServiceBookingDraft
    d = MagicMock(spec=HomeServiceBookingDraft)
    d.id                     = uuid.uuid4()
    d.customer_id            = uuid.uuid4()
    d.selected_tenant_id     = uuid.uuid4()
    d.category_id            = uuid.uuid4()
    d.offering_id            = uuid.uuid4()
    d.ai_session_id          = None
    d.customer_name          = "Alice"
    d.customer_phone         = "0500000001"
    d.city                   = "Dubai"
    d.zipcode                = "00000"
    d.address_snapshot       = {}
    d.preferred_date         = date(2026, 7, 10)
    d.preferred_time_window  = "morning"
    d.price_snapshot         = {"price": 100}
    d.selected_provider_snapshot = {}
    d.issue_summary          = "AC broken"
    d.issue_details          = {}
    d.status                 = "ready_for_confirmation"
    return d


class TestHomeServiceFinalCreation:
    @pytest.mark.asyncio
    async def test_finalize_creates_booking_and_job(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        draft = _make_hs_draft()
        db = AsyncMock()

        # Mock draft fetch (lock is replaced, so only 1 execute call)
        draft_result = MagicMock()
        draft_result.scalars.return_value.first.return_value = draft

        db.execute = AsyncMock(return_value=draft_result)
        db.flush   = AsyncMock()
        db.refresh = AsyncMock()

        # Mock number generation
        with patch("app.engines.final_records.creation_service.generate_booking_number",
                   new=AsyncMock(return_value="BK-20260702-000001")), \
             patch("app.engines.final_records.creation_service.generate_job_number",
                   new=AsyncMock(return_value="JOB-20260702-000001")), \
             patch.object(db, "add"):

            # Mock lock creation
            lock_svc = AsyncMock()
            mock_confirm = MagicMock(id=uuid.uuid4())
            lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
            lock_svc.create_lock = AsyncMock(return_value=mock_confirm)

            svc      = HomeServiceFinalCreationService(db=db)
            svc.lock = lock_svc

            result = await svc.finalize(draft.id, customer_id=draft.customer_id)

        assert result["booking_number"] == "BK-20260702-000001"
        assert result["job_number"]     == "JOB-20260702-000001"
        assert result["idempotent"]     is False

    @pytest.mark.asyncio
    async def test_finalize_returns_existing_on_duplicate(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.final_records.models import CustomerBookingConfirmation
        draft_id = uuid.uuid4()
        db = AsyncMock()

        existing = MagicMock(spec=CustomerBookingConfirmation)
        existing.result_number = "BK-20260702-000001"
        existing.result_id     = uuid.uuid4()
        existing.id            = uuid.uuid4()

        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=existing)
        lock_svc.create_lock = AsyncMock()
        db.add   = MagicMock()
        db.flush = AsyncMock()

        svc      = HomeServiceFinalCreationService(db=db)
        svc.lock = lock_svc

        result = await svc.finalize(draft_id)
        assert result["idempotent"]    is True
        assert result["booking_number"] == "BK-20260702-000001"
        lock_svc.create_lock.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalize_raises_on_draft_not_found(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.final_records.constants import ERR_DRAFT_NOT_FOUND
        db = AsyncMock()
        mock_res = MagicMock(); mock_res.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=mock_res)
        db.flush   = AsyncMock()

        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)

        svc      = HomeServiceFinalCreationService(db=db)
        svc.lock = lock_svc

        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_FOUND):
            await svc.finalize(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_finalize_raises_on_wrong_status(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.final_records.constants import ERR_DRAFT_NOT_READY
        draft = _make_hs_draft()
        draft.status = "collecting_details"  # wrong status
        db = AsyncMock()
        draft_res = MagicMock(); draft_res.scalars.return_value.first.return_value = draft
        db.execute = AsyncMock(return_value=draft_res)
        db.flush   = AsyncMock()

        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)

        svc      = HomeServiceFinalCreationService(db=db)
        svc.lock = lock_svc

        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_READY):
            await svc.finalize(draft.id)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Coaching FinalCreationService
# ─────────────────────────────────────────────────────────────────────────────

def _make_coaching_draft():
    from app.engines.coaching_appointment.models import CoachingAppointmentDraft
    d = MagicMock(spec=CoachingAppointmentDraft)
    d.id                      = uuid.uuid4()
    d.customer_id             = uuid.uuid4()
    d.selected_tenant_id      = uuid.uuid4()
    d.category_id             = uuid.uuid4()
    d.offering_id             = uuid.uuid4()
    d.ai_session_id           = None
    d.selected_staff_member_id = None
    d.student_name            = "Bob"
    d.student_phone           = "0500000002"
    d.student_email           = "bob@example.com"
    d.target_exam             = "IELTS"
    d.target_band             = "7.5"
    d.preferred_mode          = "online"
    d.selected_date           = date(2026, 7, 15)
    d.selected_time_start     = time(10, 0)
    d.selected_time_end       = time(11, 0)
    d.city                    = "Dubai"
    d.appointment_fee_snapshot = {"fee": 200}
    d.selected_provider_snapshot = {}
    d.status                  = "ready_for_confirmation"
    return d


def _make_slot_hold(draft_id, tz_aware=True):
    """Create a mock CoachingAppointmentSlotHold that is valid (held, not expired)."""
    from datetime import datetime, timezone, timedelta
    from app.engines.coaching_appointment.models import CoachingAppointmentSlotHold
    h = MagicMock(spec=CoachingAppointmentSlotHold)
    h.id            = uuid.uuid4()
    h.draft_id      = draft_id
    h.tenant_id     = uuid.uuid4()
    h.offering_id   = uuid.uuid4()
    h.hold_status   = "held"
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    h.expires_at    = future if tz_aware else future.replace(tzinfo=None)
    return h


def _db_with_draft_and_hold(draft, hold):
    """Build a mock DB where first execute returns draft, second returns hold."""
    db = AsyncMock()
    db.flush   = AsyncMock()
    db.refresh = AsyncMock()
    db.add     = MagicMock()
    draft_res = MagicMock(); draft_res.scalars.return_value.first.return_value = draft
    hold_res  = MagicMock(); hold_res.scalars.return_value.first.return_value  = hold
    db.execute = AsyncMock(side_effect=[draft_res, hold_res])
    return db


class TestCoachingFinalCreation:
    @pytest.mark.asyncio
    async def test_finalize_creates_appointment(self):
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        draft = _make_coaching_draft()
        hold  = _make_slot_hold(draft.id)
        db    = _db_with_draft_and_hold(draft, hold)

        lock_svc = AsyncMock()
        mock_confirm = MagicMock(id=uuid.uuid4())
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        lock_svc.create_lock = AsyncMock(return_value=mock_confirm)

        with patch("app.engines.final_records.creation_service.generate_appointment_number",
                   new=AsyncMock(return_value="APPT-20260702-000001")):
            svc      = CoachingFinalCreationService(db=db)
            svc.lock = lock_svc
            result   = await svc.finalize(draft.id, customer_id=draft.customer_id)

        assert result["appointment_number"]   == "APPT-20260702-000001"
        assert result["idempotent"]           is False
        assert result["slot_hold_converted"]  is True

    @pytest.mark.asyncio
    async def test_slot_hold_status_becomes_converted(self):
        """After finalize, hold.hold_status must be 'converted'."""
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        draft = _make_coaching_draft()
        hold  = _make_slot_hold(draft.id)
        db    = _db_with_draft_and_hold(draft, hold)

        lock_svc = AsyncMock()
        mock_confirm = MagicMock(id=uuid.uuid4())
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        lock_svc.create_lock = AsyncMock(return_value=mock_confirm)

        with patch("app.engines.final_records.creation_service.generate_appointment_number",
                   new=AsyncMock(return_value="APPT-20260702-000001")):
            svc      = CoachingFinalCreationService(db=db)
            svc.lock = lock_svc
            await svc.finalize(draft.id, customer_id=draft.customer_id)

        assert hold.hold_status == "converted"

    @pytest.mark.asyncio
    async def test_finalize_blocks_when_slot_hold_missing(self):
        """Confirmation fails with ERR_SLOT_HOLD_MISSING if no hold exists for draft."""
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        from app.engines.final_records.constants import ERR_SLOT_HOLD_MISSING
        draft = _make_coaching_draft()
        db    = _db_with_draft_and_hold(draft, None)  # hold = None

        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc      = CoachingFinalCreationService(db=db)
        svc.lock = lock_svc

        with pytest.raises(ValueError, match=ERR_SLOT_HOLD_MISSING):
            await svc.finalize(draft.id)

    @pytest.mark.asyncio
    async def test_finalize_blocks_when_slot_hold_expired(self):
        """Confirmation fails with ERR_SLOT_HOLD_EXPIRED if hold is past expires_at."""
        from datetime import datetime, timezone, timedelta
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        from app.engines.final_records.constants import ERR_SLOT_HOLD_EXPIRED
        draft = _make_coaching_draft()
        hold  = _make_slot_hold(draft.id)
        hold.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)  # expired
        db    = _db_with_draft_and_hold(draft, hold)

        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc      = CoachingFinalCreationService(db=db)
        svc.lock = lock_svc

        with pytest.raises(ValueError, match=ERR_SLOT_HOLD_EXPIRED):
            await svc.finalize(draft.id)

    @pytest.mark.asyncio
    async def test_finalize_blocks_when_slot_hold_already_converted(self):
        """Confirmation fails with ERR_SLOT_HOLD_ALREADY_CONVERTED if hold was already used."""
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        from app.engines.final_records.constants import ERR_SLOT_HOLD_ALREADY_CONVERTED
        draft = _make_coaching_draft()
        hold  = _make_slot_hold(draft.id)
        hold.hold_status = "converted"  # already converted
        db    = _db_with_draft_and_hold(draft, hold)

        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc      = CoachingFinalCreationService(db=db)
        svc.lock = lock_svc

        with pytest.raises(ValueError, match=ERR_SLOT_HOLD_ALREADY_CONVERTED):
            await svc.finalize(draft.id)

    @pytest.mark.asyncio
    async def test_finalize_is_idempotent_on_duplicate(self):
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        from app.engines.final_records.models import CustomerBookingConfirmation
        db = AsyncMock()
        db.add   = MagicMock()
        db.flush = AsyncMock()
        existing = MagicMock(spec=CustomerBookingConfirmation)
        existing.result_number = "APPT-20260702-000001"
        existing.result_id     = uuid.uuid4()
        existing.id            = uuid.uuid4()
        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=existing)
        svc      = CoachingFinalCreationService(db=db)
        svc.lock = lock_svc
        result   = await svc.finalize(uuid.uuid4())
        assert result["idempotent"]         is True
        assert result["appointment_number"] == "APPT-20260702-000001"


# ─────────────────────────────────────────────────────────────────────────────
# 7. RealEstate FinalCreationService
# ─────────────────────────────────────────────────────────────────────────────

def _make_re_draft():
    from app.engines.real_estate_lead.models import RealEstateLeadDraft
    d = MagicMock(spec=RealEstateLeadDraft)
    d.id                       = uuid.uuid4()
    d.customer_id              = uuid.uuid4()
    d.selected_tenant_id       = uuid.uuid4()
    d.selected_agent_id        = None
    d.category_id              = uuid.uuid4()
    d.offering_id              = uuid.uuid4()
    d.ai_session_id            = None
    d.lead_intent              = "buy"
    d.property_type            = "flat"
    d.city                     = "Dubai"
    d.locality                 = "Marina"
    d.zipcode                  = "00000"
    d.budget_min               = Decimal("500000")
    d.budget_max               = Decimal("1000000")
    d.rent_min                 = None
    d.rent_max                 = None
    d.customer_name            = "Carol"
    d.customer_phone           = "0500000003"
    d.customer_email           = "carol@example.com"
    d.preferred_contact_time   = "evening"
    d.requirement_snapshot     = {"bedrooms": 2}
    d.lead_summary             = None
    d.lead_score_snapshot      = None
    d.selected_provider_snapshot = {}
    d.fallback_payload         = None
    d.status                   = "ready_for_confirmation"
    return d


class TestRealEstateFinalCreation:
    @pytest.mark.asyncio
    async def test_finalize_creates_lead(self):
        from app.engines.final_records.creation_service import RealEstateFinalCreationService
        draft = _make_re_draft()
        db    = AsyncMock()

        # First execute: idempotency check via lock (no existing)
        # Second execute: draft load
        # Third execute: lead_score lookup
        no_existing = MagicMock(); no_existing.scalars.return_value.first.return_value = None
        draft_res   = MagicMock(); draft_res.scalars.return_value.first.return_value = draft
        score_res   = MagicMock(); score_res.scalars.return_value.first.return_value = None

        db.execute = AsyncMock(side_effect=[draft_res, score_res])
        db.flush   = AsyncMock()
        db.refresh = AsyncMock()
        db.add     = MagicMock()

        lock_svc = AsyncMock()
        mock_confirm = MagicMock(id=uuid.uuid4())
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        lock_svc.create_lock = AsyncMock(return_value=mock_confirm)

        with patch("app.engines.final_records.creation_service.generate_lead_number",
                   new=AsyncMock(return_value="LEAD-20260702-000001")):
            svc      = RealEstateFinalCreationService(db=db)
            svc.lock = lock_svc
            result   = await svc.finalize(draft.id, customer_id=draft.customer_id)

        assert result["lead_number"] == "LEAD-20260702-000001"
        assert result["idempotent"]  is False

    @pytest.mark.asyncio
    async def test_finalize_is_idempotent_for_real_estate(self):
        from app.engines.final_records.creation_service import RealEstateFinalCreationService
        from app.engines.final_records.models import CustomerBookingConfirmation
        db = AsyncMock()
        db.add   = MagicMock()
        db.flush = AsyncMock()
        existing = MagicMock(spec=CustomerBookingConfirmation)
        existing.result_number = "LEAD-20260702-000001"
        existing.result_id     = uuid.uuid4()
        existing.id            = uuid.uuid4()
        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=existing)
        svc      = RealEstateFinalCreationService(db=db)
        svc.lock = lock_svc
        result   = await svc.finalize(uuid.uuid4())
        assert result["idempotent"]  is True
        assert result["lead_number"] == "LEAD-20260702-000001"

    @pytest.mark.asyncio
    async def test_finalize_raises_on_draft_not_found(self):
        from app.engines.final_records.creation_service import RealEstateFinalCreationService
        from app.engines.final_records.constants import ERR_DRAFT_NOT_FOUND
        db = AsyncMock()
        none_res = MagicMock(); none_res.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=none_res)
        db.flush   = AsyncMock()
        lock_svc = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc      = RealEstateFinalCreationService(db=db)
        svc.lock = lock_svc
        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_FOUND):
            await svc.finalize(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# 8. Model Table Names
# ─────────────────────────────────────────────────────────────────────────────

class TestModelTableNames:
    def test_service_booking_tablename(self):
        from app.engines.final_records.models import ServiceBooking
        assert ServiceBooking.__tablename__ == "service_bookings"

    def test_service_job_tablename(self):
        from app.engines.final_records.models import ServiceJob
        assert ServiceJob.__tablename__ == "service_jobs"

    def test_coaching_appointment_tablename(self):
        from app.engines.final_records.models import CoachingAppointment
        assert CoachingAppointment.__tablename__ == "coaching_appointments"

    def test_real_estate_lead_tablename(self):
        from app.engines.final_records.models import RealEstateLead
        assert RealEstateLead.__tablename__ == "real_estate_leads"

    def test_customer_booking_confirmation_tablename(self):
        from app.engines.final_records.models import CustomerBookingConfirmation
        assert CustomerBookingConfirmation.__tablename__ == "customer_booking_confirmations"

    def test_final_creation_audit_log_tablename(self):
        from app.engines.final_records.models import FinalCreationAuditLog
        assert FinalCreationAuditLog.__tablename__ == "final_creation_audit_logs"


# ─────────────────────────────────────────────────────────────────────────────
# 9. Draft Status Guard
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftStatusGuard:
    """FinalCreationService must reject drafts not in ready_for_confirmation."""

    @pytest.mark.asyncio
    async def test_home_service_rejects_draft_status(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.final_records.constants import ERR_DRAFT_NOT_READY
        draft = _make_hs_draft()
        draft.status = "confirmed"  # already confirmed
        db = AsyncMock()
        dr = MagicMock(); dr.scalars.return_value.first.return_value = draft
        db.execute = AsyncMock(return_value=dr)
        db.flush   = AsyncMock()
        lock_svc   = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc        = HomeServiceFinalCreationService(db=db)
        svc.lock   = lock_svc
        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_READY):
            await svc.finalize(draft.id)

    @pytest.mark.asyncio
    async def test_coaching_rejects_expired_status(self):
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        from app.engines.final_records.constants import ERR_DRAFT_NOT_READY
        draft = _make_coaching_draft()
        draft.status = "expired"
        db = AsyncMock()
        dr = MagicMock(); dr.scalars.return_value.first.return_value = draft
        db.execute = AsyncMock(return_value=dr)
        db.flush   = AsyncMock()
        lock_svc   = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc        = CoachingFinalCreationService(db=db)
        svc.lock   = lock_svc
        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_READY):
            await svc.finalize(draft.id)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Confirm Router
# ─────────────────────────────────────────────────────────────────────────────

class TestConfirmRouter:
    """Confirm router builds correct response shapes and handles errors."""

    def test_confirm_router_has_three_routes(self):
        from app.engines.final_records.confirm_router import router
        paths = [r.path for r in router.routes]
        assert any("home-service-booking" in p for p in paths)
        assert any("coaching-appointment" in p for p in paths)
        assert any("real-estate-lead" in p for p in paths)

    def test_confirm_router_prefix(self):
        from app.engines.final_records.confirm_router import router
        assert router.prefix == "/v1/customer/confirm"

    def test_confirm_router_tag(self):
        from app.engines.final_records.confirm_router import router
        assert "Customer Final Confirmation" in router.tags

    def test_user_message_known_code(self):
        from app.engines.final_records.confirm_router import _user_message
        from app.engines.final_records.constants import ERR_DRAFT_NOT_FOUND, ERR_DRAFT_NOT_READY
        assert "not found" in _user_message(ERR_DRAFT_NOT_FOUND).lower()
        assert "ready" in _user_message(ERR_DRAFT_NOT_READY).lower()

    def test_user_message_unknown_code(self):
        from app.engines.final_records.confirm_router import _user_message
        msg = _user_message("UNKNOWN_CODE")
        assert "failed" in msg.lower() or "try again" in msg.lower()

    @pytest.mark.asyncio
    async def test_home_service_confirm_success_response_shape(self):
        """confirm_home_service_booking returns booking_number, job_number, record_type."""
        from app.engines.final_records.confirm_router import confirm_home_service_booking, ConfirmRequest
        draft_id    = uuid.uuid4()
        customer_id = uuid.uuid4()
        mock_result = {
            "idempotent":     False,
            "booking_number": "BK-20260702-000001",
            "booking_id":     str(uuid.uuid4()),
            "job_number":     "JOB-20260702-000001",
            "job_id":         str(uuid.uuid4()),
            "status":         "pending_assignment",
            "confirmation_id": str(uuid.uuid4()),
        }

        mock_request = MagicMock()
        mock_request.state.request_id = "req_test"

        mock_user = MagicMock()
        mock_user.user_id = str(customer_id)

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch(
            "app.engines.final_records.confirm_router.HomeServiceFinalCreationService"
        ) as MockSvc:
            instance = AsyncMock()
            instance.finalize = AsyncMock(return_value=mock_result)
            MockSvc.return_value = instance

            response = await confirm_home_service_booking(
                draft_id        = draft_id,
                body            = ConfirmRequest(),
                r               = mock_request,
                user            = mock_user,
                db              = mock_db,
                idempotency_key = "test-key-123",
            )

        data = response.data
        assert data["record_type"]    == "booking"
        assert data["booking_number"] == "BK-20260702-000001"
        assert data["job_number"]     == "JOB-20260702-000001"
        assert data["idempotent"]     is False

    @pytest.mark.asyncio
    async def test_coaching_confirm_success_response_shape(self):
        """confirm_coaching_appointment returns appointment_number, record_type."""
        from app.engines.final_records.confirm_router import confirm_coaching_appointment, ConfirmRequest
        draft_id    = uuid.uuid4()
        customer_id = uuid.uuid4()
        mock_result = {
            "idempotent":         False,
            "appointment_number": "APPT-20260702-000001",
            "appointment_id":     str(uuid.uuid4()),
            "status":             "confirmed",
            "confirmation_id":    str(uuid.uuid4()),
        }

        mock_request = MagicMock()
        mock_request.state.request_id = "req_test"
        mock_user = MagicMock(); mock_user.user_id = str(customer_id)
        mock_db   = AsyncMock(); mock_db.commit = AsyncMock()

        with patch(
            "app.engines.final_records.confirm_router.CoachingFinalCreationService"
        ) as MockSvc:
            instance = AsyncMock()
            instance.finalize = AsyncMock(return_value=mock_result)
            MockSvc.return_value = instance

            response = await confirm_coaching_appointment(
                draft_id        = draft_id,
                body            = ConfirmRequest(),
                r               = mock_request,
                user            = mock_user,
                db              = mock_db,
                idempotency_key = None,
            )

        data = response.data
        assert data["record_type"]        == "appointment"
        assert data["appointment_number"] == "APPT-20260702-000001"
        assert data["status"]             == "confirmed"

    @pytest.mark.asyncio
    async def test_real_estate_confirm_success_response_shape(self):
        """confirm_real_estate_lead returns lead_number, record_type."""
        from app.engines.final_records.confirm_router import confirm_real_estate_lead, ConfirmRequest
        draft_id    = uuid.uuid4()
        customer_id = uuid.uuid4()
        mock_result = {
            "idempotent":      False,
            "lead_number":     "LEAD-20260702-000001",
            "lead_id":         str(uuid.uuid4()),
            "status":          "new",
            "confirmation_id": str(uuid.uuid4()),
        }

        mock_request = MagicMock()
        mock_request.state.request_id = "req_test"
        mock_user = MagicMock(); mock_user.user_id = str(customer_id)
        mock_db   = AsyncMock(); mock_db.commit = AsyncMock()

        with patch(
            "app.engines.final_records.confirm_router.RealEstateFinalCreationService"
        ) as MockSvc:
            instance = AsyncMock()
            instance.finalize = AsyncMock(return_value=mock_result)
            MockSvc.return_value = instance

            response = await confirm_real_estate_lead(
                draft_id        = draft_id,
                body            = ConfirmRequest(),
                r               = mock_request,
                user            = mock_user,
                db              = mock_db,
                idempotency_key = None,
            )

        data = response.data
        assert data["record_type"] == "lead"
        assert data["lead_number"] == "LEAD-20260702-000001"
        assert data["status"]      == "new"

    @pytest.mark.asyncio
    async def test_home_service_confirm_error_response_on_not_ready(self):
        """confirm returns error dict when service raises ERR_DRAFT_NOT_READY."""
        from app.engines.final_records.confirm_router import confirm_home_service_booking, ConfirmRequest
        from app.engines.final_records.constants import ERR_DRAFT_NOT_READY

        draft_id    = uuid.uuid4()
        customer_id = uuid.uuid4()
        mock_request = MagicMock(); mock_request.state.request_id = "req_test"
        mock_user    = MagicMock(); mock_user.user_id = str(customer_id)
        mock_db      = AsyncMock(); mock_db.commit = AsyncMock()

        with patch(
            "app.engines.final_records.confirm_router.HomeServiceFinalCreationService"
        ) as MockSvc:
            instance = AsyncMock()
            instance.finalize = AsyncMock(side_effect=ValueError(ERR_DRAFT_NOT_READY))
            MockSvc.return_value = instance

            response = await confirm_home_service_booking(
                draft_id        = draft_id,
                body            = ConfirmRequest(),
                r               = mock_request,
                user            = mock_user,
                db              = mock_db,
                idempotency_key = None,
            )

        data = response.data
        assert data["success"] is False
        assert data["error"]["code"] == ERR_DRAFT_NOT_READY

    @pytest.mark.asyncio
    async def test_idempotent_home_service_confirm_returns_existing(self):
        """Duplicate confirm returns idempotent=True with same booking_number."""
        from app.engines.final_records.confirm_router import confirm_home_service_booking, ConfirmRequest
        draft_id    = uuid.uuid4()
        customer_id = uuid.uuid4()
        mock_result = {
            "idempotent":     True,
            "booking_number": "BK-20260702-000001",
            "booking_id":     str(uuid.uuid4()),
            "confirmation_id": str(uuid.uuid4()),
        }

        mock_request = MagicMock(); mock_request.state.request_id = "req_test"
        mock_user    = MagicMock(); mock_user.user_id = str(customer_id)
        mock_db      = AsyncMock(); mock_db.commit = AsyncMock()

        with patch(
            "app.engines.final_records.confirm_router.HomeServiceFinalCreationService"
        ) as MockSvc:
            instance = AsyncMock()
            instance.finalize = AsyncMock(return_value=mock_result)
            MockSvc.return_value = instance

            response = await confirm_home_service_booking(
                draft_id        = draft_id,
                body            = ConfirmRequest(),
                r               = mock_request,
                user            = mock_user,
                db              = mock_db,
                idempotency_key = "same-key",
            )

        data = response.data
        assert data["idempotent"]     is True
        assert data["booking_number"] == "BK-20260702-000001"
        assert "Already confirmed" in data["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 11. Access Control
# ─────────────────────────────────────────────────────────────────────────────

class TestAccessControl:
    """FinalCreationService must reject cross-customer access."""

    @pytest.mark.asyncio
    async def test_home_service_blocks_wrong_customer(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.final_records.constants import ERR_ACCESS_DENIED
        draft = _make_hs_draft()
        wrong_customer_id = uuid.uuid4()  # different from draft.customer_id

        db = AsyncMock()
        dr = MagicMock(); dr.scalars.return_value.first.return_value = draft
        db.execute = AsyncMock(return_value=dr)
        db.flush   = AsyncMock()
        lock_svc   = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc        = HomeServiceFinalCreationService(db=db)
        svc.lock   = lock_svc

        with pytest.raises(ValueError, match=ERR_ACCESS_DENIED):
            await svc.finalize(draft.id, customer_id=wrong_customer_id)

    @pytest.mark.asyncio
    async def test_coaching_blocks_wrong_customer(self):
        from app.engines.final_records.creation_service import CoachingFinalCreationService
        from app.engines.final_records.constants import ERR_ACCESS_DENIED
        draft = _make_coaching_draft()
        wrong_customer_id = uuid.uuid4()

        db = AsyncMock()
        dr = MagicMock(); dr.scalars.return_value.first.return_value = draft
        db.execute = AsyncMock(return_value=dr)
        db.flush   = AsyncMock()
        lock_svc   = AsyncMock()
        lock_svc.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc        = CoachingFinalCreationService(db=db)
        svc.lock   = lock_svc

        with pytest.raises(ValueError, match=ERR_ACCESS_DENIED):
            await svc.finalize(draft.id, customer_id=wrong_customer_id)
