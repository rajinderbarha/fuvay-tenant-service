"""Sprint 3 — Admin Service Catalog, Tier Pricing & Tenant Service Enablement.

Tests the AdminCatalogService, pricing engine (resolve_service_price),
and TenantCatalogService at the service layer — no real DB, no HTTP.

asyncio_mode = "auto" via pyproject.toml — no @pytest.mark.asyncio needed.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.engines.admin_catalog.service import AdminCatalogService, _slugify
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.admin_catalog.models import (
    PricingTier, TierLocation, ServiceCategory, MasterService,
    ServiceType, Brand, MasterServiceType, MasterServiceBrand,
    ServicePricingRule, TenantService, TenantServiceType, TenantServiceBrand,
)
from app.exceptions import ServiceOSException, NotFoundException

utcnow = lambda: datetime.now(timezone.utc)


# ─── DB Mock Helpers ─────────────────────────────────────────────────────────

def db_one(obj):
    """Mock db that returns `obj` for the first scalar_one_or_none call."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def db_seq(*objects):
    """Mock db returning objects[i] for the i-th execute call."""
    results = []
    for obj in objects:
        r = MagicMock()
        if isinstance(obj, list):
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = obj
            scalars_mock.first.return_value = obj[0] if obj else None
            r.scalars.return_value = scalars_mock
        else:
            r.scalar_one_or_none.return_value = obj
        results.append(r)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock(side_effect=lambda o: setattr(o, "id", uuid.uuid4()) if not getattr(o, "id", None) else None)
    db.flush = AsyncMock()
    return db


def make_tier(**kw) -> PricingTier:
    t = MagicMock(spec=PricingTier)
    t.id = uuid.uuid4()
    t.name = kw.get("name", "Tier 3 Small City")
    t.code = kw.get("code", "tier_3_small_city")
    t.tier_type = kw.get("tier_type", "small_city")
    t.description = kw.get("description", None)
    t.base_multiplier = Decimal(str(kw.get("base_multiplier", "1.0")))
    t.platform_fee_percent = Decimal("0")
    t.default_commission_percent = Decimal("10")
    t.default_sla_minutes = 60
    t.is_active = kw.get("is_active", True)
    t.deleted_at = None
    t.created_at = utcnow()
    return t


def make_category(**kw) -> ServiceCategory:
    c = MagicMock(spec=ServiceCategory)
    c.id = uuid.uuid4()
    c.name = kw.get("name", "AC Services")
    c.slug = kw.get("slug", "ac-services")
    c.description = kw.get("description", None)
    c.icon_url = None
    c.image_url = None
    c.display_order = 0
    c.is_active = kw.get("is_active", True)
    c.deleted_at = None
    c.created_at = utcnow()
    return c


def make_service(**kw) -> MasterService:
    s = MagicMock(spec=MasterService)
    s.id = uuid.uuid4()
    s.category_id = kw.get("category_id", uuid.uuid4())
    s.service_name = kw.get("service_name", "AC Repair")
    s.slug = kw.get("slug", "ac-repair")
    s.description = kw.get("description", None)
    s.image_url = None
    s.icon_url = None
    s.job_type = kw.get("job_type", "repair")
    s.pricing_model = kw.get("pricing_model", "post_assessment")
    s.base_price = Decimal(str(kw.get("base_price", "399")))
    s.min_price = Decimal(str(kw.get("min_price", "399"))) if kw.get("min_price") else None
    s.max_price = Decimal(str(kw.get("max_price", "2500"))) if kw.get("max_price") else None
    s.visit_fee = Decimal(str(kw.get("visit_fee", "399")))
    s.pre_approval_limit = None
    s.estimated_duration_minutes = None
    s.requires_checklist = kw.get("requires_checklist", False)
    s.is_brand_required = kw.get("is_brand_required", False)
    s.is_type_required = kw.get("is_type_required", False)
    s.tenant_override_allowed = kw.get("tenant_override_allowed", False)
    s.tenant_custom_name_allowed = True
    s.display_order = 0
    s.is_active = kw.get("is_active", True)
    s.deleted_at = None
    s.created_at = utcnow()
    return s


