"""Sprint 14 — Customer Category Flow Routing.

Tests CustomerCategoryFlowService at the service layer.
No real DB; no HTTP; asyncio_mode = "auto" via pyproject.toml.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.customer_flow.service import (
    CustomerCategoryFlowService,
    ERR_CAT_NOT_FOUND, ERR_CAT_NOT_VISIBLE, ERR_CAT_INACTIVE,
    ERR_CAT_FLOW_MISSING, ERR_OFFERING_NOT_FOUND, ERR_OFFERING_INACTIVE,
    ERR_FLOW_INVALID, ERR_FLOW_COMPONENT,
)
from app.engines.admin_catalog.models import (
    CustomerFlowConfig,
    MasterOffering,
    MasterService,
    ServiceCategory,
)
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)
_id = lambda: uuid.uuid4()


# ─── DB Mock helpers ─────────────────────────────────────────────────────────

def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    return r


def _scalars(lst):
    r = MagicMock()
    inner = MagicMock()
    inner.all.return_value = lst
    r.scalars.return_value = inner
    return r


def db_seq(*results):
    """Mock db returning each result in sequence across execute calls."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _cat(
    *,
    is_active=True,
    is_customer_visible=True,
    category_type="home_services",
    customer_flow_type="service_booking",
    frontend_component_key="ServiceBookingFlow",
    primary_engine_key="booking_engine",
    vertical_type="home_services",
    name="Plumbing",
    slug="plumbing",
):
    cat = MagicMock(spec=ServiceCategory)
    cat.id = _id()
    cat.name = name
    cat.slug = slug
    cat.description = "desc"
    cat.category_type = category_type
    cat.customer_flow_type = customer_flow_type
    cat.frontend_component_key = frontend_component_key
    cat.primary_engine_key = primary_engine_key
    cat.vertical_type = vertical_type
    cat.is_active = is_active
    cat.is_customer_visible = is_customer_visible
    cat.icon_url = None
    cat.banner_url = None
    cat.display_order = 1
    return cat


def _flow_cfg(cat_id, flow_type="service_booking", component="ServiceBookingFlow", active=True):
    cfg = MagicMock(spec=CustomerFlowConfig)
    cfg.id = _id()
    cfg.category_id = cat_id
    cfg.customer_flow_type = flow_type
    cfg.frontend_component_key = component
    cfg.primary_engine_key = "booking_engine"
    cfg.required_steps = ["select_offering", "address", "confirmation"]
    cfg.optional_steps = ["photo_upload"]
    cfg.config = {}
    cfg.is_active = active
    cfg.created_at = utcnow()
    cfg.updated_at = utcnow()
    return cfg


def _offering(cat_id, name="AC Repair", slug="ac-repair", status="active", is_active=True):
    o = MagicMock(spec=MasterOffering)
    o.id = _id()
    o.category_id = cat_id
    o.name = name
    o.slug = slug
    o.description = "desc"
    o.offering_class = "service"
    o.customer_flow_type = "service_booking"
    o.primary_engine_key = "booking_engine"
    o.status = status
    o.is_active = is_active
    o.is_type_required = True
    o.is_brand_required = True
    o.requires_address = True
    o.requires_slot = False
    o.requires_photo_upload = False
    o.requires_customer_notes = False
    o.default_pricing_model = "fixed"
    o.default_base_price = Decimal("500")
    o.default_visit_fee = Decimal("100")
    o.default_appointment_fee = Decimal("0")
    o.display_order = 1
    return o


def _master_service(cat_id, name="AC Repair", slug="ac-repair", is_active=True):
    service = MagicMock(spec=MasterService)
    service.id = _id()
    service.category_id = cat_id
    service.service_name = name
    service.slug = slug
    service.description = "desc"
    service.pricing_model = "fixed"
    service.base_price = Decimal("500")
    service.min_price = Decimal("450")
    service.visit_fee = Decimal("100")
    service.is_type_required = True
    service.is_brand_required = True
    service.requires_address = True
    service.requires_schedule = True
    service.is_active = is_active
    service.deleted_at = None
    service.display_order = 1
    return service


