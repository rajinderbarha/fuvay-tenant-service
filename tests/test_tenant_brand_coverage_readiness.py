"""Real in-memory SQL checks for effective brand coverage; no external DB."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine, text
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.vertical_catalog.service_setup_readiness import service_setup_readiness


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,selected,mapped,active,expected", [
    ("all", False, True, True, True),
    ("all", False, False, True, False),
    ("all", False, True, False, False),
    ("selected", False, True, True, False),
    ("selected", True, True, True, True),
    ("selected", True, False, True, False),
    ("selected", True, True, False, False),
    ("all_except", False, True, True, True),
    ("all_except", True, True, True, False),
])
async def test_effective_brand_coverage(mode, selected, mapped, active, expected):
    sid, mid, bid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            connection.execute(text("CREATE TABLE brands (id TEXT, is_active BOOLEAN, deleted_at TEXT)"))
            connection.execute(text("CREATE TABLE master_service_brands (master_service_id TEXT, brand_id TEXT, is_active BOOLEAN, status TEXT)"))
            connection.execute(text("CREATE TABLE tenant_service_brands (id TEXT, tenant_service_id TEXT, brand_id TEXT, is_enabled BOOLEAN, service_type_id TEXT)"))
            connection.execute(text("INSERT INTO brands VALUES (:bid, :active, NULL)"), {"bid": bid.hex, "active": active})
            if mapped:
                connection.execute(text("INSERT INTO master_service_brands VALUES (:mid, :bid, 1, 'active')"), {"mid": mid.hex, "bid": bid.hex})
            if selected:
                connection.execute(text("INSERT INTO tenant_service_brands VALUES ('marker', :sid, :bid, 1, NULL)"), {"sid": sid.hex, "bid": bid.hex})
            service = TenantCatalogService(MagicMock(execute=AsyncMock(side_effect=connection.execute)))
            ts = SimpleNamespace(id=sid, master_service_id=mid, brand_coverage_mode=mode)
            assert await service._has_supported_brand(ts) is expected
    finally:
        engine.dispose()


def test_error_names_the_incomplete_offering_not_the_open_editor():
    result = service_setup_readiness([
        ("ac", {"service_name": "AC Installation", "job_type": "installation", "errors": []}),
        ("fridge", {"service_name": "Refrigerator Repair", "job_type": "repair", "errors": [
            {"code": "NO_BRANDS_CONFIGURED", "message": "Admin must map brands."}]}),
    ])
    assert result["blocking_reasons"][0]["tenant_service_id"] == "fridge"
    assert result["blocking_reasons"][0]["message"] == "Refrigerator Repair (repair): Admin must map brands."


@pytest.mark.asyncio
@pytest.mark.parametrize("has_brand", [False, True])
async def test_preflight_and_publication_agree_for_all_brands_without_markers(has_brand):
    from decimal import Decimal
    from app.engines.admin_catalog.models import MasterService, TenantService
    from app.exceptions import ServiceOSException
    tid = uuid.uuid4()
    master = MasterService(id=uuid.uuid4(), service_name="AC Repair")
    ts = TenantService(id=uuid.uuid4(), tenant_id=tid, master_service_id=master.id,
                       job_type_id=uuid.uuid4(), job_type="repair", tenant_visit_fee=Decimal("249"),
                       brand_coverage_mode="all", requires_brand=True, requires_type=False, setup_rules_revision=1)
    def query_result(statement):
        result = MagicMock()
        result.scalar_one_or_none.return_value = master if "FROM master_services" in str(statement) else None
        result.scalars.return_value.all.return_value = []
        return result
    empty = MagicMock()
    empty.all.return_value = []
    db = MagicMock(execute=AsyncMock(side_effect=query_result), scalars=AsyncMock(return_value=empty), flush=AsyncMock())
    service = TenantCatalogService(db, actor_tenant_id=tid)
    service._load_tenant_service = AsyncMock(return_value=ts)
    service._setup_rule_revision = AsyncMock(return_value=1)
    service._tenant_setup_blueprint = AsyncMock(return_value={
        "source": "service_job_workflow", "type_mode": "optional", "brand_mode": "required",
        "pricing_behavior": "inspection_required", "requires_service_area": False, "requires_availability": False,
    })
    service._has_supported_brand = AsyncMock(return_value=has_brand)
    service._ts_dict = lambda row: {"setup_status": row.setup_status}
    validation = await service.validate_for_publish(ts.id)
    assert validation["service_name"] == "AC Repair"
    assert validation["valid"] is has_brand
    if has_brand:
        assert (await service.publish_service(ts.id))["setup_status"] == "published"
    else:
        with pytest.raises(ServiceOSException):
            await service.publish_service(ts.id)
        assert validation["errors"][0]["code"] == "MISSING_REQUIRED_BRAND_SELECTION"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,marker,enabled", [("all", False, True), ("all_except", False, True), ("all_except", True, False), ("selected", True, True), ("selected", False, False)])
async def test_brand_choices_project_effective_coverage(mode, marker, enabled):
    tid = uuid.uuid4()
    ts = SimpleNamespace(id=uuid.uuid4(), tenant_id=tid, master_service_id=uuid.uuid4(), brand_coverage_mode=mode)
    mapping = SimpleNamespace(id=uuid.uuid4(), brand_id=uuid.uuid4(), can_override_price=True)
    brand = SimpleNamespace(name="Daikin")
    selected = SimpleNamespace(id=uuid.uuid4(), is_enabled=marker, tenant_price_adjustment=None) if marker else None
    result = MagicMock()
    result.all.return_value = [(mapping, brand, selected)]
    service = TenantCatalogService(MagicMock(execute=AsyncMock(return_value=result)), actor_tenant_id=tid)
    service._load_tenant_service = AsyncMock(return_value=ts)
    assert (await service.get_tenant_service_brands(ts.id))["brands"][0]["is_enabled"] is enabled


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["all", "all_except"])
async def test_saving_an_explicit_supported_set_stops_treating_rows_as_exclusions(mode):
    tid, chosen, removed = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ts = SimpleNamespace(id=uuid.uuid4(), tenant_id=tid, master_service_id=uuid.uuid4(), brand_coverage_mode=mode)
    kept_row = SimpleNamespace(brand_id=chosen, is_enabled=False, tenant_min_price=1200)
    old_row = SimpleNamespace(brand_id=removed, is_enabled=True, tenant_min_price=1400)
    allowed = MagicMock()
    allowed.scalars.return_value.all.return_value = [SimpleNamespace(brand_id=chosen), SimpleNamespace(brand_id=removed)]
    existing = MagicMock()
    existing.scalars.return_value.all.return_value = [kept_row, old_row]
    db = MagicMock(execute=AsyncMock(side_effect=[allowed, existing]), flush=AsyncMock())
    service = TenantCatalogService(db, actor_tenant_id=tid)
    service._load_tenant_service = AsyncMock(return_value=ts)
    service.get_tenant_service_brands = AsyncMock(return_value={"brands": []})
    await service.set_tenant_service_brands(ts.id, [str(chosen)])
    assert ts.brand_coverage_mode == "selected"
    assert kept_row.is_enabled and not old_row.is_enabled
    assert kept_row.tenant_min_price == 1200
    assert old_row.tenant_min_price == 1400
