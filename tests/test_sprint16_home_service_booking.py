"""Sprint 16 — Home Service Chatbot Booking Flow tests.

Tests HomeServiceChatbotBookingService, HomeServiceServiceabilityService,
provider matching, and constants. No real DB, no HTTP — all mocked.
asyncio_mode = 'auto' via pyproject.toml.
"""
import uuid
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.engines.home_service_booking.serviceability_service import HomeServiceServiceabilityService
from app.engines.home_service_booking.provider_matching import find_bookable_home_service_providers
from app.engines.home_service_booking.constants import (
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_COLLECTING_DETAILS,
    DRAFT_STATUS_SERVICEABILITY_CHECKED,
    DRAFT_STATUS_PRICE_ESTIMATED,
    DRAFT_STATUS_PROVIDER_MATCHED,
    DRAFT_STATUS_READY_FOR_CONFIRMATION,
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_EXPIRED,
    SVCABILITY_SERVICEABLE,
    SVCABILITY_NOT_SERVICEABLE,
    SVCABILITY_PENDING,
    PRICE_STATUS_ESTIMATED,
    PRICE_STATUS_PENDING,
    PROVIDER_MATCH_MATCHED,
    PROVIDER_MATCH_NO_PROVIDER,
    PROVIDER_MATCH_PENDING,
    TERMINAL_STATUSES,
    ERR_DRAFT_NOT_FOUND,
    ERR_DRAFT_ACCESS_DENIED,
    ERR_DRAFT_TERMINAL,
    ERR_CATEGORY_INVALID,
    ERR_OFFERING_INVALID,
    ERR_ADDRESS_REQUIRED,
    ERR_NO_PROVIDER_AVAILABLE,
    ERR_CONFIRMATION_NOT_READY,
    ERR_PHOTO_UPLOAD_FAILED,
    ERR_REQUIRED_FIELD_MISSING,
    ALLOWED_PHOTO_TYPES,
    DRAFT_MAX_PHOTOS,
)
from app.engines.home_service_booking.models import (
    HomeServiceBookingDraft,
    HomeServiceBookingDraftEvent,
)
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)
_id    = lambda: uuid.uuid4()


# ──────────────────────────────────────────────────────────────────────────────
# Mock helpers (same pattern as sprint 15 tests)
# ──────────────────────────────────────────────────────────────────────────────

def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    return r


def _scalars(lst):
    r = MagicMock()
    inner = MagicMock()
    inner.all.return_value = lst
    inner.first.return_value = lst[0] if lst else None
    r.scalars.return_value = inner
    return r