def make_service_type(**kw) -> ServiceType:
    t = MagicMock(spec=ServiceType)
    t.id = uuid.uuid4()
    t.category_id = kw.get("category_id", uuid.uuid4())
    t.name = kw.get("name", "Split AC")
    t.slug = _slugify(kw.get("name", "Split AC"))
    t.description = None
    t.icon_url = None
    t.is_active = kw.get("is_active", True)
    t.deleted_at = None
    return t


def make_brand(**kw) -> Brand:
    b = MagicMock(spec=Brand)
    b.id = uuid.uuid4()
    b.category_id = kw.get("category_id", None)
    b.name = kw.get("name", "Daikin")
    b.slug = _slugify(kw.get("name", "Daikin"))
    b.logo_url = None
    b.description = None
    b.is_active = kw.get("is_active", True)
    b.deleted_at = None
    return b


def make_tenant_service(**kw) -> TenantService:
    ts = MagicMock(spec=TenantService)
    ts.id = uuid.uuid4()
    ts.tenant_id = kw.get("tenant_id", uuid.uuid4())
    ts.master_service_id = kw.get("master_service_id", uuid.uuid4())
    ts.category_id = kw.get("category_id", uuid.uuid4())
    ts.job_type = kw.get("job_type", "repair")
    ts.is_enabled = kw.get("is_enabled", True)
    ts.tenant_display_name = kw.get("tenant_display_name", None)
    ts.tenant_description = None
    ts.tenant_base_price = None
    ts.tenant_min_price = None
    ts.tenant_max_price = None
    ts.tenant_visit_fee = None
    ts.override_allowed = kw.get("override_allowed", False)
    ts.requires_brand = kw.get("requires_brand", False)
    ts.requires_type = kw.get("requires_type", False)
    ts.is_active = True
    ts.deleted_at = None
    ts.created_at = utcnow()
    return ts


# ═══════════════════════════════════════════════════════════════
# 1. SLUGIFY UTILITY
# ═══════════════════════════════════════════════════════════════

def test_slugify_basic():
    assert _slugify("AC Repair") == "ac-repair"

def test_slugify_special_chars():
    assert _slugify("Air Conditioning & Cooling") == "ac-cooling" or "air-conditioning" in _slugify("Air Conditioning & Cooling")

def test_slugify_strip():
    assert _slugify("  Split AC  ") == "split-ac"


# ═══════════════════════════════════════════════════════════════
# 2. PRICING TIERS
# ═══════════════════════════════════════════════════════════════

async def test_create_tier_success():
    db = db_seq(None)  # no duplicate found
    svc = AdminCatalogService(db=db)
    result = await svc.create_tier({
        "name": "Tier 3 Small City", "code": "tier_3_small_city", "tier_type": "small_city",
        "base_multiplier": 1.0, "platform_fee_percent": 5, "default_commission_percent": 10,
        "default_sla_minutes": 60,
    })
    assert result["code"] == "tier_3_small_city"
    assert result["tier_type"] == "small_city"
    assert result["base_multiplier"] == 1.0


async def test_create_tier_duplicate_code_blocked():
    existing_tier = make_tier(code="tier_3_small_city")
    db = db_seq(existing_tier)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_tier({"name": "Another", "code": "tier_3_small_city", "tier_type": "small_city"})
    assert exc.value.error_code == "TIER_CODE_DUPLICATE"


async def test_create_tier_invalid_type():
    db = db_seq(None)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_tier({"name": "T", "code": "xyz", "tier_type": "invalid_type"})
    assert exc.value.error_code == "TIER_INVALID_TYPE"


async def test_create_tier_negative_multiplier():
    db = db_seq(None)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_tier({"name": "T", "code": "t1", "tier_type": "metro", "base_multiplier": -1})
    assert exc.value.error_code == "TIER_INVALID_MULTIPLIER"


async def test_list_tiers():
    tier = make_tier()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [tier]
    result_mock.scalars.return_value = scalars_mock
    db = MagicMock()
    db.execute = AsyncMock(return_value=result_mock)
    svc = AdminCatalogService(db=db)
    # list_tiers also computes per-tier linked counts (mapped locations + pricing rules) —
    # stub that helper so this test stays focused on tier listing/shaping.
    with patch.object(AdminCatalogService, "_tier_linked_counts", AsyncMock(return_value={})):
        result = await svc.list_tiers()
    assert len(result["tiers"]) == 1
    assert result["tiers"][0]["code"] == tier.code