# ─── 1. list_customer_categories ─────────────────────────────────────────────

async def test_list_customer_categories_returns_items():
    cat = _cat()
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(3),       # total count
        _scalars([cat]),  # category rows
        _scalar(flow),    # flow config for cat
        _scalar(5),       # offering count for cat
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.list_customer_categories(page=1, page_size=20)
    assert result["total"] == 3
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["name"] == "Plumbing"
    assert item["customer_flow_type"] == "service_booking"
    assert item["available_offering_count"] == 5


async def test_list_customer_categories_empty():
    db = db_seq(
        _scalar(0),
        _scalars([]),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.list_customer_categories()
    assert result["total"] == 0
    assert result["items"] == []


async def test_list_customer_categories_pagination():
    cat = _cat()
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(50),
        _scalars([cat]),
        _scalar(flow),
        _scalar(2),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.list_customer_categories(page=3, page_size=1)
    assert result["page"] == 3
    assert result["page_size"] == 1


async def test_list_customer_categories_fallback_when_no_flow_config():
    cat = _cat(customer_flow_type="lead_capture", frontend_component_key="LeadCaptureFlow")
    db = db_seq(
        _scalar(1),
        _scalars([cat]),
        _scalar(None),   # no flow config
        _scalar(0),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.list_customer_categories()
    item = result["items"][0]
    assert item["customer_flow_type"] == "lead_capture"


# ─── 2. get_customer_category_detail ─────────────────────────────────────────

async def test_get_category_detail_by_slug():
    cat = _cat()
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(cat),    # by slug
        _scalar(flow),
        _scalar(3),
        _scalar(flow),   # second load in get_customer_category_detail
        _scalar(3),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.get_customer_category_detail("plumbing")
    assert result["name"] == "Plumbing"
    assert "required_steps" in result
    assert "optional_steps" in result


async def test_get_category_detail_not_found():
    db = db_seq(_scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_category_detail("nonexistent")
    assert exc.value.error_code == ERR_CAT_NOT_FOUND


async def test_get_category_detail_inactive():
    cat = _cat(is_active=False)
    db = db_seq(_scalar(cat))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_category_detail("plumbing")
    assert exc.value.error_code == ERR_CAT_INACTIVE


async def test_get_category_detail_not_visible():
    cat = _cat(is_customer_visible=False)
    db = db_seq(_scalar(cat))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_category_detail("plumbing")
    assert exc.value.error_code == ERR_CAT_NOT_VISIBLE


async def test_get_category_detail_no_flow_config():
    cat = _cat()
    db = db_seq(
        _scalar(cat),
        _scalar(None),   # no flow config → ERR_CAT_FLOW_MISSING
    )
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_category_detail("plumbing")
    assert exc.value.error_code == ERR_CAT_FLOW_MISSING


# ─── 3. get_customer_category_runtime ────────────────────────────────────────

async def test_get_category_runtime_returns_flow_info():
    cat = _cat()
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(cat),
        _scalar(flow),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.get_customer_category_runtime("plumbing")
    assert result["runtime"]["customer_flow_type"] == "service_booking"
    assert result["runtime"]["frontend_component_key"] == "ServiceBookingFlow"
    assert result["runtime"]["status"] == "ready"
    assert result["required_steps"] == flow.required_steps


async def test_get_category_runtime_inactive_flow_returns_inactive_status():
    cat = _cat()
    flow = _flow_cfg(cat.id, active=False)
    db = db_seq(
        _scalar(cat),
        _scalar(None),   # inactive flow config excluded by is_active=True filter
    )
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_category_runtime("plumbing")
    assert exc.value.error_code == ERR_CAT_FLOW_MISSING


# ─── 5. list_customer_offerings ──────────────────────────────────────────────

async def test_list_customer_offerings_returns_offerings():
    cat = _cat()
    o1 = _offering(cat.id, name="AC Repair", slug="ac-repair")
    o2 = _offering(cat.id, name="AC Service", slug="ac-service")
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(cat),            # load category
        _scalar(2),              # total count
        _scalars([o1, o2]),      # offerings
        _scalar(flow),           # flow config
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.list_customer_offerings("plumbing")
    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["name"] == "AC Repair"


async def test_list_customer_offerings_category_not_found():
    db = db_seq(_scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_customer_offerings("nonexistent")
    assert exc.value.error_code == ERR_CAT_NOT_FOUND


async def test_list_customer_offerings_falls_back_to_master_services():
    cat = _cat()
    service = _master_service(cat.id)
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(cat),
        _scalar(1),
        _scalars([]),
        _scalars([service]),
        _scalar(flow),
    )
    result = await CustomerCategoryFlowService(db=db).list_customer_offerings("plumbing")
    assert result["total"] == 1
    assert result["items"][0]["id"] == str(service.id)
    assert result["items"][0]["name"] == "AC Repair"
    assert result["items"][0]["requires_slot"] is True


# ─── 6. get_customer_offering_detail ─────────────────────────────────────────

async def test_get_offering_detail_returns_fields():
    cat = _cat()
    o = _offering(cat.id)
    flow = _flow_cfg(cat.id)
    db = db_seq(
        _scalar(cat),
        _scalar(o),
        _scalar(flow),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.get_customer_offering_detail("plumbing", "ac-repair")
    assert result["name"] == "AC Repair"
    assert "required_fields" in result
    assert result["required_fields"]["requires_address"] is True


async def test_get_offering_detail_inactive_offering():
    cat = _cat()
    o = _offering(cat.id, status="inactive")
    db = db_seq(_scalar(cat), _scalar(o))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_offering_detail("plumbing", "ac-repair")
    assert exc.value.error_code == ERR_OFFERING_INACTIVE


async def test_get_offering_detail_not_found():
    cat = _cat()
    db = db_seq(_scalar(cat), _scalar(None), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_offering_detail("plumbing", "nonexistent")
    assert exc.value.error_code == ERR_OFFERING_NOT_FOUND


async def test_get_offering_detail_falls_back_to_master_service():
    cat = _cat()
    service = _master_service(cat.id)
    flow = _flow_cfg(cat.id)
    db = db_seq(_scalar(cat), _scalar(None), _scalar(service), _scalar(flow))
    result = await CustomerCategoryFlowService(db=db).get_customer_offering_detail(
        "plumbing", "ac-repair"
    )
    assert result["id"] == str(service.id)
    assert result["name"] == "AC Repair"
    assert result["required_fields"]["requires_slot"] is True


# ─── 7. validate_category_customer_access ────────────────────────────────────

async def test_validate_category_access_valid():
    cat = _cat()
    db = db_seq(_scalar(cat))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.validate_category_customer_access("plumbing")
    assert result["valid"] is True
    assert result["name"] == "Plumbing"


async def test_validate_category_access_not_found_returns_invalid():
    db = db_seq(_scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.validate_category_customer_access("nonexistent")
    assert result["valid"] is False
    assert result["error_code"] == ERR_CAT_NOT_FOUND


async def test_validate_category_access_not_visible_returns_invalid():
    cat = _cat(is_customer_visible=False)
    db = db_seq(_scalar(cat))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.validate_category_customer_access("plumbing")
    assert result["valid"] is False
    assert result["error_code"] == ERR_CAT_NOT_VISIBLE


# ─── 8. validate_offering_customer_access ────────────────────────────────────

async def test_validate_offering_access_valid():
    cat = _cat()
    o = _offering(cat.id)
    db = db_seq(_scalar(cat), _scalar(o))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.validate_offering_customer_access("plumbing", "ac-repair")
    assert result["valid"] is True
    assert result["name"] == "AC Repair"


async def test_validate_offering_access_inactive():
    cat = _cat()
    o = _offering(cat.id, is_active=False)
    # is_active=False on offering - the query will return None from the DB filter
    db = db_seq(_scalar(cat), _scalar(None), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.validate_offering_customer_access("plumbing", "ac-repair")
    assert result["valid"] is False
    assert result["error_code"] == ERR_OFFERING_NOT_FOUND


# ─── 9. resolve_frontend_flow_component ──────────────────────────────────────

async def test_resolve_flow_component_from_flow_config():
    cat_id = _id()
    flow = _flow_cfg(cat_id, component="ServiceBookingFlow")
    db = db_seq(_scalar(flow))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.resolve_frontend_flow_component(cat_id)
    assert result == "ServiceBookingFlow"


async def test_resolve_flow_component_fallback_to_unsupported():
    cat_id = _id()
    db = db_seq(_scalar(None), _scalar(None))  # no flow config, no customer_flow_type
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.resolve_frontend_flow_component(cat_id)
    assert result == "UnsupportedFlow"


async def test_resolve_flow_component_from_category_type():
    cat_id = _id()
    db = db_seq(_scalar(None), _scalar("appointment_booking"))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.resolve_frontend_flow_component(cat_id)
    assert result == "AppointmentBookingFlow"


# ─── resolve_flow (POST /v1/customer/flow/resolve) ───────────────────────────

async def test_resolve_flow_returns_full_context():
    cat = _cat()
    flow = _flow_cfg(cat.id)
    avail_result = _scalar(0)  # provider_visibility_statuses count
    db = db_seq(
        _scalar(cat),
        _scalar(flow),
        avail_result,
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.resolve_flow(category_slug="plumbing")
    assert result["category"]["slug"] == "plumbing"
    assert result["flow"]["customer_flow_type"] == "service_booking"
    assert result["flow"]["frontend_component_key"] == "ServiceBookingFlow"
    assert "availability" in result


async def test_resolve_flow_missing_flow_config_raises():
    cat = _cat()
    db = db_seq(_scalar(cat), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.resolve_flow(category_slug="plumbing")
    assert exc.value.error_code == ERR_CAT_FLOW_MISSING


# ─── admin CRUD ──────────────────────────────────────────────────────────────

async def test_admin_get_flow_config_returns_config():
    cat_id = _id()
    flow = _flow_cfg(cat_id)
    db = db_seq(_scalar(flow))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.admin_get_flow_config(cat_id)
    assert result["customer_flow_type"] == "service_booking"
    assert result["is_active"] is True


async def test_admin_get_flow_config_not_found_raises():
    cat_id = _id()
    db = db_seq(_scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_get_flow_config(cat_id)
    assert exc.value.error_code == ERR_CAT_FLOW_MISSING


async def test_admin_upsert_creates_new_config():
    cat_id = _id()
    cat = _cat()
    cat.id = cat_id
    db = db_seq(
        _scalar(cat),     # load category for vertical guard
        _scalar(None),    # no existing flow config
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.admin_upsert_flow_config(cat_id, {
        "customer_flow_type": "service_booking",
        "frontend_component_key": "ServiceBookingFlow",
        "primary_engine_key": "booking_engine",
        "required_steps": ["step1"],
        "is_active": True,
    })
    db.add.assert_called_once()
    assert result["customer_flow_type"] == "service_booking"


async def test_admin_upsert_rejects_invalid_flow_type():
    cat_id = _id()
    cat = _cat()
    cat.id = cat_id
    db = db_seq(_scalar(cat), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_upsert_flow_config(cat_id, {"customer_flow_type": "INVALID_TYPE"})
    assert exc.value.error_code == ERR_FLOW_INVALID


async def test_admin_upsert_rejects_invalid_component_key():
    cat_id = _id()
    cat = _cat()
    cat.id = cat_id
    db = db_seq(_scalar(cat), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_upsert_flow_config(cat_id, {"frontend_component_key": "BadComponent"})
    assert exc.value.error_code == ERR_FLOW_COMPONENT


async def test_admin_upsert_rejects_mismatched_component_for_flow():
    cat_id = _id()
    cat = _cat(vertical_type="coaching", customer_flow_type="appointment_booking")
    cat.id = cat_id
    db = db_seq(_scalar(cat), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_upsert_flow_config(cat_id, {
            "customer_flow_type": "appointment_booking",
            "frontend_component_key": "ServiceBookingFlow",
            "primary_engine_key": "appointment_engine",
        })
    assert exc.value.error_code == ERR_FLOW_COMPONENT


async def test_admin_upsert_rejects_mismatched_engine_for_flow():
    cat_id = _id()
    cat = _cat(vertical_type="coaching", customer_flow_type="appointment_booking")
    cat.id = cat_id
    db = db_seq(_scalar(cat), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_upsert_flow_config(cat_id, {
            "customer_flow_type": "appointment_booking",
            "frontend_component_key": "AppointmentBookingFlow",
            "primary_engine_key": "booking_engine",
        })
    assert exc.value.error_code == ERR_FLOW_INVALID


async def test_admin_upsert_rejects_non_service_booking_for_home_services():
    cat_id = _id()
    cat = _cat(vertical_type="home_services")
    cat.id = cat_id
    db = db_seq(_scalar(cat), _scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_upsert_flow_config(cat_id, {
            "customer_flow_type": "appointment_booking",
            "frontend_component_key": "AppointmentBookingFlow",
            "primary_engine_key": "appointment_engine",
        })
    assert exc.value.error_code == ERR_FLOW_INVALID


async def test_admin_get_flow_config_can_read_inactive_config():
    cat_id = _id()
    flow = _flow_cfg(cat_id, active=False)
    db = db_seq(_scalar(flow))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.admin_get_flow_config(cat_id)
    assert result["is_active"] is False


async def test_admin_upsert_updates_existing_config():
    cat_id = _id()
    existing_flow = _flow_cfg(cat_id, flow_type="lead_capture", component="LeadCaptureFlow")
    cat = _cat()
    cat.id = cat_id
    db = db_seq(
        _scalar(cat),
        _scalar(existing_flow),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.admin_upsert_flow_config(cat_id, {
        "customer_flow_type": "service_booking",
        "frontend_component_key": "ServiceBookingFlow",
    })
    assert existing_flow.customer_flow_type == "service_booking"


async def test_admin_activate_flow_config():
    cat_id = _id()
    flow = _flow_cfg(cat_id, active=False)
    db = db_seq(_scalar(flow))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.admin_activate_flow_config(cat_id)
    assert flow.is_active is True
    assert result["activated"] is True


async def test_admin_deactivate_flow_config():
    cat_id = _id()
    flow = _flow_cfg(cat_id, active=True)
    db = db_seq(_scalar(flow))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.admin_deactivate_flow_config(cat_id)
    assert flow.is_active is False
    assert result["deactivated"] is True


async def test_admin_activate_not_found_raises():
    cat_id = _id()
    db = db_seq(_scalar(None))
    svc = CustomerCategoryFlowService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_activate_flow_config(cat_id)
    assert exc.value.error_code == ERR_CAT_FLOW_MISSING


# ─── search ──────────────────────────────────────────────────────────────────

async def test_search_returns_categories_and_offerings():
    cat = _cat(name="Plumbing Pro")
    o = _offering(_id(), name="Pipe Repair", slug="pipe-repair")
    db = db_seq(
        _scalars([cat]),   # category matches
        _scalars([o]),     # offering matches
        _scalars([]),      # master service matches
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.search("plumb")
    assert len(result["categories"]) == 1
    assert result["categories"][0]["name"] == "Plumbing Pro"
    assert result["query"] == "plumb"


async def test_search_empty_query_returns_empty():
    db = db_seq(
        _scalars([]),
        _scalars([]),
        _scalars([]),
    )
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.search("xyz_no_match")
    assert result["categories"] == []
    assert result["offerings"] == []


# ─── 10. get_category_provider_availability_summary ──────────────────────────

async def test_provider_availability_summary_with_count():
    cat_id = _id()
    db = db_seq(_scalar(5))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.get_category_provider_availability_summary(cat_id)
    assert result["available_provider_count"] == 5
    assert result["is_available"] is True


async def test_provider_availability_summary_zero():
    cat_id = _id()
    db = db_seq(_scalar(0))
    svc = CustomerCategoryFlowService(db=db)
    result = await svc.get_category_provider_availability_summary(cat_id)
    assert result["is_available"] is False