def db_seq(*results):
    """Mock db that returns results in sequence across execute calls."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add     = MagicMock()
    db.flush   = AsyncMock()
    db.commit  = AsyncMock()
    db.refresh = AsyncMock()
    db.get     = AsyncMock()
    return db


def _make_category(name="Home Services", slug="home-services"):
    cat = MagicMock()
    cat.id   = _id()
    cat.name = name
    cat.slug = slug
    cat.is_active = True
    cat.is_customer_visible = True
    cat.commission_pct = None       # unset -> platform default
    cat.customer_charge_pct = None  # unset -> no customer charge
    return cat


def _make_offering(
    name="AC Repair",
    slug="ac-repair",
    is_type_required=False,
    is_brand_required=False,
    requires_slot=False,
    pricing_model="visit_fee_plus_quote",
    visit_fee=Decimal("399"),
    base_price=Decimal("0"),
):
    # HS7 fix: start_booking_draft/_get_offering now resolve against the
    # real, populated MasterService table instead of the empty legacy
    # MasterOffering table (see service.py). Field names updated to match:
    # name->service_name, requires_slot->requires_schedule,
    # default_*->bare field names (no `default_` prefix on MasterService).
    o = MagicMock()
    o.id           = _id()
    o.service_name = name
    o.slug         = slug
    o.is_active             = True
    o.is_type_required      = is_type_required
    o.is_brand_required     = is_brand_required
    o.requires_schedule     = requires_slot
    o.requires_photo_upload = False
    o.requires_customer_notes = False
    o.requires_address      = True
    o.pricing_model         = pricing_model
    o.visit_fee              = visit_fee
    o.base_price              = base_price
    o.min_price              = visit_fee
    o.max_price              = None
    return o


def _make_draft(
    status=DRAFT_STATUS_DRAFT,
    city="Ludhiana",
    zipcode="141001",
    issue_summary="AC not cooling",
    svc_status=SVCABILITY_PENDING,
    price_status=PRICE_STATUS_PENDING,
    provider_match_status=PROVIDER_MATCH_PENDING,
    customer_id=None,
):
    d = MagicMock(spec=HomeServiceBookingDraft)
    d.id                    = _id()
    d.customer_id           = customer_id or _id()
    d.ai_session_id         = None
    d.category_id           = _id()
    d.offering_id           = _id()
    d.job_type_id           = None
    d.selected_tenant_id    = None
    d.status                = status
    d.customer_name         = "Test Customer"
    d.customer_phone        = "+919876543210"
    d.address_id            = None
    d.address_snapshot      = None
    d.city                  = city
    d.zipcode               = zipcode
    d.issue_summary         = issue_summary
    d.issue_details         = None
    d.offering_type_id      = None
    d.brand_id              = None
    d.photo_urls            = []
    d.preferred_date        = None
    d.preferred_time_window = None
    d.serviceability_status = svc_status
    d.price_status          = price_status
    d.provider_match_status = provider_match_status
    d.pricing_rule_id       = None
    d.price_snapshot        = None
    d.provider_options      = []
    d.selected_provider_snapshot = None
    d.booking_summary       = None
    d.failure_code          = None
    d.failure_message       = None
    d.expires_at            = utcnow() + timedelta(hours=24)
    d.created_at            = utcnow()
    d.updated_at            = utcnow()
    d.to_dict.return_value  = {"id": str(d.id), "status": status}
    return d


# ──────────────────────────────────────────────────────────────────────────────
# 1. CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_terminal_statuses_are_closed(self):
        assert DRAFT_STATUS_CONFIRMED  in TERMINAL_STATUSES
        assert DRAFT_STATUS_CANCELLED  in TERMINAL_STATUSES
        assert DRAFT_STATUS_EXPIRED    in TERMINAL_STATUSES

    def test_allowed_photo_types(self):
        assert "image/jpeg" in ALLOWED_PHOTO_TYPES
        assert "image/png"  in ALLOWED_PHOTO_TYPES
        assert "image/webp" in ALLOWED_PHOTO_TYPES
        assert "image/gif"  not in ALLOWED_PHOTO_TYPES

    def test_max_photos(self):
        assert DRAFT_MAX_PHOTOS == 5


# ──────────────────────────────────────────────────────────────────────────────
# 2. MODELS
# ──────────────────────────────────────────────────────────────────────────────

class TestModels:
    def test_draft_to_dict_returns_all_keys(self):
        draft = HomeServiceBookingDraft()
        draft.id                     = _id()
        draft.customer_id            = _id()
        draft.ai_session_id          = None
        draft.category_id            = _id()
        draft.offering_id            = _id()
        draft.selected_tenant_id     = None
        draft.status                 = DRAFT_STATUS_DRAFT
        draft.customer_name          = "Alice"
        draft.customer_phone         = "+919999999999"
        draft.address_id             = None
        draft.address_snapshot       = None
        draft.city                   = "Ludhiana"
        draft.zipcode                = "141001"
        draft.issue_summary          = "AC leaking"
        draft.issue_details          = None
        draft.offering_type_id       = None
        draft.brand_id               = None
        draft.photo_urls             = []
        draft.preferred_date         = None
        draft.preferred_time_window  = None
        draft.serviceability_status  = SVCABILITY_PENDING
        draft.price_status           = PRICE_STATUS_PENDING
        draft.provider_match_status  = PROVIDER_MATCH_PENDING
        draft.pricing_rule_id        = None
        draft.price_snapshot         = None
        draft.provider_options       = []
        draft.selected_provider_snapshot = None
        draft.booking_summary        = None
        draft.failure_code           = None
        draft.failure_message        = None
        draft.expires_at             = utcnow() + timedelta(hours=24)
        draft.created_at             = utcnow()
        draft.updated_at             = utcnow()
        d = draft.to_dict()
        assert d["status"] == DRAFT_STATUS_DRAFT
        assert d["city"] == "Ludhiana"
        assert d["zipcode"] == "141001"
        assert d["photo_urls"] == []
        assert "id" in d

    def test_event_to_dict(self):
        evt = HomeServiceBookingDraftEvent()
        evt.id         = _id()
        evt.draft_id   = _id()
        evt.actor_type = "backend"
        evt.event_type = "price_estimated"
        evt.old_value  = None
        evt.new_value  = {"price": "399"}
        evt.message    = "Price estimated: ₹399"
        evt.request_id = "req-123"
        evt.created_at = utcnow()
        d = evt.to_dict()
        assert d["actor_type"] == "backend"
        assert d["event_type"] == "price_estimated"
        assert d["message"] == "Price estimated: ₹399"


# ──────────────────────────────────────────────────────────────────────────────
# 3. START BOOKING DRAFT
# ──────────────────────────────────────────────────────────────────────────────

class TestStartBookingDraft:
    @pytest.fixture(autouse=True)
    def _enabled_home_services_vertical(self):
        vertical = MagicMock(is_enabled=True)
        with patch("app.dependencies.vertical_guard._load_vertical", AsyncMock(return_value=vertical)):
            yield

    async def test_start_draft_invalid_category(self):
        """Category slug not found → ERR_CATEGORY_INVALID."""
        db = db_seq(_scalars([]))   # category not found
        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.start_booking_draft(
                customer_id=_id(), ai_session_id=None,
                category_slug="invalid-cat", offering_slug="ac-repair",
            )
        assert exc_info.value.error_code == ERR_CATEGORY_INVALID

    async def test_start_draft_invalid_offering(self):
        """Offering slug not found under valid category → ERR_OFFERING_INVALID."""
        cat = _make_category()
        not_found = MagicMock()
        not_found.scalars.return_value.first.return_value = None

        db = MagicMock()
        db.execute = AsyncMock(side_effect=[
            _scalars([cat]),   # category found
            not_found,         # offering not found
        ])
        db.add    = MagicMock()
        db.flush  = AsyncMock()
        db.commit = AsyncMock()

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.start_booking_draft(
                customer_id=_id(), ai_session_id=None,
                category_slug="home-services", offering_slug="nonexistent",
            )
        assert exc_info.value.error_code == ERR_OFFERING_INVALID

    async def test_start_draft_success(self):
        """Valid category + offering → draft created, returned with required_fields."""
        cat      = _make_category()
        offering = _make_offering()
        cat.id   = _id()
        offering.category_id = cat.id

        db = MagicMock()
        db.execute = AsyncMock(side_effect=[
            _scalars([cat]),
            _scalars([offering]),
            # Added later this phase: start_booking_draft now independently
            # re-checks (a) at least one tenant has actually published this
            # offering, and (b) it has real problem/issue-type wiring,
            # before allowing a draft to be created -- both must resolve
            # truthy here for this "happy path" test to reach draft
            # creation. Then the customer-address auto-fill lookup (may
            # legitimately find nothing -- empty is fine, it's optional).
            _scalars([MagicMock()]),  # has_publisher: truthy
            _scalars([MagicMock()]),  # has_problems: truthy
            _scalar(0),               # active booking drafts: below cap
            _scalars([]),             # customer's default address: none found
            _scalars([]),             # no job-type dimension rules
        ])
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        # After flush, make refresh set to_dict
        async def fake_refresh(obj):
            if isinstance(obj, HomeServiceBookingDraft):
                obj.id          = _id()
                obj.status      = DRAFT_STATUS_DRAFT
                obj.category_id = cat.id
                obj.offering_id = offering.id
                obj.created_at  = utcnow()
                obj.updated_at  = utcnow()
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.start_booking_draft(
            customer_id=_id(), ai_session_id=None,
            category_slug="home-services", offering_slug="ac-repair",
        )
        assert db.add.called
        assert db.commit.called
        assert "required_fields" in result

    async def test_start_draft_non_home_service_rejected(self):
        """Offering from a different category is rejected."""
        cat = _make_category(name="Food", slug="food")

        db = MagicMock()
        db.execute = AsyncMock(side_effect=[
            _scalars([cat]),      # wrong category returned for slug mismatch
            _scalars([]),         # no offering under food/ac-repair
        ])
        db.add    = MagicMock()
        db.flush  = AsyncMock()
        db.commit = AsyncMock()

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.start_booking_draft(
                customer_id=_id(), ai_session_id=None,
                category_slug="food", offering_slug="ac-repair",
            )
        assert exc_info.value.error_code == ERR_OFFERING_INVALID


# ──────────────────────────────────────────────────────────────────────────────
# 4. DRAFT ACCESS CONTROL
# ──────────────────────────────────────────────────────────────────────────────

class TestDraftAccessControl:
    async def test_customer_cannot_access_another_customers_draft(self):
        """Draft owned by customer_A — customer_B gets access denied."""
        owner_id  = _id()
        other_id  = _id()
        draft = _make_draft(customer_id=owner_id)

        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.get_booking_draft(draft_id=draft.id, customer_id=other_id)
        assert exc_info.value.error_code == ERR_DRAFT_ACCESS_DENIED

    async def test_draft_not_found_raises(self):
        db = MagicMock()
        db.get = AsyncMock(return_value=None)
        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.get_booking_draft(draft_id=_id(), customer_id=_id())
        assert exc_info.value.error_code == ERR_DRAFT_NOT_FOUND

    async def test_admin_can_access_any_draft(self):
        """admin_get_draft has no ownership check."""
        draft = _make_draft()
        offering = _make_offering()
        cat      = _make_category()
        draft.offering_id = offering.id
        draft.category_id = cat.id

        db = MagicMock()
        db.get     = AsyncMock(side_effect=[draft, offering, cat])
        db.execute = AsyncMock()

        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.admin_get_draft(draft_id=draft.id)
        assert result is not None


# ──────────────────────────────────────────────────────────────────────────────
# 5. UPDATE DRAFT FIELDS
# ──────────────────────────────────────────────────────────────────────────────

class TestUpdateDraftFields:
    async def test_update_changes_status_to_collecting(self):
        """Updating any field transitions status to collecting_details."""
        customer_id = _id()
        draft       = _make_draft(customer_id=customer_id)

        db = MagicMock()
        db.get     = AsyncMock(return_value=draft)
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars([]))

        offering = _make_offering()
        db.get   = AsyncMock(side_effect=[draft, offering, _make_category()])

        async def fake_refresh(obj):
            obj.status = DRAFT_STATUS_COLLECTING_DETAILS
            obj.to_dict.return_value = {"id": str(obj.id), "status": DRAFT_STATUS_COLLECTING_DETAILS}
        db.refresh.side_effect = fake_refresh

        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.update_draft_fields(
            draft_id=draft.id, customer_id=customer_id,
            payload={"city": "Ludhiana", "zipcode": "141001"},
        )
        assert draft.city == "Ludhiana"
        assert draft.zipcode == "141001"

    async def test_terminal_draft_cannot_be_updated(self):
        """Cancelled draft rejects field updates."""
        customer_id = _id()
        draft       = _make_draft(status=DRAFT_STATUS_CANCELLED, customer_id=customer_id)

        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.update_draft_fields(
                draft_id=draft.id, customer_id=customer_id,
                payload={"city": "Mumbai"},
            )
        assert exc_info.value.error_code == ERR_DRAFT_TERMINAL


# ──────────────────────────────────────────────────────────────────────────────
# 6. VALIDATE REQUIRED FIELDS
# ──────────────────────────────────────────────────────────────────────────────

class TestRequiredFields:
    async def test_missing_type_when_required(self):
        """offering.is_type_required=True + no offering_type_id → type missing."""
        customer_id = _id()
        draft    = _make_draft(customer_id=customer_id, issue_summary="AC not working")
        draft.offering_type_id = None
        offering = _make_offering(is_type_required=True)
        offering.id = draft.offering_id

        db = MagicMock()
        db.get = AsyncMock(side_effect=[draft, offering])

        svc     = HomeServiceChatbotBookingService(db=db)
        missing = await svc.get_missing_fields(draft_id=draft.id, customer_id=customer_id)
        assert "offering_type_id" in missing

    async def test_missing_brand_when_required(self):
        """offering.is_brand_required=True + no brand_id → brand missing."""
        customer_id = _id()
        draft    = _make_draft(customer_id=customer_id)
        draft.brand_id = None
        offering = _make_offering(is_brand_required=True)
        offering.id = draft.offering_id

        db = MagicMock()
        db.get = AsyncMock(side_effect=[draft, offering])

        svc     = HomeServiceChatbotBookingService(db=db)
        missing = await svc.get_missing_fields(draft_id=draft.id, customer_id=customer_id)
        assert "brand_id" in missing

    async def test_no_missing_fields_when_complete(self):
        """All required fields present → empty missing list."""
        customer_id = _id()
        draft       = _make_draft(customer_id=customer_id, issue_summary="AC leaking")
        draft.city  = "Ludhiana"
        offering    = _make_offering(is_type_required=False, is_brand_required=False)
        offering.id = draft.offering_id

        db = MagicMock()
        db.get = AsyncMock(side_effect=[draft, offering])

        svc     = HomeServiceChatbotBookingService(db=db)
        missing = await svc.get_missing_fields(draft_id=draft.id, customer_id=customer_id)
        assert missing == []

    async def test_city_required_for_serviceability(self):
        """No city → check_serviceability raises ERR_ADDRESS_REQUIRED."""
        customer_id  = _id()
        draft        = _make_draft(customer_id=customer_id, city=None)
        draft.city   = None

        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.check_serviceability(draft_id=draft.id, customer_id=customer_id)
        assert exc_info.value.error_code == ERR_ADDRESS_REQUIRED


# ──────────────────────────────────────────────────────────────────────────────
# 7. SERVICEABILITY CHECK
# ──────────────────────────────────────────────────────────────────────────────

class TestServiceabilityCheck:
    async def test_serviceable_when_providers_in_zipcode(self):
        """Provider covers city+zipcode → serviceable=True, matched_by=zipcode."""
        cat      = _make_category()
        offering = _make_offering()

        svc_db = MagicMock()
        svc_db.execute = AsyncMock(side_effect=[
            _scalars([cat]),        # category check
            _scalars([offering]),   # offering check
            _scalar(2),             # zipcode count = 2
        ])

        svc = HomeServiceServiceabilityService(db=svc_db)
        result = await svc.check(
            category_id=cat.id,
            offering_id=offering.id,
            city="Ludhiana",
            zipcode="141001",
        )
        assert result["serviceable"] is True
        assert result["matched_by"]  == "zipcode"
        assert result["available_provider_count"] == 2

    async def test_not_serviceable_when_no_providers(self):
        """No provider covers city → serviceable=False."""
        cat      = _make_category()
        offering = _make_offering()

        svc_db = MagicMock()
        svc_db.execute = AsyncMock(side_effect=[
            _scalars([cat]),
            _scalars([offering]),
            _scalar(0),   # zipcode count = 0
            _scalar(0),   # city count = 0
        ])

        svc = HomeServiceServiceabilityService(db=svc_db)
        result = await svc.check(
            category_id=cat.id,
            offering_id=offering.id,
            city="Unknown City",
            zipcode="999999",
        )
        assert result["serviceable"] is False
        assert result["available_provider_count"] == 0

    async def test_city_match_when_no_zipcode_match(self):
        """Zipcode=0 but city=3 → serviceable=True, matched_by=city."""
        cat      = _make_category()
        offering = _make_offering()

        svc_db = MagicMock()
        svc_db.execute = AsyncMock(side_effect=[
            _scalars([cat]),
            _scalars([offering]),
            _scalar(0),   # zipcode count = 0
            _scalar(3),   # city count = 3
        ])

        svc = HomeServiceServiceabilityService(db=svc_db)
        result = await svc.check(
            category_id=cat.id,
            offering_id=offering.id,
            city="Mumbai",
            zipcode="400001",
        )
        assert result["serviceable"] is True
        assert result["matched_by"] == "city"

    async def test_inactive_category_not_serviceable(self):
        """Inactive category → not serviceable."""
        svc_db = MagicMock()
        not_found = MagicMock()
        not_found.scalars.return_value.first.return_value = None
        svc_db.execute = AsyncMock(return_value=not_found)

        svc = HomeServiceServiceabilityService(db=svc_db)
        result = await svc.check(
            category_id=_id(), offering_id=_id(), city="Mumbai",
        )
        assert result["serviceable"] is False
        assert result["reason_code"] is not None


# ──────────────────────────────────────────────────────────────────────────────
# 8. PRICE ESTIMATE
# ──────────────────────────────────────────────────────────────────────────────

class TestPriceEstimate:
    async def test_price_estimate_from_backend_catalog(self):
        """Price comes from offering defaults + city tier. Frontend price ignored."""
        customer_id = _id()
        draft       = _make_draft(
            customer_id=customer_id,
            city="Ludhiana",
            zipcode="141001",
        )
        offering    = _make_offering(visit_fee=Decimal("399"))
        cat         = _make_category()
        draft.offering_id = offering.id
        draft.category_id = cat.id

        # City tier floor < visit fee so offering default wins
        city_floor = MagicMock()
        city_floor.floor_price = Decimal("200")
        city_floor.tier        = "tier_2"

        db = MagicMock()
        db.get     = AsyncMock(side_effect=[draft, offering, cat])
        db.execute = AsyncMock(return_value=_scalars([city_floor]))
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        async def fake_refresh(obj):
            obj.price_status = PRICE_STATUS_ESTIMATED
            obj.price_snapshot = {"display_price": "₹399"}
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.resolve_price_estimate(draft_id=draft.id, customer_id=customer_id)
        assert result["price_snapshot"]["display_price"] == "₹399"
        assert draft.price_status == PRICE_STATUS_ESTIMATED

    async def test_frontend_price_is_never_used(self):
        """Payload with 'price' field is ignored; backend price is used."""
        customer_id = _id()
        draft       = _make_draft(customer_id=customer_id, city="Ludhiana")
        offering    = _make_offering(visit_fee=Decimal("399"))
        cat         = _make_category()
        draft.offering_id = offering.id
        draft.category_id = cat.id

        db = MagicMock()
        db.get     = AsyncMock(side_effect=[draft, offering, cat])
        db.execute = AsyncMock(return_value=_scalars([]))   # no city tier
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        async def fake_refresh(obj):
            obj.price_status   = PRICE_STATUS_ESTIMATED
            obj.price_snapshot = {"display_price": "₹399", "source": "backend_catalog"}
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.resolve_price_estimate(draft_id=draft.id, customer_id=customer_id)
        assert result["price_snapshot"]["source"] == "backend_catalog"

    async def test_city_floor_raises_price_when_above_default(self):
        """City floor price > visit fee → floor price used."""
        customer_id = _id()
        draft       = _make_draft(customer_id=customer_id, city="Mumbai")
        offering    = _make_offering(visit_fee=Decimal("200"), pricing_model="fixed", base_price=Decimal("200"))
        cat         = _make_category()
        draft.offering_id = offering.id
        draft.category_id = cat.id

        city_floor  = MagicMock()
        city_floor.floor_price = Decimal("500")
        city_floor.tier        = "tier_1"

        db = MagicMock()
        db.get     = AsyncMock(side_effect=[draft, offering, cat])
        db.execute = AsyncMock(return_value=_scalars([city_floor]))
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        async def fake_refresh(obj):
            obj.price_status   = PRICE_STATUS_ESTIMATED
            obj.price_snapshot = {"display_price": "₹500", "base_price": 500}
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.resolve_price_estimate(draft_id=draft.id, customer_id=customer_id)
        assert result["price_snapshot"]["base_price"] == 500


# ──────────────────────────────────────────────────────────────────────────────
# 9. PROVIDER MATCHING
# ──────────────────────────────────────────────────────────────────────────────

class TestProviderMatching:
    async def test_returns_only_bookable_providers(self):
        """Provider matching returns only active tenants with service areas."""
        cat_id       = _id()
        offering_id  = _id()
        customer_id  = _id()
        tenant_id    = _id()

        # Simulate provider row
        provider_row = MagicMock()
        provider_row.tenant_id     = tenant_id
        provider_row.business_name = "Rahul AC Services"
        provider_row.tenant_name   = "Rahul AC Services"
        provider_row.logo_url      = None
        provider_row.health_score  = Decimal("95.0")
        provider_row.rating        = Decimal("4.5")
        provider_row.area_zipcode  = "141001"
        provider_row.area_city     = "Ludhiana"

        db = MagicMock()
        zipcode_result = MagicMock()
        zipcode_result.all.return_value = [provider_row]
        db.execute = AsyncMock(return_value=zipcode_result)

        providers = await find_bookable_home_service_providers(
            db=db, category_id=cat_id, offering_id=offering_id,
            city="Ludhiana", zipcode="141001",
        )
        assert len(providers) >= 1
        assert providers[0]["business_name"] == "Rahul AC Services"
        assert providers[0]["is_bookable"] is True
        compiled = str(db.execute.await_args.args[0].compile())
        assert "provider_visibility_statuses" in compiled
        assert "is_bookable" in compiled

    async def test_provider_without_area_excluded(self):
        """No matching provider rows → empty list."""
        db = MagicMock()
        empty_result = MagicMock()
        empty_result.all.return_value = []
        db.execute = AsyncMock(return_value=empty_result)

        providers = await find_bookable_home_service_providers(
            db=db, category_id=_id(), offering_id=_id(),
            city="Timbuktu", zipcode="000000",
        )
        assert providers == []
        # A supplied zipcode is authoritative. Do not run a second city-only
        # query that could expose a provider outside the customer's zipcode.
        assert db.execute.await_count == 1

    async def test_no_provider_available_raises(self):
        """No bookable providers → ERR_NO_PROVIDER_AVAILABLE."""
        customer_id = _id()
        draft       = _make_draft(
            customer_id=customer_id, city="Timbuktu", zipcode="000000",
        )

        db = MagicMock()
        db.get     = AsyncMock(return_value=draft)
        empty_result = MagicMock()
        empty_result.all.return_value = []
        db.execute = AsyncMock(return_value=empty_result)
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.find_bookable_providers(draft_id=draft.id, customer_id=customer_id)
        assert exc_info.value.error_code == ERR_NO_PROVIDER_AVAILABLE
        assert "ZIP code 000000" in exc_info.value.detail

    async def test_provider_fields_are_customer_safe(self):
        """Provider options must NOT include internal IDs or commission."""
        cat_id   = _id()
        tenant_id = _id()
        row = MagicMock()
        row.tenant_id     = tenant_id
        row.business_name = "Safe Services"
        row.tenant_name   = "Safe Services"
        row.logo_url      = None
        row.health_score  = Decimal("80")
        row.rating        = Decimal("4.0")
        row.area_zipcode  = "141001"
        row.area_city     = "Ludhiana"

        db = MagicMock()
        result = MagicMock()
        result.all.return_value = [row]
        db.execute = AsyncMock(return_value=result)

        providers = await find_bookable_home_service_providers(
            db=db, category_id=cat_id, offering_id=_id(),
            city="Ludhiana", zipcode="141001",
        )
        assert len(providers) == 1
        p = providers[0]
        # provider_ref is present (opaque ref) but no internal-only fields
        assert "provider_ref" in p
        assert "commission"        not in p
        assert "credit_balance"    not in p
        assert "subscription_status" not in p


# ──────────────────────────────────────────────────────────────────────────────
# 10. BOOKING SUMMARY
# ──────────────────────────────────────────────────────────────────────────────

class TestBookingSummary:
    async def test_summary_built_after_required_fields_complete(self):
        """All fields present, provider matched, price tier chosen →
        booking_summary returned with ready_for_confirmation.

        HS7 fix: ready_for_confirmation now reflects the real
        provider-first flow (selected_tenant_id set + a price tier
        already confirmed via confirm_price_choice), not the legacy flat
        price_status flag — a draft with a resolved flat price estimate
        but no matched provider/chosen tier was never actually
        confirmable through the real customer flow.
        """
        customer_id = _id()
        draft = _make_draft(
            customer_id=customer_id,
            city="Ludhiana",
            zipcode="141001",
            issue_summary="AC not cooling",
            svc_status=SVCABILITY_SERVICEABLE,
            price_status=PRICE_STATUS_ESTIMATED,
        )
        draft.price_snapshot = {"display_price": "₹399", "note": "Visit fee"}
        draft.selected_provider_snapshot = {"business_name": "Rahul AC"}
        draft.selected_tenant_id = _id()
        draft.booking_summary = {"selected_price_tier": "standard"}
        # Phase 2A.2: ready_for_confirmation now also requires a resolved,
        # still-valid Job Type context -- short-circuit that check here
        # since this test is about the pre-existing price/provider summary
        # logic, not job-type resolution (covered by its own tests).
        draft.job_type_id = _id()
        offering = _make_offering()
        offering.id = draft.offering_id
        cat = _make_category()
        cat.id = draft.category_id

        db = MagicMock()
        db.get     = AsyncMock(side_effect=[draft, offering, offering, cat])
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        async def fake_refresh(obj):
            obj.booking_summary = {
                "offering_name": "AC Repair",
                "ready_for_confirmation": True,
            }
            obj.to_dict.return_value = {
                "id": str(obj.id),
                "status": draft.status,
                "booking_summary": obj.booking_summary,
            }
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        with patch.object(svc, "_validate_job_type_context", AsyncMock(return_value=None)), \
             patch.object(svc, "_emergency_surcharge_for", AsyncMock(return_value=None)):
            result = await svc.build_booking_summary(draft_id=draft.id, customer_id=customer_id)
        assert "booking_summary" in result
        assert result["booking_summary"]["ready_for_confirmation"] is True


# ──────────────────────────────────────────────────────────────────────────────
# 11. CONFIRM DRAFT
# ──────────────────────────────────────────────────────────────────────────────

class TestConfirmDraft:
    async def test_confirm_blocked_if_not_ready(self):
        """Draft in price_estimated (not ready_for_confirmation) → ERR_CONFIRMATION_NOT_READY."""
        customer_id = _id()
        draft = _make_draft(
            customer_id=customer_id,
            status=DRAFT_STATUS_PRICE_ESTIMATED,
        )
        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.confirm_draft(draft_id=draft.id, customer_id=customer_id)
        assert exc_info.value.error_code == ERR_CONFIRMATION_NOT_READY

    async def test_confirm_returns_booking_ready_payload(self):
        """Ready draft confirmed → booking_ready_payload returned, no job created."""
        customer_id = _id()
        tenant_id   = _id()
        draft = _make_draft(
            customer_id=customer_id,
            status=DRAFT_STATUS_READY_FOR_CONFIRMATION,
            svc_status=SVCABILITY_SERVICEABLE,
            price_status=PRICE_STATUS_ESTIMATED,
        )
        draft.selected_tenant_id    = tenant_id
        draft.price_snapshot        = {"display_price": "₹399"}
        draft.address_snapshot      = {"city": "Ludhiana"}
        draft.issue_summary         = "AC not cooling"

        db = MagicMock()
        db.get     = AsyncMock(return_value=draft)
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        # FINAL-L5-04C: confirm_draft() looks up the draft's offering's
        # service_group_id to re-validate entitlement; this synthetic draft's
        # offering_id doesn't correspond to a real MasterService row, so the
        # real query would return None (no group -> entitlement check is
        # skipped, the correct behavior for offerings with no group) —
        # simulate that here rather than leaving db.execute unmocked.
        from types import SimpleNamespace
        billing_result = MagicMock()
        billing_result.fetchone.return_value = SimpleNamespace(
            credit_balance=1000, entitled_seats=1,
        )
        policy_result = MagicMock()
        policy_result.fetchone.return_value = SimpleNamespace(
            credit_booking_floor=0, credit_warning_threshold=100,
            seat_accrual_mode="purchased",
        )
        offering_result = MagicMock()
        offering_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[
            billing_result, policy_result, offering_result,
        ])

        async def fake_refresh(obj):
            obj.status = DRAFT_STATUS_CONFIRMED
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.confirm_draft(draft_id=draft.id, customer_id=customer_id)
        assert result["success"] is True
        payload = result["data"]["booking_ready_payload"]
        assert payload["tenant_id"] == str(tenant_id)
        assert "price_snapshot" in payload
        assert "address_snapshot" in payload
        # Confirm no job/booking was created
        assert result["data"]["next_step"] == "final_booking_creation_in_sprint_19"

    async def test_confirmed_draft_cannot_be_cancelled(self):
        """Confirmed draft in terminal status → cancel is a no-op (already closed)."""
        customer_id = _id()
        draft = _make_draft(customer_id=customer_id, status=DRAFT_STATUS_CONFIRMED)

        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.cancel_draft(draft_id=draft.id, customer_id=customer_id)
        assert result["draft_status"] == DRAFT_STATUS_CONFIRMED


# ──────────────────────────────────────────────────────────────────────────────
# 12. CANCEL DRAFT
# ──────────────────────────────────────────────────────────────────────────────

class TestCancelDraft:
    async def test_cancel_active_draft(self):
        """Active draft → cancelled."""
        customer_id = _id()
        draft = _make_draft(customer_id=customer_id, status=DRAFT_STATUS_COLLECTING_DETAILS)

        db = MagicMock()
        db.get     = AsyncMock(return_value=draft)
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.cancel_draft(
            draft_id=draft.id, customer_id=customer_id, reason="Changed my mind"
        )
        assert result["draft_status"] == DRAFT_STATUS_CANCELLED
        assert draft.status == DRAFT_STATUS_CANCELLED


# ──────────────────────────────────────────────────────────────────────────────
# 13. PHOTO UPLOAD
# ──────────────────────────────────────────────────────────────────────────────

class TestPhotoUpload:
    async def test_invalid_file_type_rejected(self):
        """GIF file type rejected → ERR_PHOTO_UPLOAD_FAILED."""
        customer_id = _id()
        draft = _make_draft(customer_id=customer_id)
        draft.photo_urls = []

        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.add_photo(
                draft_id=draft.id, customer_id=customer_id,
                photo_url="https://example.com/photo.gif",
                content_type="image/gif",
            )
        assert exc_info.value.error_code == ERR_PHOTO_UPLOAD_FAILED

    async def test_max_photos_enforced(self):
        """6th photo rejected (max = 5)."""
        customer_id = _id()
        draft = _make_draft(customer_id=customer_id)
        draft.photo_urls = [f"https://example.com/p{i}.jpg" for i in range(5)]

        db = MagicMock()
        db.get = AsyncMock(return_value=draft)

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.add_photo(
                draft_id=draft.id, customer_id=customer_id,
                photo_url="https://example.com/extra.jpg",
                content_type="image/jpeg",
            )
        assert exc_info.value.error_code == ERR_PHOTO_UPLOAD_FAILED

    async def test_valid_photo_added(self):
        """Valid JPEG photo appended to photo_urls."""
        customer_id = _id()
        draft = _make_draft(customer_id=customer_id)
        draft.photo_urls = []

        db = MagicMock()
        db.get     = AsyncMock(return_value=draft)
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()

        async def fake_refresh(obj):
            obj.photo_urls = ["https://example.com/photo.jpg"]
        db.refresh.side_effect = fake_refresh

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.add_photo(
            draft_id=draft.id, customer_id=customer_id,
            photo_url="https://example.com/photo.jpg",
            content_type="image/jpeg",
        )
        assert len(result["photo_urls"]) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 14. EXPIRE OLD DRAFTS
# ──────────────────────────────────────────────────────────────────────────────

class TestExpireOldDrafts:
    async def test_expired_drafts_marked(self):
        """Drafts past expires_at are set to DRAFT_STATUS_EXPIRED."""
        draft = _make_draft(status=DRAFT_STATUS_COLLECTING_DETAILS)
        draft.expires_at = utcnow() - timedelta(minutes=1)

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([draft]))
        db.add     = MagicMock()
        db.flush   = AsyncMock()
        db.commit  = AsyncMock()

        svc   = HomeServiceChatbotBookingService(db=db)
        count = await svc.expire_old_drafts()
        assert count == 1
        assert draft.status == DRAFT_STATUS_EXPIRED


# ──────────────────────────────────────────────────────────────────────────────
# 15. ADMIN LISTING
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminListing:
    async def test_admin_list_drafts(self):
        """Admin list returns drafts with pagination."""
        draft1 = _make_draft()
        draft2 = _make_draft(status=DRAFT_STATUS_CONFIRMED)

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([draft1, draft2]))

        svc    = HomeServiceChatbotBookingService(db=db)
        result = await svc.admin_list_drafts(page=1, page_size=20)
        assert len(result["drafts"]) == 2
        assert result["page"] == 1

    async def test_admin_get_draft_events(self):
        """Events returned in order."""
        draft_id = _id()
        evt1 = MagicMock(spec=HomeServiceBookingDraftEvent)
        evt1.id         = _id()
        evt1.draft_id   = draft_id
        evt1.actor_type = "backend"
        evt1.event_type = "draft_created"
        evt1.old_value  = None
        evt1.new_value  = {}
        evt1.message    = "Draft created"
        evt1.request_id = None
        evt1.created_at = utcnow()
        evt1.to_dict.return_value = {"event_type": "draft_created"}

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([evt1]))

        svc    = HomeServiceChatbotBookingService(db=db)
        events = await svc.admin_get_draft_events(draft_id=draft_id)
        assert len(events) == 1
        assert events[0]["event_type"] == "draft_created"