async def test_delete_tier():
    tier = make_tier()
    db = db_one(tier)
    svc = AdminCatalogService(db=db)
    result = await svc.delete_tier(tier.id)
    assert result["deleted"] is True
    assert tier.is_active is False


# ═══════════════════════════════════════════════════════════════
# 3. TIER LOCATIONS
# ═══════════════════════════════════════════════════════════════

async def test_create_tier_location_by_zipcode():
    tier = make_tier()
    db = db_seq(tier, None)  # tier load + duplicate check (not needed actually, just tier)
    # Actually create_tier_location only calls _load_tier once
    db2 = db_one(tier)
    svc = AdminCatalogService(db=db2)
    result = await svc.create_tier_location({"tier_id": str(tier.id), "zipcode": "141001", "state": "Punjab"})
    assert result["zipcode"] == "141001"


async def test_create_tier_location_requires_city_or_zip():
    tier = make_tier()
    db = db_one(tier)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_tier_location({"tier_id": str(tier.id)})
    assert exc.value.error_code == "TIER_LOCATION_CITY_OR_ZIP"


async def test_resolve_location_by_zipcode():
    loc = MagicMock(spec=TierLocation)
    loc.tier_id = uuid.uuid4()
    tier = make_tier()
    db = db_seq(loc, tier)
    svc = AdminCatalogService(db=db)
    result = await svc.resolve_location(None, "141001")
    assert result["matched_by"] == "zipcode"
    assert result["tier"] is not None


async def test_resolve_location_by_city_fallback():
    # zipcode gives no result, city gives result
    loc = MagicMock(spec=TierLocation)
    loc.tier_id = uuid.uuid4()
    tier = make_tier()
    db = db_seq(None, loc, tier)  # zipcode query → None; city query → loc; tier query → tier
    svc = AdminCatalogService(db=db)
    result = await svc.resolve_location("Ludhiana", "999999")
    assert result["matched_by"] == "city"


async def test_resolve_location_no_match():
    db = db_seq(None, None)
    svc = AdminCatalogService(db=db)
    result = await svc.resolve_location("UnknownCity", None)
    assert result["matched_by"] is None
    assert result["tier"] is None


# ═══════════════════════════════════════════════════════════════
# 4. SERVICE CATEGORIES
# ═══════════════════════════════════════════════════════════════

async def test_create_category_success():
    db = db_seq(None)  # no duplicate slug
    svc = AdminCatalogService(db=db)
    result = await svc.create_category({"name": "AC Services", "description": "All AC services"})
    assert result["name"] == "AC Services"
    assert result["slug"] == "ac-services"
    assert result["is_active"] is True


async def test_create_category_duplicate_slug_blocked():
    existing = make_category(name="AC Services", slug="ac-services")
    db = db_seq(existing)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_category({"name": "AC Services"})
    assert exc.value.error_code == "SERVICE_CATEGORY_SLUG_DUPLICATE"


async def test_create_category_name_required():
    db = MagicMock()
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_category({"name": ""})
    assert exc.value.error_code == "SERVICE_CATEGORY_NAME_REQUIRED"


async def test_delete_category_with_active_services_blocked():
    cat = make_category()
    active_svc = make_service()
    db = db_seq(cat, active_svc)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.delete_category(cat.id)
    assert exc.value.error_code == "SERVICE_CATEGORY_HAS_ACTIVE_SERVICES"


async def test_delete_category_safe():
    cat = make_category()
    db = db_seq(cat, None)  # category found, no active services
    svc = AdminCatalogService(db=db)
    result = await svc.delete_category(cat.id)
    assert result["deleted"] is True
    assert cat.is_active is False


# ═══════════════════════════════════════════════════════════════
# 5. MASTER SERVICES
# ═══════════════════════════════════════════════════════════════

async def test_create_master_service_repair():
    cat = make_category()
    db = db_seq(cat, None)  # category + slug check
    svc = AdminCatalogService(db=db)
    result = await svc.create_master_service({
        "category_id": str(cat.id), "service_name": "AC Repair",
        "job_type": "repair", "pricing_model": "post_assessment",
        "base_price": 399, "visit_fee": 399, "min_price": 399, "max_price": 2500,
        "customer_note": "Final price will be shared after technician inspection.",
    })
    assert result["job_type"] == "repair"
    assert result["pricing_model"] == "post_assessment"


