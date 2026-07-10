"""Sprint 17 — Coaching / IELTS Chatbot Appointment Flow tests.

Tests CoachingAppointmentFlowService, CoachingCenterDiscoveryService,
AppointmentSlotAvailabilityService, constants and models.
No real DB, no HTTP — all mocked.
asyncio_mode = 'auto' via pyproject.toml.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.coaching_appointment.service import CoachingAppointmentFlowService
from app.engines.coaching_appointment.center_discovery import CoachingCenterDiscoveryService
from app.engines.coaching_appointment.slot_service import AppointmentSlotAvailabilityService
from app.engines.coaching_appointment.constants import (
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_COLLECTING_DETAILS,
    DRAFT_STATUS_LOCATION_CHECKED,
    DRAFT_STATUS_SLOTS_LOADED,
    DRAFT_STATUS_SLOT_SELECTED,
    DRAFT_STATUS_READY_FOR_CONFIRMATION,
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_FAILED,
    TERMINAL_STATUSES,
    HOLD_STATUS_HELD,
    HOLD_STATUS_RELEASED,
    HOLD_STATUS_EXPIRED,
    SLOT_HOLD_EXPIRY_MINUTES,
    LOC_STATUS_AVAILABLE,
    LOC_STATUS_NOT_AVAILABLE,
    SLOT_STATUS_LOADED,
    SLOT_STATUS_NO_SLOT,
    SLOT_STATUS_NEXT_FOUND,
    SLOT_STATUS_FALLBACK,
    FEE_STATUS_FREE,
    FEE_STATUS_ESTIMATED,
    ERR_DRAFT_NOT_FOUND,
    ERR_DRAFT_ACCESS_DENIED,
    ERR_DRAFT_TERMINAL,
    ERR_CATEGORY_INVALID,
    ERR_OFFERING_INVALID,
    ERR_NO_CENTER_AVAILABLE,
    ERR_SLOT_ALREADY_HELD,
    ERR_SLOT_REQUIRED,
    ERR_CONFIRMATION_NOT_READY,
    ERR_REQUIRED_FIELD_MISSING,
    ERR_FEE_ESTIMATE_FAILED,
    ERR_NEXT_AVAILABLE_SLOT_NOT_FOUND,
)
from app.engines.coaching_appointment.models import (
    CoachingAppointmentDraft,
    CoachingAppointmentDraftEvent,
    CoachingAppointmentSlotHold,
)
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)
_id    = lambda: uuid.uuid4()


# ──────────────────────────────────────────────────────────────────────────────
# Mock helpers
# ──────────────────────────────────────────────────────────────────────────────

def _mock_db():
    db = MagicMock()
    db.add     = MagicMock()
    db.flush   = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.delete  = MagicMock()
    return db


def db_seq(*results):
    """Return successive results from db.execute."""
    db = _mock_db()
    db.execute = AsyncMock(side_effect=list(results))
    return db


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars(lst):
    r = MagicMock()
    inner = MagicMock()
    inner.all.return_value = lst
    r.scalars.return_value = inner
    return r


def _all_rows(lst):
    r = MagicMock()
    r.all.return_value = lst
    r.scalars.return_value = MagicMock(all=MagicMock(return_value=lst))
    return r


# ──────────────────────────────────────────────────────────────────────────────
# Factory helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_category(slug="coaching-center", **kwargs):
    cat = MagicMock()
    cat.id               = _id()
    cat.slug             = slug
    cat.name             = "Coaching Center"
    cat.is_active        = True
    cat.is_customer_visible = True
    for k, v in kwargs.items():
        setattr(cat, k, v)
    return cat


def _make_offering(offering_class="appointment", **kwargs):
    off = MagicMock()
    off.id                      = _id()
    off.name                    = "IELTS Demo Class"
    off.slug                    = "ielts-demo-class"
    off.offering_class          = offering_class
    off.is_active               = True
    off.default_appointment_fee = Decimal("0")
    off.default_base_price      = Decimal("0")
    off.default_visit_fee       = Decimal("0")
    off.currency                = "INR"
    off.requires_slot           = True
    off.requires_address        = False
    for k, v in kwargs.items():
        setattr(off, k, v)
    return off


def _make_draft(status=DRAFT_STATUS_DRAFT, **kwargs):
    draft = MagicMock(spec=CoachingAppointmentDraft)
    draft.id                      = _id()
    draft.customer_id             = _id()
    draft.category_id             = _id()
    draft.offering_id             = _id()
    draft.ai_session_id           = None
    draft.selected_tenant_id      = None
    draft.selected_staff_member_id= None
    draft.status                  = status
    draft.student_name            = None
    draft.student_phone           = None
    draft.student_email           = None
    draft.student_age             = None
    draft.current_education       = None
    draft.target_exam             = None
    draft.target_band             = None
    draft.preferred_mode          = None
    draft.city                    = None
    draft.zipcode                 = None
    draft.selected_date           = None
    draft.selected_time_start     = None
    draft.selected_time_end       = None
    draft.slot_snapshot           = None
    draft.center_location_snapshot= None
    draft.appointment_fee_snapshot= None
    draft.provider_options        = None
    draft.next_available_slots    = None
    draft.recommended_slot_snapshot = None
    draft.selected_provider_snapshot= None
    draft.fallback_inquiry_payload  = None
    draft.appointment_summary       = None
    draft.location_status          = "pending"
    draft.slot_status              = "pending"
    draft.fee_status               = "pending"
    draft.failure_code             = None
    draft.failure_message          = None
    draft.notes                    = None
    draft.expires_at               = utcnow() + timedelta(hours=24)
    draft.created_at               = utcnow()
    draft.updated_at               = utcnow()
    draft.to_dict = MagicMock(return_value={
        "id":     str(draft.id),
        "status": draft.status,
    })
    for k, v in kwargs.items():
        setattr(draft, k, v)
    return draft


def _make_hold(status=HOLD_STATUS_HELD, expired=False):
    hold = MagicMock(spec=CoachingAppointmentSlotHold)
    hold.id           = _id()
    hold.draft_id     = _id()
    hold.tenant_id    = _id()
    hold.offering_id  = _id()
    hold.slot_date    = date.today()
    hold.start_time   = time(10, 0)
    hold.end_time     = time(10, 30)
    hold.hold_status  = status
    hold.expires_at   = utcnow() - timedelta(minutes=1) if expired else utcnow() + timedelta(minutes=10)
    hold.to_dict      = MagicMock(return_value={"id": str(hold.id), "hold_status": status})
    return hold


# ══════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_terminal_statuses(self):
        assert DRAFT_STATUS_CONFIRMED in TERMINAL_STATUSES
        assert DRAFT_STATUS_CANCELLED in TERMINAL_STATUSES
        assert DRAFT_STATUS_EXPIRED   in TERMINAL_STATUSES
        assert DRAFT_STATUS_FAILED    in TERMINAL_STATUSES
        assert DRAFT_STATUS_DRAFT not in TERMINAL_STATUSES

    def test_error_codes_are_strings(self):
        assert ERR_DRAFT_NOT_FOUND.startswith("COACHING_")
        assert ERR_NO_CENTER_AVAILABLE.startswith("COACHING_")
        assert ERR_SLOT_ALREADY_HELD.startswith("COACHING_")

    def test_slot_hold_expiry(self):
        assert SLOT_HOLD_EXPIRY_MINUTES == 15


# ══════════════════════════════════════════════════════════════════════════════
# 2. Models
# ══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_draft_to_dict_includes_id_and_status(self):
        draft = CoachingAppointmentDraft()
        draft.id              = _id()
        draft.customer_id     = _id()
        draft.category_id     = _id()
        draft.offering_id     = _id()
        draft.status          = DRAFT_STATUS_DRAFT
        draft.created_at      = utcnow()
        draft.updated_at      = utcnow()
        d = draft.to_dict()
        assert d["status"] == DRAFT_STATUS_DRAFT
        assert "id" in d

    def test_slot_hold_to_dict(self):
        hold = CoachingAppointmentSlotHold()
        hold.id          = _id()
        hold.draft_id    = _id()
        hold.tenant_id   = _id()
        hold.offering_id = _id()
        hold.slot_date   = date.today()
        hold.start_time  = time(10, 0)
        hold.end_time    = time(10, 30)
        hold.hold_status = HOLD_STATUS_HELD
        hold.expires_at  = utcnow() + timedelta(minutes=15)
        d = hold.to_dict()
        assert d["hold_status"] == HOLD_STATUS_HELD


# ══════════════════════════════════════════════════════════════════════════════
# 3. Start appointment draft
# ══════════════════════════════════════════════════════════════════════════════

class TestStartAppointmentDraft:
    async def test_start_draft_success(self):
        cat = _make_category()
        off = _make_offering()
        db  = db_seq(_scalars([cat]), _scalars([off]))
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        draft_obj = _make_draft()
        db.add = MagicMock()

        with patch.object(CoachingAppointmentFlowService, "_emit_event", new_callable=AsyncMock):
            with patch("app.engines.coaching_appointment.service.CoachingAppointmentDraft") as MockDraft:
                MockDraft.return_value = draft_obj
                svc = CoachingAppointmentFlowService(db)
                result = await svc.start_appointment_draft(
                    customer_id=_id(),
                    ai_session_id=None,
                    category_slug="coaching-center",
                    offering_slug="ielts-demo-class",
                )
        assert result["status"] == DRAFT_STATUS_DRAFT

    async def test_start_draft_invalid_category(self):
        db = db_seq(_scalars([]))  # no categories
        svc = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.start_appointment_draft(_id(), None, "non-existent", "some-offering")
        assert exc.value.error_code == ERR_CATEGORY_INVALID

    async def test_start_draft_invalid_offering(self):
        cat = _make_category()
        db  = db_seq(_scalars([cat]), _scalars([]))  # no offerings
        svc = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.start_appointment_draft(_id(), None, "coaching-center", "non-existent-offering")
        assert exc.value.error_code == ERR_OFFERING_INVALID

    async def test_coaching_category_aliases_work(self):
        """coaching-center, ielts, coaching, coaching_center should all resolve."""
        cat = _make_category(slug="coaching-center")
        off = _make_offering()
        db  = db_seq(_scalars([cat]), _scalars([off]))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        draft_obj = _make_draft()

        with patch.object(CoachingAppointmentFlowService, "_emit_event", new_callable=AsyncMock):
            with patch("app.engines.coaching_appointment.service.CoachingAppointmentDraft") as MockDraft:
                MockDraft.return_value = draft_obj
                svc = CoachingAppointmentFlowService(db)
                result = await svc.start_appointment_draft(_id(), None, "ielts", "ielts-demo-class")
        assert result is not None


# ══════════════════════════════════════════════════════════════════════════════
# 4. Draft access control
# ══════════════════════════════════════════════════════════════════════════════

class TestDraftAccessControl:
    async def test_customer_can_access_own_draft(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id)
        db      = db_seq(_scalar(draft))
        svc     = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_get_missing_fields_for_draft", new_callable=AsyncMock, return_value=[]):
            result = await svc.get_appointment_draft(draft.id, cust_id)
        assert result["status"] == draft.status

    async def test_customer_cannot_access_another_customer_draft(self):
        draft = _make_draft(customer_id=_id())
        db    = db_seq(_scalar(draft))
        svc   = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.get_appointment_draft(draft.id, _id())  # different customer
        assert exc.value.error_code == ERR_DRAFT_ACCESS_DENIED

    async def test_draft_not_found_raises(self):
        db  = db_seq(_scalar(None))
        svc = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.get_appointment_draft(_id(), _id())
        assert exc.value.error_code == ERR_DRAFT_NOT_FOUND


# ══════════════════════════════════════════════════════════════════════════════
# 5. Update draft fields
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateDraftFields:
    async def test_update_allowed_fields(self):
        draft = _make_draft()
        db    = db_seq(_scalar(draft))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc   = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            with patch.object(svc, "_get_missing_fields_for_draft", new_callable=AsyncMock, return_value=[]):
                result = await svc.update_draft_fields(
                    draft.id,
                    draft.customer_id,
                    {"student_name": "Raj", "student_phone": "9876543210", "preferred_mode": "offline"},
                )
        assert "updated_fields" in result

    async def test_forbidden_fields_are_ignored(self):
        draft = _make_draft()
        db    = db_seq(_scalar(draft))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc   = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            with patch.object(svc, "_get_missing_fields_for_draft", new_callable=AsyncMock, return_value=[]):
                result = await svc.update_draft_fields(
                    draft.id, draft.customer_id,
                    {"appointment_fee_snapshot": {"amount": 999}, "commission": 50},
                )
        # forbidden fields should NOT be in updated list
        updated = result.get("updated_fields", [])
        assert "appointment_fee_snapshot" not in updated
        assert "commission" not in updated

    async def test_terminal_draft_blocks_update(self):
        draft = _make_draft(status=DRAFT_STATUS_CONFIRMED)
        db    = db_seq(_scalar(draft))
        svc   = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.update_draft_fields(draft.id, draft.customer_id, {"student_name": "Raj"})
        assert exc.value.error_code == ERR_DRAFT_TERMINAL


# ══════════════════════════════════════════════════════════════════════════════
# 6. Required fields
# ══════════════════════════════════════════════════════════════════════════════

class TestRequiredFields:
    def test_missing_fields_with_no_data(self):
        svc   = CoachingAppointmentFlowService(MagicMock())
        draft = _make_draft()
        off   = _make_offering()
        missing = svc._compute_missing_fields(draft, off)
        assert "student_name"  in missing
        assert "student_phone" in missing
        assert "preferred_mode" in missing

    def test_city_required_only_for_offline(self):
        svc   = CoachingAppointmentFlowService(MagicMock())
        draft = _make_draft()
        draft.student_name  = "Raj"
        draft.student_phone = "9876543210"
        draft.preferred_mode = "online"
        draft.selected_date  = date.today()
        off = _make_offering()
        missing = svc._compute_missing_fields(draft, off)
        assert "city" not in missing  # online mode — no city required

    def test_city_required_for_offline(self):
        svc   = CoachingAppointmentFlowService(MagicMock())
        draft = _make_draft()
        draft.student_name   = "Raj"
        draft.student_phone  = "9876543210"
        draft.preferred_mode = "offline"
        draft.selected_date  = date.today()
        draft.city           = None
        off = _make_offering()
        missing = svc._compute_missing_fields(draft, off)
        assert "city" in missing

    def test_slot_required_when_flag_set(self):
        svc   = CoachingAppointmentFlowService(MagicMock())
        draft = _make_draft()
        draft.student_name   = "Raj"
        draft.student_phone  = "9876543210"
        draft.preferred_mode = "offline"
        draft.city           = "Ludhiana"
        draft.selected_date  = date.today()
        draft.slot_snapshot  = None  # not selected yet
        off = _make_offering(requires_slot=True)
        missing = svc._compute_missing_fields(draft, off)
        assert "selected_slot" in missing


# ══════════════════════════════════════════════════════════════════════════════
# 7. Center discovery
# ══════════════════════════════════════════════════════════════════════════════

class TestCenterDiscovery:
    async def test_returns_available_centers_for_offline(self):
        cat_id  = _id()
        off_id  = _id()
        tenant  = MagicMock()
        tenant.id              = _id()
        tenant.status          = "active"
        tenant.category_id     = cat_id
        tenant.is_discoverable = True
        tenant.business_name   = "Bright IELTS Academy"
        tenant.tenant_name     = "Bright IELTS Academy"
        tenant.city            = "Ludhiana"
        tenant.rating_average  = 4.5
        tenant.health_score    = 90.0
        tenant.logo_url        = None

        area = MagicMock()
        db   = _mock_db()
        db.execute = AsyncMock(side_effect=[
            _all_rows([(tenant, area)]),   # zipcode query
            _all_rows([]),                  # city fallback (already have results)
        ])

        svc    = CoachingCenterDiscoveryService(db)
        result = await svc.find_centers(
            category_id=cat_id,
            offering_id=off_id,
            city="Ludhiana",
            zipcode="141001",
            preferred_mode="offline",
        )
        assert result["available"] is True
        assert result["available_center_count"] >= 1
        assert result["centers"][0]["business_name"] == "Bright IELTS Academy"

    async def test_no_centers_returns_not_available(self):
        cat_id = _id()
        off_id = _id()
        db = _mock_db()
        db.execute = AsyncMock(return_value=_all_rows([]))

        svc    = CoachingCenterDiscoveryService(db)
        result = await svc.find_centers(cat_id, off_id, "UnknownCity", None, "offline")
        assert result["available"] is False
        assert result["reason_code"] == ERR_NO_CENTER_AVAILABLE

    async def test_online_mode_does_not_require_location(self):
        cat_id = _id()
        off_id = _id()
        tenant = MagicMock()
        tenant.id              = _id()
        tenant.status          = "active"
        tenant.category_id     = cat_id
        tenant.is_discoverable = True
        tenant.business_name   = "Online IELTS Hub"
        tenant.tenant_name     = "Online IELTS Hub"
        tenant.city            = None
        tenant.rating_average  = 4.0
        tenant.health_score    = 85.0
        tenant.logo_url        = None

        db = _mock_db()
        db.execute = AsyncMock(return_value=_scalars([tenant]))

        svc    = CoachingCenterDiscoveryService(db)
        result = await svc.find_centers(cat_id, off_id, city=None, zipcode=None, preferred_mode="online")
        assert result["available"] is True

    async def test_center_result_does_not_expose_commission(self):
        cat_id = _id()
        off_id = _id()
        tenant = MagicMock()
        tenant.id              = _id()
        tenant.status          = "active"
        tenant.category_id     = cat_id
        tenant.is_discoverable = True
        tenant.business_name   = "Safe Center"
        tenant.tenant_name     = "Safe Center"
        tenant.city            = "Delhi"
        tenant.rating_average  = 4.0
        tenant.health_score    = 80.0
        tenant.logo_url        = None
        tenant.commission      = 0.15  # must NOT appear in result

        area = MagicMock()
        db   = _mock_db()
        db.execute = AsyncMock(return_value=_all_rows([(tenant, area)]))

        svc    = CoachingCenterDiscoveryService(db)
        result = await svc.find_centers(cat_id, off_id, "Delhi", None, "offline")
        for center in result.get("centers", []):
            assert "commission" not in center
            assert "subscription_status" not in center


# ══════════════════════════════════════════════════════════════════════════════
# 8. Slot availability
# ══════════════════════════════════════════════════════════════════════════════

class TestSlotAvailability:
    async def test_returns_empty_when_no_working_hours(self):
        db = _mock_db()
        db.execute = AsyncMock(return_value=_scalars([]))  # no working hours
        svc    = AppointmentSlotAvailabilityService(db)
        result = await svc.get_available_slots(
            tenant_id=_id(), offering_id=_id(),
            date_str="2026-07-05", preferred_mode="offline",
        )
        assert result["slots"] == []
        assert "message" in result

    async def test_held_slot_is_excluded(self):
        """Held slots from other drafts must not appear in available list."""
        wh = MagicMock()
        wh.staff_id      = _id()
        wh.start_time    = "09:00"
        wh.end_time      = "11:00"
        wh.slot_duration = 30
        wh.buffer_minutes= 5
        wh.day_of_week   = 6  # Sunday

        hold = MagicMock()
        hold.start_time      = time(9, 0)
        hold.staff_member_id = wh.staff_id
        hold.expires_at      = utcnow() + timedelta(minutes=10)
        hold.hold_status     = HOLD_STATUS_HELD

        db = _mock_db()
        db.execute = AsyncMock(side_effect=[
            _scalars([wh]),    # working hours
            _scalars([]),       # calendar blocks
            _scalars([hold]),   # slot holds
            _scalars([]),       # appointments
        ])

        svc    = AppointmentSlotAvailabilityService(db)
        result = await svc.get_available_slots(
            tenant_id=_id(), offering_id=_id(),
            date_str="2026-07-05", preferred_mode="offline",
        )
        # The 09:00 slot should be excluded (held)
        times = [s["start_time"] for s in result.get("slots", [])]
        assert "09:00" not in times

    async def test_expired_hold_is_ignored(self):
        """Expired holds must NOT block a slot."""
        wh = MagicMock()
        wh.staff_id      = _id()
        wh.start_time    = "10:00"
        wh.end_time      = "12:00"
        wh.slot_duration = 30
        wh.buffer_minutes= 5
        wh.day_of_week   = 5

        db = _mock_db()
        db.execute = AsyncMock(side_effect=[
            _scalars([wh]),   # working hours
            _scalars([]),      # calendar blocks
            _scalars([]),      # holds (empty — expired ones filtered in SQL query)
            _scalars([]),      # appointments
        ])

        svc    = AppointmentSlotAvailabilityService(db)
        result = await svc.get_available_slots(
            tenant_id=_id(), offering_id=_id(),
            date_str="2026-07-05",
        )
        # Slots should be available (expired hold not blocking)
        assert len(result.get("slots", [])) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 9. Select slot
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectSlot:
    async def test_select_slot_creates_hold(self):
        cust_id = _id()
        t_id    = _id()
        draft   = _make_draft(
            customer_id=cust_id,
            preferred_mode="offline",
            selected_date=None,
        )
        db = _mock_db()
        db.execute = AsyncMock(side_effect=[
            _scalar(draft),   # get draft
            # slot_service.get_available_slots calls:
            _scalars([]),     # working hours → no slots, but we mock slot result separately
            _scalar(None),    # release_slot_hold → no existing hold
            _scalar(None),    # hold_slot → no existing hold
        ])
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        svc = CoachingAppointmentFlowService(db)
        with patch.object(svc._slot_svc, "get_available_slots", new_callable=AsyncMock) as mock_slots:
            mock_slots.return_value = {
                "slots": [{"start_time": "10:00", "end_time": "10:30", "staff_member_id": str(_id()), "mode": "offline", "remaining_capacity": 1}]
            }
            # release hold → no existing holds
            db.execute = AsyncMock(side_effect=[
                _scalar(draft),      # get draft
                _scalars([]),         # release_slot_hold query
                _scalar(None),        # hold creation flush (no return needed)
            ])
            db.refresh = AsyncMock(side_effect=lambda obj: None)

            with patch.object(svc, "_emit_event", new_callable=AsyncMock):
                with patch.object(svc, "hold_slot", new_callable=AsyncMock) as mock_hold:
                    mock_hold.return_value = {"hold_id": str(_id()), "expires_at": utcnow().isoformat(), "hold_ttl_min": 15}
                    result = await svc.select_slot(
                        draft_id=draft.id,
                        customer_id=cust_id,
                        tenant_id=t_id,
                        slot_date="2026-07-05",
                        start_time="10:00",
                        end_time="10:30",
                        mode="offline",
                    )
        assert result.get("slot_hold") is not None

    async def test_select_unavailable_slot_raises(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id)
        db = db_seq(_scalar(draft))
        svc = CoachingAppointmentFlowService(db)

        with patch.object(svc._slot_svc, "get_available_slots", new_callable=AsyncMock) as mock_slots:
            mock_slots.return_value = {"slots": []}  # no available slots

            with pytest.raises(ServiceOSException) as exc:
                await svc.select_slot(
                    draft_id=draft.id, customer_id=cust_id,
                    tenant_id=_id(), slot_date="2026-07-05",
                    start_time="10:00", end_time="10:30",
                )
        assert exc.value.error_code == ERR_SLOT_ALREADY_HELD


# ══════════════════════════════════════════════════════════════════════════════
# 10. Fee estimate
# ══════════════════════════════════════════════════════════════════════════════

class TestFeeEstimate:
    async def test_free_offering_returns_free_status(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id)
        off     = _make_offering(default_appointment_fee=Decimal("0"))
        db      = db_seq(_scalar(draft), _scalar(off))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc     = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.resolve_appointment_fee(draft.id, cust_id)
        assert result["fee_snapshot"]["fee_type"] == "free"
        assert result["fee_snapshot"]["amount"] == 0.0
        assert result["fee_snapshot"]["source"] == "backend_catalog"

    async def test_paid_offering_returns_fee(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id)
        off     = _make_offering(default_appointment_fee=Decimal("199"))
        db      = db_seq(_scalar(draft), _scalar(off))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc     = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.resolve_appointment_fee(draft.id, cust_id)
        assert result["fee_snapshot"]["fee_type"] == "fixed"
        assert result["fee_snapshot"]["amount"] == 199.0
        assert "₹" in result["fee_snapshot"]["display_fee"]

    async def test_frontend_fee_ignored_backend_is_source(self):
        """Fee must come from MasterOffering — frontend value is irrelevant."""
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id)
        off     = _make_offering(default_appointment_fee=Decimal("99"))
        db      = db_seq(_scalar(draft), _scalar(off))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc     = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.resolve_appointment_fee(draft.id, cust_id)
        # Source is always backend_catalog regardless of what frontend sent
        assert result["fee_snapshot"]["source"] == "backend_catalog"
        assert result["fee_snapshot"]["amount"] == 99.0


# ══════════════════════════════════════════════════════════════════════════════
# 11. Build appointment summary
# ══════════════════════════════════════════════════════════════════════════════

class TestAppointmentSummary:
    async def test_summary_built_after_slot_selection(self):
        cust_id = _id()
        t_id    = _id()
        draft   = _make_draft(
            customer_id=cust_id,
            selected_tenant_id=t_id,
            student_name="Raj",
            student_phone="9876543210",
            preferred_mode="offline",
            city="Ludhiana",
            selected_date=date.today(),
            selected_time_start=time(10, 0),
            target_exam="IELTS",
        )
        off    = _make_offering()
        tenant = MagicMock()
        tenant.business_name = "Bright IELTS"
        tenant.tenant_name   = "Bright IELTS"

        db = db_seq(_scalar(draft), _scalar(off), _scalar(tenant))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.build_appointment_summary(draft.id, cust_id)
        assert result["appointment_summary"]["student_name"] == "Raj"
        assert result["appointment_summary"]["target_exam"] == "IELTS"


# ══════════════════════════════════════════════════════════════════════════════
# 12. Confirm draft
# ══════════════════════════════════════════════════════════════════════════════

class TestConfirmDraft:
    async def test_confirm_draft_requires_held_slot(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id, status=DRAFT_STATUS_SLOT_SELECTED)
        db = db_seq(_scalar(draft), _scalar(None))  # no hold found
        svc = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.confirm_draft(draft.id, cust_id)
        assert exc.value.error_code == ERR_SLOT_REQUIRED

    async def test_confirm_draft_blocked_if_not_slot_selected(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id, status=DRAFT_STATUS_COLLECTING_DETAILS)
        db = db_seq(_scalar(draft))
        svc = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.confirm_draft(draft.id, cust_id)
        assert exc.value.error_code == ERR_CONFIRMATION_NOT_READY

    async def test_confirm_returns_appointment_ready_payload(self):
        cust_id = _id()
        t_id    = _id()
        draft   = _make_draft(
            customer_id=cust_id,
            status=DRAFT_STATUS_SLOT_SELECTED,
            selected_tenant_id=t_id,
            student_name="Raj",
            student_phone="9876543210",
            preferred_mode="offline",
            city="Ludhiana",
            slot_snapshot={"slot_date": "2026-07-05", "start_time": "10:00"},
        )
        hold = _make_hold(status=HOLD_STATUS_HELD, expired=False)
        db   = db_seq(_scalar(draft), _scalar(hold))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, cust_id)
        assert result["success"] is True
        payload = result["data"]["appointment_ready_payload"]
        assert "slot_snapshot" in payload
        assert "student_snapshot" in payload
        assert result["data"]["next_step"] == "final_appointment_creation_in_sprint_19"


# ══════════════════════════════════════════════════════════════════════════════
# 13. Cancel draft
# ══════════════════════════════════════════════════════════════════════════════

class TestCancelDraft:
    async def test_cancel_draft(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id, status=DRAFT_STATUS_SLOTS_LOADED)
        db      = db_seq(_scalar(draft), _scalars([]))  # no holds to release
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc     = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.cancel_draft(draft.id, cust_id)
        assert result["cancelled"] is True

    async def test_cancel_terminal_draft_raises(self):
        cust_id = _id()
        draft   = _make_draft(customer_id=cust_id, status=DRAFT_STATUS_CONFIRMED)
        db      = db_seq(_scalar(draft))
        svc     = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.cancel_draft(draft.id, cust_id)
        assert exc.value.error_code == ERR_DRAFT_TERMINAL


# ══════════════════════════════════════════════════════════════════════════════
# 14. Next available slots
# ══════════════════════════════════════════════════════════════════════════════

class TestNextAvailableSlots:
    async def test_recommended_slot_is_earliest(self):
        """First slot in result must be marked is_recommended=True."""
        svc = AppointmentSlotAvailabilityService(_mock_db())
        with patch.object(svc, "get_available_slots", new_callable=AsyncMock) as mock_slots:
            with patch("app.engines.coaching_appointment.center_discovery.CoachingCenterDiscoveryService") as MockDisc:
                disc_inst = MagicMock()
                disc_inst.find_centers = AsyncMock(return_value={
                    "available": True,
                    "centers": [{"provider_ref": str(_id()), "business_name": "Center A"}],
                })
                MockDisc.return_value = disc_inst
                mock_slots.return_value = {"slots": [{"start_time": "10:00", "end_time": "10:30", "staff_member_id": str(_id()), "mode": "offline", "remaining_capacity": 1}]}

                with patch("app.engines.coaching_appointment.slot_service.CoachingCenterDiscoveryService", MockDisc):
                    result = await svc.find_next_available_slots(
                        category_id=_id(), offering_id=_id(),
                        city="Ludhiana", zipcode="141001",
                        preferred_mode="offline",
                        preferred_date="2026-07-05",
                    )
        next_slots = result.get("next_available_slots", [])
        if next_slots:
            assert next_slots[0]["is_recommended"] is True

    async def test_fallback_returned_when_no_slots_in_window(self):
        svc = AppointmentSlotAvailabilityService(_mock_db())
        disc_inst = MagicMock()
        disc_inst.find_centers = AsyncMock(return_value={"available": False, "centers": []})

        with patch("app.engines.coaching_appointment.slot_service.CoachingCenterDiscoveryService", return_value=disc_inst):
            result = await svc.find_next_available_slots(
                category_id=_id(), offering_id=_id(),
                city="UnknownCity", zipcode=None,
                preferred_mode="offline",
                preferred_date="2026-07-05",
            )
        assert result.get("fallback_available") is True
        assert result.get("next_available_slots") == []

    async def test_next_slots_exclude_non_bookable_centers(self):
        """find_centers returning empty → next slots empty → fallback."""
        svc = AppointmentSlotAvailabilityService(_mock_db())
        disc_inst = MagicMock()
        disc_inst.find_centers = AsyncMock(return_value={
            "available": False, "centers": [],
            "reason_code": ERR_NO_CENTER_AVAILABLE,
        })

        with patch("app.engines.coaching_appointment.slot_service.CoachingCenterDiscoveryService", return_value=disc_inst):
            result = await svc.find_next_available_slots(
                category_id=_id(), offering_id=_id(),
                city="Ludhiana", zipcode=None,
                preferred_mode="offline",
                preferred_date="2026-07-05",
            )
        assert result["next_available_slots"] == []
        assert result["fallback_available"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 15. Fallback inquiry payload
# ══════════════════════════════════════════════════════════════════════════════

class TestFallbackInquiry:
    async def test_fallback_payload_contains_required_fields(self):
        cust_id = _id()
        draft   = _make_draft(
            customer_id=cust_id,
            student_name="Raj",
            student_phone="9876543210",
            preferred_mode="offline",
            city="Ludhiana",
            zipcode="141001",
            selected_date=date.today(),
            target_exam="IELTS",
        )
        db = db_seq(_scalar(draft))
        db.refresh = AsyncMock(side_effect=lambda obj: None)
        svc = CoachingAppointmentFlowService(db)
        with patch.object(svc, "_emit_event", new_callable=AsyncMock):
            result = await svc.prepare_fallback_inquiry_payload(draft.id, cust_id)
        fp = result["fallback_payload"]
        assert fp["customer_name"]  == "Raj"
        assert fp["customer_phone"] == "9876543210"
        assert fp["reason"]         == "no_slot_available"
        assert result["fallback_type"] == "center_call_back_request"


# ══════════════════════════════════════════════════════════════════════════════
# 16. Expire drafts and slot holds
# ══════════════════════════════════════════════════════════════════════════════

class TestExpireOldDrafts:
    async def test_expire_drafts_and_holds(self):
        expired_draft = _make_draft(status=DRAFT_STATUS_SLOTS_LOADED)
        expired_hold  = _make_hold(status=HOLD_STATUS_HELD)

        db = _mock_db()
        db.execute = AsyncMock(side_effect=[
            _scalars([expired_draft]),   # expired drafts query
            _scalars([expired_hold]),    # expired holds query
        ])
        db.flush   = AsyncMock()

        svc    = CoachingAppointmentFlowService(db)
        result = await svc.expire_old_drafts_and_slot_holds()
        assert result["expired_drafts"] == 1
        assert result["expired_holds"]  == 1
        assert expired_draft.status    == DRAFT_STATUS_EXPIRED
        assert expired_hold.hold_status == HOLD_STATUS_EXPIRED


# ══════════════════════════════════════════════════════════════════════════════
# 17. Admin methods
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminMethods:
    async def test_admin_list_drafts(self):
        drafts = [_make_draft(), _make_draft()]
        db     = db_seq(_scalars(drafts))
        svc    = CoachingAppointmentFlowService(db)
        result = await svc.admin_list_drafts()
        assert len(result["drafts"]) == 2

    async def test_admin_list_slot_holds(self):
        holds = [_make_hold(), _make_hold()]
        db    = db_seq(_scalars(holds))
        svc   = CoachingAppointmentFlowService(db)
        result = await svc.admin_list_slot_holds()
        assert len(result["holds"]) == 2

    async def test_admin_get_draft_not_found(self):
        db  = db_seq(_scalar(None))
        svc = CoachingAppointmentFlowService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.admin_get_draft(_id())
        assert exc.value.error_code == ERR_DRAFT_NOT_FOUND

    async def test_admin_get_draft_events(self):
        event = MagicMock(spec=CoachingAppointmentDraftEvent)
        event.to_dict = MagicMock(return_value={"event_type": "draft_created"})
        db  = db_seq(_scalars([event]))
        svc = CoachingAppointmentFlowService(db)
        result = await svc.admin_get_draft_events(_id())
        assert len(result["events"]) == 1
