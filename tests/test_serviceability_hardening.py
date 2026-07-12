"""
Step 2 — Customer Address + Tenant Service Area Foundation.

The data model and most endpoints already existed as the "Serviceability
Engine" (Phase 21/22). This suite hardens and proves the foundation pieces
required by Step 2: address CRUD + default-address logic + ownership
isolation, tenant service-area CRUD + coverage validation + duplicate
prevention + tenant isolation, service-area-to-service mapping CRUD +
validation + isolation, OpenAPI completeness, and the new indexes from
migration 023.

Explicitly NOT covered here (out of scope per Step 2 — left untouched):
matching/serviceability-check, booking preflight, dispatch, pricing calc.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.serviceability.service import ServiceabilityService
from app.engines.serviceability.models import (
    CustomerAddress, TenantServiceArea, TenantServiceAreaService,
)
from app.engines.serviceability.constants import (
    ERR_ADDRESS_NOT_FOUND, ERR_INVALID_ZIPCODE, ERR_INVALID_CITY,
    ERR_SERVICE_NOT_FOUND, ERR_SERVICE_NOT_ACTIVE, ERR_AREA_NOT_FOUND,
    ERR_DUPLICATE_AREA, ERR_INVALID_COVERAGE, ERR_ZIPCODE_REQUIRED,
    ERR_CITY_REQUIRED, ERR_ZONE_REQUIRED, ERR_RADIUS_REQUIRED,
    ERR_MAPPING_NOT_FOUND, ERR_DUPLICATE_MAPPING, ERR_INVALID_JOB_TYPE,
    ERR_INVALID_PRICE_RANGE, ERR_INVALID_SLA,
)


def make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def result(scalar_one_or_none=None, scalars_all=None, scalar_one=None, scalars_first=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_one_or_none
    r.scalar_one.return_value = scalar_one
    r.scalars.return_value.all.return_value = scalars_all or []
    r.scalars.return_value.first.return_value = scalars_first
    return r


def address_payload(**overrides):
    data = dict(
        address_line_1="221B Baker Street", city="Mumbai", state="Maharashtra",
        zipcode="400001", is_default=False,
    )
    data.update(overrides)
    return data


def area_payload(**overrides):
    data = dict(
        coverage_type="city", state="Maharashtra", city="Mumbai",
        country="India", priority=100, is_active=True,
    )
    data.update(overrides)
    return data


def mapping_payload(**overrides):
    data = dict(service_id=str(uuid.uuid4()), job_type="repair", is_available=True)
    data.update(overrides)
    return data


# ══════════════════════════════════════════════════════════════════════════
# 1-11 — Customer Addresses: CRUD, default logic, isolation
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_01_first_address_is_auto_default():
    db = make_db()
    customer_id = uuid.uuid4()
    db.execute.return_value = result(scalar_one=0)  # no existing active addresses
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    out = await svc.create_address(customer_id, None, address_payload())
    assert out["is_default"] is True


@pytest.mark.asyncio
async def test_02_second_address_not_default_unless_requested():
    db = make_db()
    customer_id = uuid.uuid4()
    db.execute.return_value = result(scalar_one=1)  # one existing active address already
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    out = await svc.create_address(customer_id, None, address_payload())
    assert out["is_default"] is False


@pytest.mark.asyncio
async def test_03_create_address_with_is_default_clears_other_defaults():
    db = make_db()
    customer_id = uuid.uuid4()
    existing_default = CustomerAddress(customer_id=customer_id, is_default=True, is_active=True,
                                        address_line_1="x", city="Pune", state="MH", zipcode="411001")
    db.execute.return_value = result(scalars_all=[existing_default])
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    out = await svc.create_address(customer_id, None, address_payload(is_default=True))
    assert out["is_default"] is True
    assert existing_default.is_default is False


@pytest.mark.asyncio
async def test_04_create_address_requires_zipcode():
    db = make_db()
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_address(uuid.uuid4(), None, address_payload(zipcode=""))
    assert exc.value.error_code == ERR_INVALID_ZIPCODE


@pytest.mark.asyncio
async def test_05_create_address_requires_city():
    db = make_db()
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_address(uuid.uuid4(), None, address_payload(city=""))
    assert exc.value.error_code == ERR_INVALID_CITY


@pytest.mark.asyncio
async def test_06_list_addresses_returns_only_active():
    db = make_db()
    customer_id = uuid.uuid4()
    active = CustomerAddress(customer_id=customer_id, is_active=True, city="Pune",
                              state="MH", zipcode="411001", address_line_1="a")
    db.execute.return_value = result(scalars_all=[active])
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    out = await svc.list_addresses(customer_id)
    assert out["total"] == 1


@pytest.mark.asyncio
async def test_07_get_address_not_found_raises_404():
    db = make_db()
    db.get.return_value = None
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_address_dict(uuid.uuid4())
    assert exc.value.error_code == ERR_ADDRESS_NOT_FOUND
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_08_get_address_cross_customer_access_denied_as_not_found():
    """Ownership-hiding convention: cross-customer access looks like 404, not 403."""
    db = make_db()
    owner_id = uuid.uuid4()
    other_customer_id = uuid.uuid4()
    addr = CustomerAddress(id=uuid.uuid4(), customer_id=owner_id, is_active=True,
                            city="Pune", state="MH", zipcode="411001", address_line_1="a")
    db.get.return_value = addr
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=other_customer_id)
    with pytest.raises(NotFoundException):
        await svc.get_address_dict(addr.id)


@pytest.mark.asyncio
async def test_09_update_address_setting_default_clears_others():
    db = make_db()
    customer_id = uuid.uuid4()
    addr = CustomerAddress(id=uuid.uuid4(), customer_id=customer_id, is_active=True, is_default=False,
                            city="Pune", state="MH", zipcode="411001", address_line_1="a")
    other_default = CustomerAddress(customer_id=customer_id, is_default=True, is_active=True,
                                     city="Mumbai", state="MH", zipcode="400001", address_line_1="b")
    db.get.return_value = addr
    db.execute.return_value = result(scalars_all=[other_default])
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    out = await svc.update_address(addr.id, {"is_default": True})
    assert out["is_default"] is True
    assert other_default.is_default is False


@pytest.mark.asyncio
async def test_10_delete_address_soft_deletes():
    db = make_db()
    customer_id = uuid.uuid4()
    addr = CustomerAddress(id=uuid.uuid4(), customer_id=customer_id, is_active=True, is_default=False,
                            city="Pune", state="MH", zipcode="411001", address_line_1="a")
    db.get.return_value = addr
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    out = await svc.delete_address(addr.id)
    assert out["deleted"] is True
    assert addr.is_active is False


@pytest.mark.asyncio
async def test_11_delete_default_address_reassigns_new_default():
    db = make_db()
    customer_id = uuid.uuid4()
    addr = CustomerAddress(id=uuid.uuid4(), customer_id=customer_id, is_active=True, is_default=True,
                            city="Pune", state="MH", zipcode="411001", address_line_1="a")
    next_addr = CustomerAddress(id=uuid.uuid4(), customer_id=customer_id, is_active=True, is_default=False,
                                 city="Mumbai", state="MH", zipcode="400001", address_line_1="b")
    db.get.return_value = addr
    db.execute.return_value = result(scalars_first=next_addr)
    svc = ServiceabilityService(db=db, actor_role="customer", actor_id=customer_id)

    await svc.delete_address(addr.id)
    assert next_addr.is_default is True


# ══════════════════════════════════════════════════════════════════════════
# 12-25 — Tenant Service Areas: CRUD, coverage validation, duplicate
#          prevention, tenant isolation
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_12_create_service_area_city_coverage_success():
    db = make_db()
    tenant_id = uuid.uuid4()
    # no duplicate; no TenantLimits row (defaults to 5); 0 existing areas
    db.execute.return_value = result(scalar_one_or_none=None, scalar_one=0)
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.create_service_area(tenant_id, area_payload())
    assert out["coverage_type"] == "city"
    assert out["city"] == "Mumbai"


@pytest.mark.asyncio
async def test_13_city_coverage_requires_city_and_state():
    db = make_db()
    tenant_id = uuid.uuid4()
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload(city=""))
    assert exc.value.error_code == ERR_CITY_REQUIRED


@pytest.mark.asyncio
async def test_14_zipcode_coverage_requires_zipcode():
    db = make_db()
    tenant_id = uuid.uuid4()
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload(coverage_type="zipcode"))
    assert exc.value.error_code == ERR_ZIPCODE_REQUIRED


@pytest.mark.asyncio
async def test_15_zone_coverage_requires_zone_id_or_zone_name():
    db = make_db()
    tenant_id = uuid.uuid4()
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload(coverage_type="zone"))
    assert exc.value.error_code == ERR_ZONE_REQUIRED


@pytest.mark.asyncio
async def test_16_radius_coverage_requires_lat_lng_radius():
    db = make_db()
    tenant_id = uuid.uuid4()
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload(coverage_type="radius"))
    assert exc.value.error_code == ERR_RADIUS_REQUIRED


@pytest.mark.asyncio
async def test_17_invalid_coverage_type_rejected():
    db = make_db()
    tenant_id = uuid.uuid4()
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload(coverage_type="planet"))
    assert exc.value.error_code == ERR_INVALID_COVERAGE


@pytest.mark.asyncio
async def test_18_duplicate_city_coverage_rejected():
    db = make_db()
    tenant_id = uuid.uuid4()
    existing = TenantServiceArea(tenant_id=tenant_id, coverage_type="city", city="Mumbai",
                                  state="MH", is_active=True)
    db.execute.return_value = result(scalar_one_or_none=existing)
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload())
    assert exc.value.error_code == ERR_DUPLICATE_AREA


@pytest.mark.asyncio
async def test_19_duplicate_zone_coverage_rejected():
    db = make_db()
    tenant_id = uuid.uuid4()
    zone_id = uuid.uuid4()
    existing = TenantServiceArea(tenant_id=tenant_id, coverage_type="zone", zone_id=zone_id,
                                  state="MH", city="Mumbai", is_active=True)
    db.execute.return_value = result(scalar_one_or_none=existing)
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_area(tenant_id, area_payload(coverage_type="zone", zone_id=str(zone_id)))
    assert exc.value.error_code == ERR_DUPLICATE_AREA


@pytest.mark.asyncio
async def test_20_create_service_area_persists_zone_id():
    db = make_db()
    tenant_id = uuid.uuid4()
    zone_id = uuid.uuid4()
    db.execute.return_value = result(scalar_one_or_none=None, scalar_one=0)
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.create_service_area(
        tenant_id, area_payload(coverage_type="zone", zone_id=str(zone_id), zone_name="North Zone"))
    assert out["zone_id"] == str(zone_id)


@pytest.mark.asyncio
async def test_21_update_service_area_changed_coverage_revalidates():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = TenantServiceArea(id=uuid.uuid4(), tenant_id=tenant_id, coverage_type="city",
                              city="Mumbai", state="MH", is_active=True)
    db.get.return_value = area
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    with pytest.raises(ServiceOSException) as exc:
        await svc.update_service_area(area.id, {"coverage_type": "zipcode"})
    assert exc.value.error_code == ERR_ZIPCODE_REQUIRED


@pytest.mark.asyncio
async def test_22_update_service_area_duplicate_check_excludes_self():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = TenantServiceArea(id=uuid.uuid4(), tenant_id=tenant_id, coverage_type="city",
                              city="Mumbai", state="MH", is_active=True)
    db.get.return_value = area
    db.execute.return_value = result(scalar_one_or_none=None)  # no OTHER duplicate found
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.update_service_area(area.id, {"priority": 50})
    assert out["priority"] == 50


@pytest.mark.asyncio
async def test_23_list_service_areas_tenant_owner_cross_tenant_denied():
    db = make_db()
    own_tenant = uuid.uuid4()
    other_tenant = uuid.uuid4()
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=own_tenant)
    with pytest.raises(NotFoundException):
        await svc.list_service_areas(other_tenant)


@pytest.mark.asyncio
async def test_24_get_service_area_cross_tenant_denied_as_not_found():
    db = make_db()
    own_tenant = uuid.uuid4()
    other_tenant = uuid.uuid4()
    area = TenantServiceArea(id=uuid.uuid4(), tenant_id=other_tenant, coverage_type="city",
                              city="Mumbai", state="MH", is_active=True)
    db.get.return_value = area
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=own_tenant)
    with pytest.raises(NotFoundException):
        await svc.get_service_area_dict(area.id)


@pytest.mark.asyncio
async def test_25_deactivate_service_area_cascades_disable_mappings():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = TenantServiceArea(id=uuid.uuid4(), tenant_id=tenant_id, coverage_type="city",
                              city="Mumbai", state="MH", is_active=True)
    mapping = TenantServiceAreaService(tenant_service_area_id=area.id, tenant_id=tenant_id,
                                        service_id=uuid.uuid4(), job_type="repair", is_available=True)
    db.get.return_value = area
    db.execute.return_value = result(scalars_all=[mapping])
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.deactivate_service_area(area.id)
    assert out["deactivated"] is True
    assert area.is_active is False
    assert mapping.is_available is False


# ══════════════════════════════════════════════════════════════════════════
# 26-35 — Service Area ↔ Service mappings: CRUD, validation, isolation
# ══════════════════════════════════════════════════════════════════════════

def _area(tenant_id, area_id=None):
    return TenantServiceArea(id=area_id or uuid.uuid4(), tenant_id=tenant_id,
                              coverage_type="city", city="Mumbai", state="MH", is_active=True)


@pytest.mark.asyncio
async def test_26_add_service_mapping_success():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    active_service = MagicMock(is_active=True)
    db.get.side_effect = [area, active_service]
    db.execute.return_value = result(scalar_one_or_none=None)  # no dup
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.add_service_mapping(area.id, mapping_payload())
    assert out["job_type"] == "repair"
    assert out["is_available"] is True


@pytest.mark.asyncio
async def test_27_add_service_mapping_service_not_found():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    db.get.side_effect = [area, None]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.add_service_mapping(area.id, mapping_payload())
    assert exc.value.error_code == ERR_SERVICE_NOT_FOUND


@pytest.mark.asyncio
async def test_28_add_service_mapping_service_not_active():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    inactive_service = MagicMock(is_active=False)
    db.get.side_effect = [area, inactive_service]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.add_service_mapping(area.id, mapping_payload())
    assert exc.value.error_code == ERR_SERVICE_NOT_ACTIVE


@pytest.mark.asyncio
async def test_29_add_service_mapping_invalid_job_type():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    db.get.side_effect = [area]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.add_service_mapping(area.id, mapping_payload(job_type="haircut"))
    assert exc.value.error_code == ERR_INVALID_JOB_TYPE


@pytest.mark.asyncio
async def test_30_add_service_mapping_invalid_sla():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    db.get.side_effect = [area]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.add_service_mapping(area.id, mapping_payload(sla_minutes=0))
    assert exc.value.error_code == ERR_INVALID_SLA


@pytest.mark.asyncio
async def test_31_add_service_mapping_invalid_price_range():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    db.get.side_effect = [area]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.add_service_mapping(area.id, mapping_payload(min_price=500, max_price=100))
    assert exc.value.error_code == ERR_INVALID_PRICE_RANGE


@pytest.mark.asyncio
async def test_32_add_service_mapping_duplicate_active_rejected():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    active_service = MagicMock(is_active=True)
    existing_mapping = MagicMock()
    db.get.side_effect = [area, active_service]
    db.execute.return_value = result(scalar_one_or_none=existing_mapping)
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.add_service_mapping(area.id, mapping_payload())
    assert exc.value.error_code == ERR_DUPLICATE_MAPPING


@pytest.mark.asyncio
async def test_33_update_service_mapping_validates_changed_fields():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    mapping = TenantServiceAreaService(id=uuid.uuid4(), tenant_service_area_id=area.id,
                                        tenant_id=tenant_id, service_id=uuid.uuid4(),
                                        job_type="repair", is_available=True, sla_minutes=60)
    db.get.side_effect = [area, mapping]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_service_mapping(area.id, mapping.id, {"sla_minutes": -10})
    assert exc.value.error_code == ERR_INVALID_SLA


@pytest.mark.asyncio
async def test_34_delete_service_mapping_soft_disables():
    db = make_db()
    tenant_id = uuid.uuid4()
    area = _area(tenant_id)
    mapping = TenantServiceAreaService(id=uuid.uuid4(), tenant_service_area_id=area.id,
                                        tenant_id=tenant_id, service_id=uuid.uuid4(),
                                        job_type="repair", is_available=True)
    db.get.side_effect = [area, mapping]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.delete_service_mapping(area.id, mapping.id)
    assert out["deleted"] is True
    assert mapping.is_available is False


@pytest.mark.asyncio
async def test_35_service_mapping_cross_tenant_denied_as_not_found():
    db = make_db()
    own_tenant = uuid.uuid4()
    other_tenant = uuid.uuid4()
    area = _area(other_tenant)
    db.get.side_effect = [area]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=own_tenant)
    with pytest.raises(NotFoundException):
        await svc.list_service_mappings(area.id)


# ══════════════════════════════════════════════════════════════════════════
# Admin / tenant_owner read access to customer addresses
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_36_admin_super_admin_has_full_address_access():
    db = make_db()
    customer_id = uuid.uuid4()
    addr = CustomerAddress(id=uuid.uuid4(), customer_id=customer_id, is_active=True,
                            city="Pune", state="MH", zipcode="411001", address_line_1="a")
    db.execute.return_value = result(scalars_all=[addr])
    svc = ServiceabilityService(db=db, actor_role="super_admin")

    out = await svc.admin_list_addresses(customer_id)
    assert out["total"] == 1


@pytest.mark.asyncio
async def test_37_admin_tenant_owner_denied_without_booking_or_job_connection():
    db = make_db()
    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    db.execute.side_effect = [result(scalar_one=0), result(scalar_one=0)]  # no booking, no job
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    with pytest.raises(NotFoundException):
        await svc.admin_list_addresses(customer_id)


@pytest.mark.asyncio
async def test_38_admin_tenant_owner_allowed_with_booking_connection():
    db = make_db()
    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    addr = CustomerAddress(id=uuid.uuid4(), customer_id=customer_id, is_active=True,
                            city="Pune", state="MH", zipcode="411001", address_line_1="a")
    db.execute.side_effect = [result(scalar_one=1), result(scalars_all=[addr])]
    svc = ServiceabilityService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

    out = await svc.admin_list_addresses(customer_id)
    assert out["total"] == 1


@pytest.mark.asyncio
async def test_39_admin_staff_and_customer_roles_blocked():
    db = make_db()
    for role in ("staff", "customer"):
        svc = ServiceabilityService(db=db, actor_role=role)
        with pytest.raises(NotFoundException):
            await svc.admin_list_addresses(uuid.uuid4())


# ══════════════════════════════════════════════════════════════════════════
# OpenAPI completeness
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_40_openapi_includes_customer_address_endpoints():
    from app.main import app
    spec = app.openapi()
    paths = spec["paths"]
    assert "/v1/customers/me/addresses" in paths
    assert "/v1/customers/me/addresses/{address_id}" in paths
    assert "/v1/admin/customers/{customer_id}/addresses" in paths


@pytest.mark.asyncio
async def test_41_openapi_includes_tenant_service_area_endpoints():
    from app.main import app
    spec = app.openapi()
    paths = spec["paths"]
    assert "/v1/tenant/service-areas" in paths
    assert "/v1/tenant/service-areas/{area_id}/services" in paths
    assert "/v1/admin/tenants/{tenant_id}/service-areas" in paths


@pytest.mark.asyncio
async def test_42_openapi_error_codes_registered():
    from app.schemas.base import ERROR_CODES
    for code in (
        "CUSTOMER_ADDRESS_NOT_FOUND", "CUSTOMER_ADDRESS_ACCESS_DENIED",
        "TENANT_SERVICE_AREA_NOT_FOUND", "DUPLICATE_SERVICE_AREA",
        "ZONE_REQUIRED_FOR_ZONE_COVERAGE", "RADIUS_FIELDS_REQUIRED",
        "DUPLICATE_SERVICE_AREA_SERVICE", "INVALID_JOB_TYPE",
        "INVALID_PRICE_RANGE", "INVALID_SLA_MINUTES",
    ):
        assert code in ERROR_CODES, f"{code} missing from ERROR_CODES registry"


# ══════════════════════════════════════════════════════════════════════════
# Migration 023 — new indexes
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_43_customer_address_model_declares_default_address_unique_index():
    names = {ix.name for ix in CustomerAddress.__table__.indexes}
    assert "uq_ca_one_default_active" in names
    ix = next(i for i in CustomerAddress.__table__.indexes if i.name == "uq_ca_one_default_active")
    assert ix.unique is True


@pytest.mark.asyncio
async def test_44_service_area_mapping_model_declares_active_mapping_unique_index():
    names = {ix.name for ix in TenantServiceAreaService.__table__.indexes}
    assert "uq_tsas_active_mapping" in names
    assert "ix_tsas_tenant_service_job" in names