async def test_create_master_service_service():
    cat = make_category()
    db = db_seq(cat, None)
    svc = AdminCatalogService(db=db)
    result = await svc.create_master_service({
        "category_id": str(cat.id), "service_name": "AC Annual Service",
        "job_type": "service", "pricing_model": "fixed", "base_price": 699,
    })
    assert result["job_type"] == "service"


async def test_create_master_service_consultation():
    cat = make_category()
    db = db_seq(cat, None)
    svc = AdminCatalogService(db=db)
    result = await svc.create_master_service({
        "category_id": str(cat.id), "service_name": "AC Inspection",
        "job_type": "consultation", "pricing_model": "fixed", "base_price": 199,
    })
    assert result["job_type"] == "consultation"


async def test_create_master_service_missing_job_type():
    cat = make_category()
    db = db_seq(cat)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_master_service({
            "category_id": str(cat.id), "service_name": "Test",
            "pricing_model": "fixed", "base_price": 100,
        })
    assert exc.value.error_code == "INVALID_JOB_TYPE"


async def test_create_master_service_invalid_job_type():
    cat = make_category()
    db = db_seq(cat)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_master_service({
            "category_id": str(cat.id), "service_name": "Test",
            "job_type": "invalid_type", "pricing_model": "fixed", "base_price": 100,
        })
    assert exc.value.error_code == "INVALID_JOB_TYPE"


async def test_create_master_service_min_exceeds_max():
    cat = make_category()
    db = db_seq(cat)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_master_service({
            "category_id": str(cat.id), "service_name": "Test",
            "job_type": "repair", "pricing_model": "range",
            "base_price": 100, "min_price": 500, "max_price": 200,
        })
    assert exc.value.error_code == "INVALID_PRICE_RANGE"


async def test_create_master_service_inactive_category():
    cat = make_category(is_active=False)
    db = db_seq(cat)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_master_service({
            "category_id": str(cat.id), "service_name": "Test",
            "job_type": "repair", "pricing_model": "fixed", "base_price": 100,
        })
    assert exc.value.error_code == "SERVICE_CATEGORY_INACTIVE"


async def test_delete_master_service():
    service = make_service()
    db = db_one(service)
    svc = AdminCatalogService(db=db)
    result = await svc.delete_master_service(service.id)
    assert result["deleted"] is True
    assert service.is_active is False


# ═══════════════════════════════════════════════════════════════
# 6. SERVICE TYPES
# ═══════════════════════════════════════════════════════════════

async def test_create_service_type_success():
    db = db_seq(None)  # no duplicate slug
    svc = AdminCatalogService(db=db)
    result = await svc.create_service_type({"name": "Split AC", "category_id": str(uuid.uuid4())})
    assert result["name"] == "Split AC"
    assert result["slug"] == "split-ac"


async def test_create_service_type_name_required():
    db = MagicMock()
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_service_type({"name": ""})
    assert exc.value.error_code == "SERVICE_TYPE_NAME_REQUIRED"


async def test_delete_service_type():
    st = make_service_type()
    db = db_one(st)
    svc = AdminCatalogService(db=db)
    result = await svc.delete_service_type(st.id)
    assert result["deleted"] is True


# ═══════════════════════════════════════════════════════════════
# 7. BRANDS
# ═══════════════════════════════════════════════════════════════

async def test_create_brand_success():
    db = db_seq(None)
    svc = AdminCatalogService(db=db)
    result = await svc.create_brand({"name": "Daikin"})
    assert result["name"] == "Daikin"
    assert result["slug"] == "daikin"


async def test_create_brand_name_required():
    db = MagicMock()
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_brand({"name": ""})
    assert exc.value.error_code == "BRAND_NAME_REQUIRED"


async def test_delete_brand():
    brand = make_brand()
    db = db_one(brand)
    svc = AdminCatalogService(db=db)
    result = await svc.delete_brand(brand.id)
    assert result["deleted"] is True


# ═══════════════════════════════════════════════════════════════
# 8. TYPE / BRAND MAPPING
# ═══════════════════════════════════════════════════════════════

async def test_map_service_type_success():
    service = make_service()
    st = make_service_type()
    # db_seq: load_master_service, load service_type, check duplicate
    db = db_seq(service, st, None)
    svc = AdminCatalogService(db=db)
    result = await svc.map_service_type(service.id, {"service_type_id": str(st.id)})
    assert "mapping_id" in result


