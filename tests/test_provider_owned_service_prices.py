"""Isolated regressions: provider pricing must not depend on legacy admin amounts."""
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.tenant_service import TenantCatalogService, _decimal_or_none
from app.engines.admin_catalog.models import TenantService
from app.exceptions import ServiceOSException


def result(value):
    row = MagicMock()
    row.scalar_one_or_none.return_value = value
    return row


def catalog(vertical="home_services"):
    tenant_id = uuid.uuid4()
    ts = TenantService(
        id=uuid.uuid4(), tenant_id=tenant_id, master_service_id=uuid.uuid4(),
        category_id=uuid.uuid4(), job_type="installation", override_allowed=False,
        tenant_base_price=None, tenant_min_price=None, tenant_max_price=None,
        tenant_visit_fee=None, warranty_days=5,
    )
    db = MagicMock(
        get=AsyncMock(return_value=SimpleNamespace(vertical_type=vertical)),
        execute=AsyncMock(return_value=result(SimpleNamespace(tenant_override_allowed=False))),
        flush=AsyncMock(),
    )
    service = TenantCatalogService(db, actor_role="tenant_owner", actor_tenant_id=tenant_id)
    service._load_tenant_service = AsyncMock(return_value=ts)
    service._ts_dict = lambda row: row
    return service, ts


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,minimum,visit", [
    ({"tenant_base_price": "899"}, Decimal("899"), None),
    ({"tenant_min_price": "500", "tenant_max_price": "900"}, Decimal("500"), None),
    ({"tenant_visit_fee": "249"}, None, Decimal("249")),
])
async def test_legacy_false_flags_do_not_block_home_provider_prices(payload, minimum, visit):
    service, ts = catalog()
    saved = await service.update_enabled_service(ts.id, payload)
    assert saved.tenant_min_price == minimum
    assert saved.tenant_visit_fee == visit
    assert saved.override_allowed is True
    service.db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_home_price_lock_is_preserved():
    service, ts = catalog("other_vertical")
    with pytest.raises(ServiceOSException, match="Price override"):
        await service.update_enabled_service(ts.id, {"tenant_base_price": 899})
    service.db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_tenant_price_updates_remain_denied():
    service, ts = catalog()
    ts.tenant_id = uuid.uuid4()
    with pytest.raises(ServiceOSException):
        await service.update_enabled_service(ts.id, {"tenant_base_price": 899})
    service.db.get.assert_not_awaited()
    service.db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_partial_update_cannot_invert_saved_range():
    service, ts = catalog()
    ts.tenant_min_price, ts.tenant_max_price = Decimal("500"), Decimal("900")
    with pytest.raises(ServiceOSException, match="Minimum price"):
        await service.update_enabled_service(ts.id, {"tenant_max_price": 300})
    assert ts.tenant_max_price == Decimal("900")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "bad", ""])
def test_invalid_money_is_not_silently_cleared(value):
    with pytest.raises(ServiceOSException):
        _decimal_or_none(value)


@pytest.mark.asyncio
async def test_consultations_cannot_create_dimension_prices():
    service, ts = catalog()
    ts.job_type = "consultation"
    with pytest.raises(ServiceOSException, match="provider-wide fee"):
        await service._reject_dimension_price_for_inspection(ts)
    service.db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_enable_allows_home_provider_price_without_admin_override():
    service, _ = catalog()
    master = SimpleNamespace(
        id=uuid.uuid4(), category_id=uuid.uuid4(), service_group_id=None,
        is_active=True, tenant_override_allowed=False,
    )
    job = SimpleNamespace(id=uuid.uuid4(), key="installation", label="Installation")
    service.db.execute.side_effect = [
        result(master), result(SimpleNamespace(is_active=True, vertical_type="home_services")),
        result(None), result(None),
    ]
    service._resolve_active_job_type = AsyncMock(return_value=job)
    service._setup_rule_revision = AsyncMock(return_value="revision")
    service._tenant_setup_blueprint = AsyncMock(return_value={
        "source": "service_job_workflow", "type_mode": "optional", "brand_mode": "optional",
    })
    saved = await service.enable_service({
        "master_service_id": str(master.id), "job_type_id": str(job.id), "tenant_base_price": "899",
    })
    assert saved.override_allowed is True
    assert saved.tenant_min_price == saved.tenant_max_price == Decimal("899")


def test_readiness_uses_actual_settings_table_and_provider_prices_only():
    from app.engines.tenant_engine.models import TenantSettings
    from app.engines.vertical_catalog.pricing_readiness import PUBLISHED_PRICED_SERVICES_SQL as sql
    assert TenantSettings.__tablename__ in sql
    assert "consultation_fee" in sql
    assert "ts.tenant_visit_fee > 0" in sql
    assert "ts.is_enabled=true" in sql
    assert "master_services" not in sql


def test_readiness_sql_only_references_columns_in_the_actual_models():
    import re
    from app.engines.tenant_engine.models import TenantSettings
    from app.engines.admin_catalog.models import TenantServiceType, TenantServiceBrand
    from app.engines.vertical_catalog.pricing_readiness import PUBLISHED_PRICED_SERVICES_SQL as sql
    for alias, model in {"ts": TenantService, "tst": TenantServiceType,
                         "tsb": TenantServiceBrand, "settings": TenantSettings}.items():
        used_columns = set(re.findall(rf"\b{alias}\.([a-z_]+)", sql))
        assert used_columns <= set(model.__table__.columns.keys())
