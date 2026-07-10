"""
Step 4 — Booking Preflight + Booking Creation Integration
44 tests covering:
  - Booking preflight (run_booking_preflight)
  - Booking creation (create_booking)
  - Isolation / RBAC (get_booking, cancel_booking)
  - List endpoints (list_bookings)
  - Schema / constants / error codes
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _make_svc(actor_role="customer", actor_id=None, actor_tenant_id=None, db=None):
    from app.engines.booking.service import BookingService
    _db = db or _make_db()
    _actor_id = actor_id or uuid.uuid4()
    svc = BookingService(
        db=_db,
        request_id="test-req",
        actor_id=_actor_id,
        actor_role=actor_role,
        actor_tenant_id=actor_tenant_id,
    )
    return svc, _db, _actor_id


def _make_booking(status="pending_confirmation", customer_id=None, tenant_id=None, **kwargs):
    """Build a mock Booking object."""
    from app.engines.booking.models import Booking
    b = MagicMock(spec=Booking)
    b.id = uuid.uuid4()
    b.booking_number = "BK-202606-12345"
    b.tenant_id = tenant_id or uuid.uuid4()
    b.customer_id = customer_id or uuid.uuid4()
    b.service_type_id = "ac_service"
    b.service_category = "hvac"
    b.status = status
    b.quoted_price = Decimal("800.00")
    b.estimated_price = Decimal("800.00")
    b.final_price = None
    b.price_snapshot_id = None
    b.preferred_date = None
    b.preferred_slot = None
    b.scheduled_at = None
    b.address = {}
    b.city = "Mumbai"
    b.pincode = "400001"
    b.address_id = uuid.uuid4()
    b.matched_service_area_id = uuid.uuid4()
    b.matched_service_area_service_id = uuid.uuid4()
    b.coverage_match_level = "zipcode"
    b.service_id = uuid.uuid4()
    b.job_type = "repair"
    b.sla_minutes = 60
    b.matching_snapshot = []
    b.preflight_passed = True
    b.preflight_result = {"passed": True}
    b.blocking_reason = None
    b.job_id = None
    b.cancelled_at = None
    b.cancellation_reason = None
    b.cancellation_policy = "standard"
    b.within_cancel_window = None
    b.reschedule_count = 0
    b.customer_notes = None
    b.internal_notes = None
    b.tags = []
    b.meta = {}
    b.reservation_id = None
    b.idempotency_key = None
    b.converted_at = None
    b.created_at = datetime.now(timezone.utc)
    for k, v in kwargs.items():
        setattr(b, k, v)
    return b


def _mock_match_result(tenant_id=None, city="Mumbai", zipcode="400001"):
    tid = tenant_id or str(uuid.uuid4())
    return [{
        "tenant_id": tid,
        "tenant_name": "TestCo Services",
        "coverage_match_level": "zipcode",
        "coverage_rank": 1,
        "matched_area_id": str(uuid.uuid4()),
        "service_area_service_id": str(uuid.uuid4()),
        "health_score": 0.9,
        "rating": 4.5,
        "staff_capacity": 3,
        "estimated_sla_minutes": 60,
        "base_price": 800.0,
        "min_price": 600.0,
        "max_price": 1200.0,
        "distance_km": None,
        "match_reason": "zipcode match",
    }]


# ══════════════════════════════════════════════════════════════════════════════
# 1-3: Constants and status machine
# ══════════════════════════════════════════════════════════════════════════════

def test_1_bs_pending_confirmation_value():
    from app.engines.booking.constants import BS
    assert BS.PENDING_CONFIRMATION == "pending_confirmation"


def test_2_booking_transitions_include_pending_confirmation():
    from app.engines.booking.constants import BOOKING_TRANSITIONS, BS
    assert BS.PENDING_CONFIRMATION in BOOKING_TRANSITIONS
    transitions = BOOKING_TRANSITIONS[BS.PENDING_CONFIRMATION]
    assert BS.CONFIRMED in transitions
    assert BS.CANCELLED in transitions


def test_3_terminal_statuses_do_not_include_pending_confirmation():
    from app.engines.booking.constants import TERMINAL_BOOKING_STATUSES, BS
    assert BS.PENDING_CONFIRMATION not in TERMINAL_BOOKING_STATUSES


# ══════════════════════════════════════════════════════════════════════════════
# 4-6: Error codes registered
# ══════════════════════════════════════════════════════════════════════════════

def test_4_error_codes_booking_not_found():
    from app.schemas.base import ERROR_CODES
    assert "BOOKING_NOT_FOUND" in ERROR_CODES
    assert ERROR_CODES["BOOKING_NOT_FOUND"]["status"] == 404


def test_5_error_codes_booking_cannot_be_cancelled():
    from app.schemas.base import ERROR_CODES
    assert "BOOKING_CANNOT_BE_CANCELLED" in ERROR_CODES
    assert ERROR_CODES["BOOKING_CANNOT_BE_CANCELLED"]["status"] == 409


def test_6_error_codes_step4_all_registered():
    from app.schemas.base import ERROR_CODES
    required = [
        "BOOKING_NOT_FOUND", "BOOKING_ACCESS_DENIED", "BOOKING_CANNOT_BE_CANCELLED",
        "BOOKING_PREFLIGHT_FAILED", "BOOKING_CREATE_FAILED", "SCHEDULED_TIME_IN_PAST",
        "BOOKING_SLOT_NOT_AVAILABLE", "PRICING_NOT_CONFIGURED", "SLA_NOT_CONFIGURED",
        "TENANT_INACTIVE", "SERVICE_AREA_INACTIVE", "SERVICE_MAPPING_INACTIVE",
        "FRONTEND_TENANT_ID_NOT_ALLOWED",
    ]
    for code in required:
        assert code in ERROR_CODES, f"Missing error code: {code}"


# ══════════════════════════════════════════════════════════════════════════════
# 7-8: Booking model has new fields
# ══════════════════════════════════════════════════════════════════════════════

def test_7_booking_model_has_city_field():
    from app.engines.booking.models import Booking
    assert hasattr(Booking, "city")


def test_8_booking_model_has_step4_fields():
    from app.engines.booking.models import Booking
    for field in ["city", "matched_service_area_service_id", "estimated_price",
                  "final_price", "sla_minutes", "matching_snapshot"]:
        assert hasattr(Booking, field), f"Booking is missing field: {field}"


# ══════════════════════════════════════════════════════════════════════════════
# 9-12: _assert_can_access_booking — isolation logic
# ══════════════════════════════════════════════════════════════════════════════

def test_9_assert_can_access_customer_own_booking():
    from app.engines.booking.service import BookingService
    from app.exceptions import NotFoundException
    cid = uuid.uuid4()
    svc = BookingService(db=_make_db(), actor_id=cid, actor_role="customer")
    b = _make_booking(customer_id=cid)
    svc._assert_can_access_booking(b)  # Should not raise


def test_10_assert_can_access_customer_other_booking_raises_404():
    from app.engines.booking.service import BookingService
    from app.exceptions import NotFoundException
    svc = BookingService(db=_make_db(), actor_id=uuid.uuid4(), actor_role="customer")
    b = _make_booking(customer_id=uuid.uuid4())
    with pytest.raises(NotFoundException):
        svc._assert_can_access_booking(b)


def test_11_assert_can_access_tenant_owner_own_tenant():
    from app.engines.booking.service import BookingService
    tid = uuid.uuid4()
    svc = BookingService(db=_make_db(), actor_id=uuid.uuid4(),
                         actor_role="tenant_owner", actor_tenant_id=tid)
    b = _make_booking(tenant_id=tid)
    svc._assert_can_access_booking(b)  # Should not raise


def test_12_assert_can_access_tenant_owner_other_tenant_raises_404():
    from app.engines.booking.service import BookingService
    from app.exceptions import NotFoundException
    svc = BookingService(db=_make_db(), actor_id=uuid.uuid4(),
                         actor_role="tenant_owner", actor_tenant_id=uuid.uuid4())
    b = _make_booking(tenant_id=uuid.uuid4())
    with pytest.raises(NotFoundException):
        svc._assert_can_access_booking(b)


# ══════════════════════════════════════════════════════════════════════════════
# 13: super_admin can access any booking
# ══════════════════════════════════════════════════════════════════════════════

def test_13_super_admin_can_access_any_booking():
    from app.engines.booking.service import BookingService
    svc = BookingService(db=_make_db(), actor_id=uuid.uuid4(), actor_role="super_admin")
    b = _make_booking(tenant_id=uuid.uuid4(), customer_id=uuid.uuid4())
    svc._assert_can_access_booking(b)  # Should not raise


# ══════════════════════════════════════════════════════════════════════════════
# 14-16: run_booking_preflight — job_type validation
# ══════════════════════════════════════════════════════════════════════════════

async def test_14_preflight_invalid_job_type():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException
    svc = BookingService(db=_make_db(), actor_role="customer")
    with pytest.raises(ServiceOSException) as exc_info:
        await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()),
            job_type="invalid_type",
        )
    assert exc_info.value.error_code == "INVALID_JOB_TYPE"


async def test_15_preflight_valid_job_types_pass_validation():
    """Valid job types: repair, service, consultation."""
    from app.engines.serviceability.constants import JOB_TYPES
    assert "repair" in JOB_TYPES
    assert "service" in JOB_TYPES
    assert "consultation" in JOB_TYPES


async def test_16_preflight_scheduled_at_in_past_raises():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException

    past_dt = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    svc = BookingService(db=_make_db(), actor_role="customer")

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mock_instance = AsyncMock()
        mock_instance._resolve_service_type_id = AsyncMock(
            return_value=("ac_service", "AC Service", "hvac"))
        MockSvc.return_value = mock_instance

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.run_booking_preflight(
                address_id=None, city="Mumbai", state="MH",
                zipcode="400001", service_id=str(uuid.uuid4()),
                job_type="repair", scheduled_at=past_dt,
            )
        assert exc_info.value.error_code == "SCHEDULED_TIME_IN_PAST"


# ══════════════════════════════════════════════════════════════════════════════
# 17-20: run_booking_preflight — service validation
# ══════════════════════════════════════════════════════════════════════════════

async def test_17_preflight_service_not_found_raises():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException

    svc = BookingService(db=_make_db(), actor_role="customer")

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        from app.exceptions import ServiceOSException as SE
        mock_instance = AsyncMock()
        mock_instance._resolve_service_type_id = AsyncMock(
            side_effect=SE("SERVICE_NOT_FOUND", "Not found", status_code=404))
        MockSvc.return_value = mock_instance

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.run_booking_preflight(
                address_id=None, city="Mumbai", state="MH",
                zipcode="400001", service_id=str(uuid.uuid4()),
                job_type="repair",
            )
        assert exc_info.value.error_code == "BOOKING_PREFLIGHT_FAILED"


async def test_18_preflight_no_city_raises_location_required():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException

    svc = BookingService(db=_make_db(), actor_role="customer")

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mock_instance = AsyncMock()
        mock_instance._resolve_service_type_id = AsyncMock(
            return_value=("ac_service", "AC Service", "hvac"))
        mock_instance._resolve_location_full = AsyncMock(
            return_value=(None, None, None, None, None, None))
        MockSvc.return_value = mock_instance

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.run_booking_preflight(
                address_id=None, city=None, state=None,
                zipcode=None, service_id=str(uuid.uuid4()),
                job_type="repair",
            )
        assert exc_info.value.error_code == "LOCATION_REQUIRED"


async def test_19_preflight_no_matches_returns_can_book_false():
    from app.engines.booking.service import BookingService

    svc = BookingService(db=_make_db(), actor_role="customer")

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mock_instance = AsyncMock()
        mock_instance._resolve_service_type_id = AsyncMock(
            return_value=("ac_service", "AC Service", "hvac"))
        mock_instance._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, None))
        mock_instance.match_tenants_for_location = AsyncMock(return_value=[])
        MockSvc.return_value = mock_instance

        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()),
            job_type="repair",
        )
    assert result["can_book"] is False
    assert result["reason_code"] == "SERVICE_NOT_AVAILABLE_IN_AREA"
    assert result["matched_count"] == 0


async def test_20_preflight_success_returns_can_book_true():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result()

    svc = BookingService(db=_make_db(), actor_role="customer")

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mock_instance = AsyncMock()
        mock_instance._resolve_service_type_id = AsyncMock(
            return_value=("ac_service", "AC Service", "hvac"))
        mock_instance._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, None))
        mock_instance.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mock_instance

        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()),
            job_type="repair",
        )
    assert result["can_book"] is True
    assert "matched_tenant_id" in result
    assert result["matched_tenant_id"] == matches[0]["tenant_id"]


# ══════════════════════════════════════════════════════════════════════════════
# 21-26: run_booking_preflight — result structure
# ══════════════════════════════════════════════════════════════════════════════

async def test_21_preflight_result_has_service_info():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result()
    svc = BookingService(db=_make_db(), actor_role="customer")
    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi
        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()), job_type="repair")
    assert result["service_type_id"] == "ac_service"
    assert result["service_name"] == "AC Service"
    assert result["service_category"] == "hvac"


async def test_22_preflight_result_has_pricing():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result()
    svc = BookingService(db=_make_db(), actor_role="customer")
    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi
        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()), job_type="repair")
    assert "price_breakdown" in result
    assert result["estimated_price"] == 800.0
    assert result["price_breakdown"]["base_price"] == 800.0
    assert result["price_breakdown"]["currency"] == "INR"


async def test_23_preflight_result_has_sla():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result()
    svc = BookingService(db=_make_db(), actor_role="customer")
    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi
        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()), job_type="repair")
    assert result["sla_minutes"] == 60


async def test_24_preflight_result_has_coverage_level():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result()
    svc = BookingService(db=_make_db(), actor_role="customer")
    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi
        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()), job_type="repair")
    assert result["coverage_match_level"] == "zipcode"
    assert result["coverage_rank"] == 1


async def test_25_preflight_result_has_matching_snapshot():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result()
    svc = BookingService(db=_make_db(), actor_role="customer")
    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi
        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()), job_type="repair")
    assert "matching_snapshot" in result
    assert isinstance(result["matching_snapshot"], list)
    assert len(result["matching_snapshot"]) == 1


async def test_26_preflight_result_has_available_matches_count():
    from app.engines.booking.service import BookingService
    matches = _mock_match_result() + _mock_match_result()  # 2 matches
    svc = BookingService(db=_make_db(), actor_role="customer")
    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi
        result = await svc.run_booking_preflight(
            address_id=None, city="Mumbai", state="MH",
            zipcode="400001", service_id=str(uuid.uuid4()), job_type="repair")
    assert result["available_matches_count"] == 2


# ══════════════════════════════════════════════════════════════════════════════
# 27-30: create_booking — validation
# ══════════════════════════════════════════════════════════════════════════════

async def test_27_create_booking_requires_address_service_jobtype():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException
    svc = BookingService(db=_make_db(), actor_role="customer")
    with pytest.raises(ServiceOSException) as exc_info:
        await svc.create_booking(
            customer_id=uuid.uuid4(),
            address_id=None, service_id=None, job_type=None,
        )
    assert exc_info.value.error_code == "VALIDATION_ERROR"


async def test_28_create_booking_sets_pending_confirmation_status():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    db = _make_db()

    matches = _mock_match_result()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}

        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        # Mock redis to avoid idempotency hit
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid,
            address_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            job_type="repair",
        )

    assert result["status"] == "pending_confirmation"


async def test_29_create_booking_stores_city():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    db = _make_db()
    matches = _mock_match_result()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid, address_id=uuid.uuid4(),
            service_id=uuid.uuid4(), job_type="repair")

    assert result["city"] == "Mumbai"


async def test_30_create_booking_stores_sla_minutes():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    db = _make_db()
    matches = _mock_match_result()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC Service", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid, address_id=uuid.uuid4(),
            service_id=uuid.uuid4(), job_type="repair")

    assert result["sla_minutes"] == 60


# ══════════════════════════════════════════════════════════════════════════════
# 31-33: create_booking — serviceability failures
# ══════════════════════════════════════════════════════════════════════════════

async def test_31_create_booking_service_not_found():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException
    cid = uuid.uuid4()
    db = _make_db()

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(
            side_effect=ServiceOSException("SERVICE_NOT_FOUND", "Not found", status_code=404))
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.create_booking(
                customer_id=cid, address_id=uuid.uuid4(),
                service_id=uuid.uuid4(), job_type="repair")

    assert exc_info.value.error_code == "SERVICE_NOT_FOUND"


async def test_32_create_booking_no_service_area():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException
    cid = uuid.uuid4()
    db = _make_db()

    with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, None))
        mi.match_tenants_for_location = AsyncMock(return_value=[])
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.create_booking(
                customer_id=cid, address_id=uuid.uuid4(),
                service_id=uuid.uuid4(), job_type="repair")

    assert exc_info.value.error_code == "SERVICE_NOT_AVAILABLE_IN_AREA"


async def test_33_create_booking_tenant_overridden_by_matching():
    """Booking stores the tenant from serviceability match, not any external input."""
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    expected_tenant_id = str(uuid.uuid4())
    matches = _mock_match_result(tenant_id=expected_tenant_id)
    db = _make_db()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid, address_id=uuid.uuid4(),
            service_id=uuid.uuid4(), job_type="repair")

    assert result["tenant_id"] == expected_tenant_id


# ══════════════════════════════════════════════════════════════════════════════
# 34-36: create_booking — booking dict has new fields
# ══════════════════════════════════════════════════════════════════════════════

async def test_34_create_booking_stores_matching_snapshot():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    matches = _mock_match_result()
    db = _make_db()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid, address_id=uuid.uuid4(),
            service_id=uuid.uuid4(), job_type="repair")

    assert "matching_snapshot" in result
    assert isinstance(result["matching_snapshot"], list)


async def test_35_create_booking_stores_estimated_price():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    matches = _mock_match_result()
    db = _make_db()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid, address_id=uuid.uuid4(),
            service_id=uuid.uuid4(), job_type="repair")

    assert result["estimated_price"] == 800.0


async def test_36_create_booking_stores_coverage_match_level():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    matches = _mock_match_result()
    db = _make_db()

    with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
               new_callable=AsyncMock) as mock_preflight, \
         patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc, \
         patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
         patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):

        mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                        "blocking_reason": None, "allowed_transitions": []}
        mi = AsyncMock()
        mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
        mi._resolve_location_full = AsyncMock(
            return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
        mi.match_tenants_for_location = AsyncMock(return_value=matches)
        MockSvc.return_value = mi

        svc = BookingService(db=db, actor_role="customer", actor_id=cid)
        svc.redis = AsyncMock()
        svc.redis.get = AsyncMock(return_value=None)
        svc.redis.setex = AsyncMock()

        result = await svc.create_booking(
            customer_id=cid, address_id=uuid.uuid4(),
            service_id=uuid.uuid4(), job_type="repair")

    assert result["coverage_match_level"] == "zipcode"


# ══════════════════════════════════════════════════════════════════════════════
# 37-38: get_booking — isolation
# ══════════════════════════════════════════════════════════════════════════════

async def test_37_get_booking_customer_sees_own():
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    b = _make_booking(customer_id=cid)
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=b)
    db.execute = AsyncMock(return_value=result_mock)

    svc = BookingService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_booking(b.id)
    assert result["booking_id"] == str(b.id)


async def test_38_get_booking_customer_cannot_see_other_booking():
    from app.engines.booking.service import BookingService
    from app.exceptions import NotFoundException
    b = _make_booking(customer_id=uuid.uuid4())
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=b)
    db.execute = AsyncMock(return_value=result_mock)

    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
    with pytest.raises(NotFoundException):
        await svc.get_booking(b.id)


# ══════════════════════════════════════════════════════════════════════════════
# 39-40: cancel_booking — isolation + terminal status
# ══════════════════════════════════════════════════════════════════════════════

async def test_39_cancel_booking_tenant_isolation():
    from app.engines.booking.service import BookingService
    from app.exceptions import NotFoundException
    tid = uuid.uuid4()
    b = _make_booking(tenant_id=uuid.uuid4())  # different tenant
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=b)
    db.execute = AsyncMock(return_value=result_mock)

    svc = BookingService(db=db, actor_id=uuid.uuid4(),
                         actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(NotFoundException):
        await svc.cancel_booking(b.id, "test reason")


async def test_40_cancel_booking_terminal_status_raises():
    from app.engines.booking.service import BookingService
    from app.exceptions import ServiceOSException
    cid = uuid.uuid4()
    b = _make_booking(status="completed", customer_id=cid)
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=b)
    db.execute = AsyncMock(return_value=result_mock)

    svc = BookingService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc_info:
        await svc.cancel_booking(b.id, "reason")
    assert exc_info.value.error_code == "BOOKING_CANNOT_BE_CANCELLED"


# ══════════════════════════════════════════════════════════════════════════════
# 41-42: list_bookings — role-scoped queries
# ══════════════════════════════════════════════════════════════════════════════

async def test_41_list_bookings_customer_scoped():
    """Customer list uses customer_id filter."""
    from app.engines.booking.service import BookingService
    cid = uuid.uuid4()
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock(return_value=result_mock)

    svc = BookingService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.list_bookings()
    assert result["bookings"] == []
    assert result["has_next"] is False


async def test_42_list_bookings_tenant_owner_scoped():
    """Tenant owner list uses actor_tenant_id filter."""
    from app.engines.booking.service import BookingService
    tid = uuid.uuid4()
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock(return_value=result_mock)

    svc = BookingService(db=db, actor_id=uuid.uuid4(),
                         actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.list_bookings()
    assert result["bookings"] == []


# ══════════════════════════════════════════════════════════════════════════════
# 43-44: _booking_dict — new fields present
# ══════════════════════════════════════════════════════════════════════════════

def test_43_booking_dict_includes_step4_fields():
    from app.engines.booking.service import BookingService
    svc = BookingService(db=_make_db(), actor_role="customer")
    b = _make_booking()
    d = svc._booking_dict(b)
    for field in ["city", "zipcode", "sla_minutes", "estimated_price", "final_price",
                  "matching_snapshot", "matched_service_area_service_id"]:
        assert field in d, f"_booking_dict missing field: {field}"


def test_44_booking_dict_zipcode_maps_to_pincode():
    """zipcode in API response maps to pincode column."""
    from app.engines.booking.service import BookingService
    svc = BookingService(db=_make_db(), actor_role="customer")
    b = _make_booking()
    b.pincode = "400088"
    d = svc._booking_dict(b)
    assert d["zipcode"] == "400088"
    assert d["pincode"] == "400088"