async def test_map_service_type_duplicate_blocked():
    service = make_service()
    st = make_service_type()
    existing_mapping = MagicMock(spec=MasterServiceType)
    db = db_seq(service, st, existing_mapping)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.map_service_type(service.id, {"service_type_id": str(st.id)})
    assert exc.value.error_code == "MAPPING_DUPLICATE"


async def test_map_brand_success():
    service = make_service()
    brand = make_brand()
    db = db_seq(service, brand, None)
    svc = AdminCatalogService(db=db)
    result = await svc.map_service_brand(service.id, {"brand_id": str(brand.id)})
    assert "mapping_id" in result


async def test_map_brand_duplicate_blocked():
    service = make_service()
    brand = make_brand()
    existing_mapping = MagicMock(spec=MasterServiceBrand)
    db = db_seq(service, brand, existing_mapping)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.map_service_brand(service.id, {"brand_id": str(brand.id)})
    assert exc.value.error_code == "MAPPING_DUPLICATE"


# ═══════════════════════════════════════════════════════════════
# 9. PRICING RULES
# ═══════════════════════════════════════════════════════════════

async def test_create_pricing_rule_success():
    service = make_service()
    # HS3: create_pricing_rule now runs an extra duplicate-check query
    # (empty list = no existing duplicate) before inserting.
    db = db_seq(service, [])
    svc = AdminCatalogService(db=db)
    result = await svc.create_pricing_rule({
        "master_service_id": str(service.id),
        "job_type": "repair",
        "pricing_model": "post_assessment",
        "base_price": 399,
        "visit_fee": 399,
        "commission_percent": 10,
        "priority": 50,
    })
    assert result["job_type"] == "repair"
    assert result["base_price"] == 399.0
    assert result["priority"] == 50


async def test_create_pricing_rule_invalid_job_type():
    service = make_service()
    db = db_seq(service)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_pricing_rule({
            "master_service_id": str(service.id),
            "job_type": "bad_type",
            "pricing_model": "fixed",
            "base_price": 100,
        })
    assert exc.value.error_code == "INVALID_JOB_TYPE"


