"""Real, isolated SQL persistence tests for type-specific supported brands."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import JSON, MetaData, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.engines.admin_catalog.models import (
    Brand, MasterServiceBrand, MasterServiceType, ServiceType,
    TenantServiceBrand, TenantServiceType,
)
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.exceptions import ServiceOSException


@pytest.fixture
def catalog():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    for model in (Brand, MasterServiceBrand, MasterServiceType, ServiceType, TenantServiceBrand, TenantServiceType):
        table = model.__table__.to_metadata(metadata)
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON(none_as_null=column.type.none_as_null)
    metadata.create_all(engine)
    with Session(engine) as session:
        ts = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4(), master_service_id=uuid.uuid4(),
                             brand_coverage_mode="all", type_coverage_mode="selected")
        types = [ServiceType(id=uuid.uuid4(), name=name, slug=name) for name in ("split", "window")]
        brands = [Brand(id=uuid.uuid4(), name=name, slug=name) for name in ("daikin", "lg")]
        session.add_all(types + brands)
        session.add_all([MasterServiceType(master_service_id=ts.master_service_id, service_type_id=row.id) for row in types])
        session.add_all([MasterServiceBrand(master_service_id=ts.master_service_id, brand_id=row.id) for row in brands])
        session.flush()
        db = MagicMock(execute=AsyncMock(side_effect=session.execute), flush=AsyncMock(side_effect=session.flush))
        db.add = session.add
        service = TenantCatalogService(db, actor_tenant_id=ts.tenant_id)
        service._load_tenant_service = AsyncMock(return_value=ts)
        yield service, session, ts, types, brands
    engine.dispose()


async def save_mixed(service, ts, types, brands):
    return await service.set_tenant_service_types(ts.id, [str(row.id) for row in types], {
        str(types[0].id): {"mode": "selected", "brand_ids": [str(brands[0].id)]},
        str(types[1].id): {"mode": "all", "brand_ids": []},
    })


@pytest.mark.asyncio
async def test_save_reload_and_exact_pair_support(catalog):
    service, session, ts, types, brands = catalog
    result = await save_mixed(service, ts, types, brands)
    session.commit()
    session.expire_all()
    reloaded = await service.get_tenant_service_types(ts.id)
    assert reloaded == result
    by_name = {row["name"]: row["brand_coverage"] for row in reloaded["types"]}
    assert by_name["split"] == {"mode": "selected", "brand_ids": [str(brands[0].id)]}
    assert by_name["window"] == {"mode": "all", "brand_ids": []}
    assert await service.is_brand_supported(ts, brands[0].id, types[0].id)
    assert not await service.is_brand_supported(ts, brands[1].id, types[0].id)
    assert await service.is_brand_supported(ts, brands[1].id, types[1].id)
    assert not await service.is_brand_supported(ts, uuid.uuid4(), types[1].id)


@pytest.mark.asyncio
async def test_price_override_cannot_enable_an_unsupported_pair(catalog):
    service, session, ts, types, brands = catalog
    await save_mixed(service, ts, types, brands)
    session.add(TenantServiceBrand(tenant_id=ts.tenant_id, tenant_service_id=ts.id,
                                  service_type_id=types[0].id, brand_id=brands[1].id,
                                  tenant_min_price=999, tenant_max_price=999, is_enabled=True))
    session.flush()
    assert await service.resolve_tenant_price(ts.id, types[0].id, brands[1].id) == {
        "resolved": False, "reason": "COMBINATION_NOT_SUPPORTED",
    }


@pytest.mark.asyncio
async def test_global_repair_brand_choice_replaces_stale_type_coverage(catalog):
    service, session, ts, types, brands = catalog
    await save_mixed(service, ts, types, brands)
    assert not await service.is_brand_supported(ts, brands[1].id, types[0].id)
    await service.set_tenant_service_brands(ts.id, [str(brand.id) for brand in brands], apply_to_all_types=True)
    session.commit()
    session.expire_all()
    for service_type in types:
        for brand in brands:
            assert await service.is_brand_supported(ts, brand.id, service_type.id)
    await service.set_tenant_service_brands(ts.id, [str(brands[0].id)], apply_to_all_types=True)
    session.commit()
    session.expire_all()
    for service_type in types:
        assert await service.is_brand_supported(ts, brands[0].id, service_type.id)
        assert not await service.is_brand_supported(ts, brands[1].id, service_type.id)


@pytest.mark.asyncio
async def test_normal_brand_save_preserves_type_specific_coverage(catalog):
    service, session, ts, types, brands = catalog
    await save_mixed(service, ts, types, brands)
    await service.set_tenant_service_brands(ts.id, [str(brand.id) for brand in brands])
    assert not await service.is_brand_supported(ts, brands[1].id, types[0].id)
    assert await service.is_brand_supported(ts, brands[1].id, types[1].id)


@pytest.mark.asyncio
async def test_disabled_type_and_retired_brand_do_not_match(catalog):
    service, session, ts, types, brands = catalog
    await save_mixed(service, ts, types, brands)
    brands[0].is_active = False
    session.flush()
    assert not await service.is_brand_supported(ts, brands[0].id, types[0].id)
    await service.set_tenant_service_types(ts.id, [str(types[0].id)])
    assert not await service.is_brand_supported(ts, brands[1].id, types[1].id)


@pytest.mark.asyncio
async def test_required_brand_readiness_uses_scoped_support_without_global_markers(catalog):
    service, session, ts, types, brands = catalog
    ts.requires_type = True
    ts.brand_coverage_mode = "selected"
    await save_mixed(service, ts, types, brands)
    assert await service._has_supported_brand(ts)
    for brand in brands:
        brand.is_active = False
    session.flush()
    assert not await service._has_supported_brand(ts)


@pytest.mark.asyncio
async def test_type_selection_without_coverage_preserves_legacy_null(catalog):
    service, session, ts, types, brands = catalog
    ts.requires_type = True
    await service.set_tenant_service_types(ts.id, [str(types[0].id)])
    session.commit()
    session.expire_all()
    row = session.scalars(select(TenantServiceType)).one()
    assert row.brand_coverage is None
    assert await service._has_supported_brand(ts)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["empty", "unmapped", "wrong_type", "mode", "not_list"])
async def test_invalid_coverage_rejected_before_any_write(catalog, invalid):
    service, session, ts, types, brands = catalog
    coverage = {str(types[0].id): {"mode": "selected", "brand_ids": [str(brands[0].id)]}}
    if invalid == "empty": coverage[str(types[0].id)]["brand_ids"] = []
    if invalid == "unmapped": coverage[str(types[0].id)]["brand_ids"] = [str(uuid.uuid4())]
    if invalid == "wrong_type": coverage[str(uuid.uuid4())] = {"mode": "all"}
    if invalid == "mode": coverage[str(types[0].id)]["mode"] = "anything"
    if invalid == "not_list": coverage[str(types[0].id)]["brand_ids"] = "daikin"
    with pytest.raises(ServiceOSException):
        await service.set_tenant_service_types(ts.id, [str(types[0].id)], coverage)
    assert session.scalars(select(TenantServiceType)).all() == []


@pytest.mark.asyncio
async def test_foreign_tenant_cannot_change_coverage(catalog):
    service, session, ts, types, brands = catalog
    service.actor_tenant_id = uuid.uuid4()
    with pytest.raises(ServiceOSException):
        await save_mixed(service, ts, types, brands)
    assert session.scalars(select(TenantServiceType)).all() == []