async def test_create_pricing_rule_min_exceeds_max():
    service = make_service()
    db = db_seq(service)
    svc = AdminCatalogService(db=db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_pricing_rule({
            "master_service_id": str(service.id),
            "job_type": "repair",
            "pricing_model": "range",
            "base_price": 100,
            "min_price": 1000,
            "max_price": 500,
        })
    assert exc.value.error_code == "INVALID_PRICE_RANGE"


async def test_delete_pricing_rule():
    rule = MagicMock(spec=ServicePricingRule)
    rule.id = uuid.uuid4()
    rule.is_active = True
    rule.deleted_at = None
    db = db_one(rule)
    svc = AdminCatalogService(db=db)
    result = await svc.delete_pricing_rule(rule.id)
    assert result["deleted"] is True


# ═══════════════════════════════════════════════════════════════
# 10. PRICING ENGINE (resolve_service_price)
# ═══════════════════════════════════════════════════════════════

async def test_pricing_engine_uses_global_default_when_no_rule():
    """When no pricing rule matches, falls back to master service base price."""
    from app.engines.admin_catalog.pricing_engine import resolve_service_price

    service = make_service(base_price=399, visit_fee=399, is_type_required=False, is_brand_required=False)
    # db.execute sequence: svc load, no tier loc found, no rule candidates found (all None)
    db = MagicMock()
    results = []
    # 1st: service load
    r = MagicMock(); r.scalar_one_or_none.return_value = service; results.append(r)
    # 2nd+: tier location lookups return None
    for _ in range(10):
        r = MagicMock(); r.scalar_one_or_none.return_value = None; results.append(r)

    db.execute = AsyncMock(side_effect=results)

    result = await resolve_service_price(db, service.id)
    assert result["source"] == "master_service_default"
    assert result["base_price"] == 399.0
    assert result["service_name"] == "AC Repair"


async def test_pricing_engine_requires_type_when_flagged():
    from app.engines.admin_catalog.pricing_engine import resolve_service_price

    service = make_service(is_type_required=True, is_brand_required=False)
    db = db_one(service)
    with pytest.raises(ServiceOSException) as exc:
        await resolve_service_price(db, service.id)
    assert exc.value.error_code == "SERVICE_TYPE_REQUIRED"


async def test_pricing_engine_requires_brand_when_flagged():
    from app.engines.admin_catalog.pricing_engine import resolve_service_price

    service = make_service(is_type_required=False, is_brand_required=True)
    db = db_one(service)
    with pytest.raises(ServiceOSException) as exc:
        await resolve_service_price(db, service.id)
    assert exc.value.error_code == "BRAND_REQUIRED"


async def test_pricing_engine_inactive_service_blocked():
    from app.engines.admin_catalog.pricing_engine import resolve_service_price

    service = make_service(is_active=False)
    db = db_one(service)
    with pytest.raises(ServiceOSException) as exc:
        await resolve_service_price(db, service.id)
    assert exc.value.error_code == "MASTER_SERVICE_INACTIVE"


# ═══════════════════════════════════════════════════════════════
# 11. TENANT SERVICE ENABLEMENT
# ═══════════════════════════════════════════════════════════════

async def test_tenant_can_enable_active_service():
    tenant_id = uuid.uuid4()
    service = make_service()
    cat = make_category()
    # db_seq: svc load, category load, existing check (none)
    db = db_seq(service, cat, None)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    result = await ts_svc.enable_service({"master_service_id": str(service.id)}, tenant_id)
    assert result["is_enabled"] is True
    assert result["job_type"] == service.job_type


async def test_tenant_cannot_enable_inactive_service():
    tenant_id = uuid.uuid4()
    service = make_service(is_active=False)
    db = db_seq(service)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.enable_service({"master_service_id": str(service.id)}, tenant_id)
    assert exc.value.error_code == "MASTER_SERVICE_INACTIVE"


async def test_tenant_cannot_enable_service_from_inactive_category():
    tenant_id = uuid.uuid4()
    service = make_service()
    cat = make_category(is_active=False)
    db = db_seq(service, cat)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.enable_service({"master_service_id": str(service.id)}, tenant_id)
    assert exc.value.error_code == "SERVICE_CATEGORY_INACTIVE"


async def test_tenant_cannot_enable_already_enabled_service():
    tenant_id = uuid.uuid4()
    service = make_service()
    cat = make_category()
    existing_ts = make_tenant_service(tenant_id=tenant_id, master_service_id=service.id, is_enabled=True)
    db = db_seq(service, cat, existing_ts)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.enable_service({"master_service_id": str(service.id)}, tenant_id)
    assert exc.value.error_code == "TENANT_SERVICE_ALREADY_ENABLED"


async def test_tenant_override_blocked_when_not_allowed():
    tenant_id = uuid.uuid4()
    service = make_service(tenant_override_allowed=False)
    cat = make_category()
    db = db_seq(service, cat, None)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.enable_service({
            "master_service_id": str(service.id),
            "tenant_base_price": 500,
        }, tenant_id)
    assert exc.value.error_code == "TENANT_SERVICE_OVERRIDE_NOT_ALLOWED"


async def test_tenant_price_below_admin_min_blocked():
    tenant_id = uuid.uuid4()
    service = make_service(tenant_override_allowed=True, min_price=399)
    cat = make_category()
    db = db_seq(service, cat, None)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.enable_service({
            "master_service_id": str(service.id),
            "tenant_min_price": 99,
        }, tenant_id)
    assert exc.value.error_code == "TENANT_PRICE_BELOW_ADMIN_MIN"


async def test_tenant_cannot_select_unmapped_brand():
    tenant_id = uuid.uuid4()
    ts = make_tenant_service(tenant_id=tenant_id)
    unmapped_brand_id = str(uuid.uuid4())
    # admin mapped brands = empty list
    ts_load = MagicMock(); ts_load.scalar_one_or_none.return_value = ts
    admin_brands_scalars = MagicMock(); admin_brands_scalars.all.return_value = []
    admin_brands_res = MagicMock(); admin_brands_res.scalars.return_value = admin_brands_scalars
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[ts_load, admin_brands_res])
    db.add = MagicMock()
    db.flush = AsyncMock()
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.set_tenant_service_brands(ts.id, [unmapped_brand_id])
    assert exc.value.error_code == "BRAND_NOT_SUPPORTED"


async def test_tenant_cannot_select_unmapped_type():
    tenant_id = uuid.uuid4()
    ts = make_tenant_service(tenant_id=tenant_id)
    unmapped_type_id = str(uuid.uuid4())
    ts_load = MagicMock(); ts_load.scalar_one_or_none.return_value = ts
    admin_types_scalars = MagicMock(); admin_types_scalars.all.return_value = []
    admin_types_res = MagicMock(); admin_types_res.scalars.return_value = admin_types_scalars
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[ts_load, admin_types_res])
    db.add = MagicMock()
    db.flush = AsyncMock()
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    with pytest.raises(ServiceOSException) as exc:
        await ts_svc.set_tenant_service_types(ts.id, [unmapped_type_id])
    assert exc.value.error_code == "SERVICE_TYPE_NOT_SUPPORTED"


async def test_tenant_idor_blocked():
    """Tenant A cannot access Tenant B's enabled service."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    ts = make_tenant_service(tenant_id=tenant_b)
    db = db_one(ts)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_a, actor_role="tenant_owner")
    with pytest.raises(NotFoundException):
        await ts_svc.get_enabled_service(ts.id)


async def test_disable_service():
    tenant_id = uuid.uuid4()
    service = make_service()
    ts = make_tenant_service(tenant_id=tenant_id, master_service_id=service.id, is_enabled=True)
    db = db_one(ts)
    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    result = await ts_svc.disable_service({"master_service_id": str(service.id)}, tenant_id)
    assert result["disabled"] is True
    assert ts.is_enabled is False


async def test_list_available_shows_enabled_flag():
    tenant_id = uuid.uuid4()
    service = make_service()
    tenant_service = make_tenant_service(tenant_id=tenant_id, master_service_id=service.id)

    # db: list master services, list enabled
    svcs_scalars = MagicMock(); svcs_scalars.all.return_value = [service]
    svcs_res = MagicMock(); svcs_res.scalars.return_value = svcs_scalars
    enabled_scalars = MagicMock(); enabled_scalars.all.return_value = [tenant_service]
    enabled_res = MagicMock(); enabled_res.scalars.return_value = enabled_scalars
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[svcs_res, enabled_res])

    ts_svc = TenantCatalogService(db=db, actor_tenant_id=tenant_id, actor_role="tenant_owner")
    result = await ts_svc.list_available_services(tenant_id)
    assert len(result["services"]) == 1
    assert result["services"][0]["is_enabled"] is True


# ═══════════════════════════════════════════════════════════════
# 12. SECURITY — cross-tenant access blocked
# ═══════════════════════════════════════════════════════════════

async def test_non_admin_cannot_read_nonexistent_tier():
    db = db_one(None)
    svc = AdminCatalogService(db=db, actor_role="tenant_owner")
    with pytest.raises(NotFoundException):
        await svc.get_tier(uuid.uuid4())


async def test_non_admin_cannot_read_nonexistent_master_service():
    db = db_one(None)
    svc = AdminCatalogService(db=db, actor_role="tenant_owner")
    with pytest.raises(NotFoundException):
        await svc.get_master_service(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# 13. PRICING ENGINE — message formatting
# ═══════════════════════════════════════════════════════════════

def test_price_message_post_assessment():
    from app.engines.admin_catalog.pricing_engine import _price_message
    msg = _price_message("post_assessment", 399.0, 399.0)
    assert "assessment" in msg.lower()


def test_price_message_fixed():
    from app.engines.admin_catalog.pricing_engine import _price_message
    msg = _price_message("fixed", 699.0, 0.0)
    assert "699" in msg


def test_price_message_range():
    from app.engines.admin_catalog.pricing_engine import _price_message
    msg = _price_message("range", 300.0, 0.0)
    assert "300" in msg


def test_compute_customer_estimate_post_assessment():
    from app.engines.admin_catalog.pricing_engine import _compute_customer_estimate
    assert _compute_customer_estimate("post_assessment", 0, 399.0, None) == 399.0


def test_compute_customer_estimate_fixed():
    from app.engines.admin_catalog.pricing_engine import _compute_customer_estimate
    assert _compute_customer_estimate("fixed", 699.0, 0, None) == 699.0


def test_compute_customer_estimate_range():
    from app.engines.admin_catalog.pricing_engine import _compute_customer_estimate
    assert _compute_customer_estimate("range", 500.0, 0, 350.0) == 350.0
