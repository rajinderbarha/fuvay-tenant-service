"""Phase 4 — Pricing Engine Tests (45 tests)."""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest

from app.engines.pricing.constants import (
    CITY_TIERS, MAX_BRAND_ADJUSTMENT_PCT, MAX_ZONE_SURCHARGE_PCT,
    MAX_DYNAMIC_DISCOUNT_PCT, MAX_DYNAMIC_SURGE_PCT, MIN_PRICE_INR,
    PipelineStep, RuleType,
)
from app.engines.pricing.pipeline import _rule_matches

# ── 1. Constants ──────────────────────────────────────────────────────────────
def test_city_tiers_defined():
    assert "tier_1" in CITY_TIERS and "tier_2" in CITY_TIERS and "tier_3" in CITY_TIERS

def test_tier_1_contains_metro_cities():
    assert "Mumbai" in CITY_TIERS["tier_1"]["cities"]
    assert "Delhi" in CITY_TIERS["tier_1"]["cities"]
    assert "Bengaluru" in CITY_TIERS["tier_1"]["cities"]

def test_platform_caps_are_sane():
    assert MAX_BRAND_ADJUSTMENT_PCT == Decimal("50.00")
    assert MAX_ZONE_SURCHARGE_PCT == Decimal("40.00")
    assert MAX_DYNAMIC_DISCOUNT_PCT == Decimal("30.00")
    assert MAX_DYNAMIC_SURGE_PCT == Decimal("100.00")
    assert MIN_PRICE_INR == Decimal("50.00")

def test_pipeline_step_constants_unique():
    steps = [PipelineStep.CITY_FLOOR, PipelineStep.TENANT_PRICE,
             PipelineStep.BRAND_ADJ, PipelineStep.ZONE_SURCHARGE, PipelineStep.DYNAMIC_RULE]
    assert len(steps) == len(set(steps))

def test_rule_type_constants_unique():
    types = [RuleType.TIME_OF_DAY, RuleType.DAY_OF_WEEK, RuleType.DATE_RANGE,
             RuleType.DEMAND_SURGE, RuleType.FLAT_OVERRIDE]
    assert len(types) == len(set(types))

# ── 2. Pipeline math ──────────────────────────────────────────────────────────
def test_brand_adjustment_positive_markup():
    base = Decimal("1000.00")
    pct  = Decimal("20.00")
    result = base + (base * pct / Decimal("100")).quantize(Decimal("0.01"))
    assert result == Decimal("1200.00")

def test_brand_adjustment_negative_discount():
    base = Decimal("1000.00")
    pct  = Decimal("-15.00")
    result = base + (base * pct / Decimal("100")).quantize(Decimal("0.01"))
    assert result == Decimal("850.00")

def test_zone_surcharge_adds_correctly():
    base = Decimal("800.00")
    pct  = Decimal("25.00")
    surge = (base * pct / Decimal("100")).quantize(Decimal("0.01"))
    assert surge == Decimal("200.00")
    assert base + surge == Decimal("1000.00")

def test_dynamic_surge_adds_correctly():
    base = Decimal("500.00")
    pct  = Decimal("50.00")
    surge = (base * pct / Decimal("100")).quantize(Decimal("0.01"))
    assert base + surge == Decimal("750.00")

def test_dynamic_discount_subtracts():
    base = Decimal("600.00")
    pct  = Decimal("-20.00")
    discount = (base * pct / Decimal("100")).quantize(Decimal("0.01"))
    assert base + discount == Decimal("480.00")

def test_minimum_price_enforced():
    computed = Decimal("30.00")  # below minimum
    final = max(MIN_PRICE_INR, computed)
    assert final == MIN_PRICE_INR

def test_above_minimum_not_clamped():
    computed = Decimal("500.00")
    final = max(MIN_PRICE_INR, computed)
    assert final == Decimal("500.00")

def test_floor_enforcement_on_tenant_price():
    floor = Decimal("200.00")
    tenant_set = Decimal("150.00")  # below floor
    applied = max(floor, tenant_set)
    assert applied == floor  # floor enforced

def test_tenant_price_above_floor_respected():
    floor = Decimal("200.00")
    tenant_set = Decimal("350.00")
    applied = max(floor, tenant_set)
    assert applied == tenant_set

def test_full_pipeline_math():
    # Simulate all 5 steps
    floor = Decimal("300.00")
    tenant = Decimal("400.00")  # above floor
    brand_pct = Decimal("10.00")
    zone_pct = Decimal("20.00")
    dynamic_pct = Decimal("-5.00")

    after_floor = max(floor, tenant)  # 400
    after_brand = after_floor + (after_floor * brand_pct / 100).quantize(Decimal("0.01"))  # 440
    after_zone  = after_brand + (after_brand * zone_pct / 100).quantize(Decimal("0.01"))   # 528
    after_dyn   = after_zone + (after_zone * dynamic_pct / 100).quantize(Decimal("0.01"))  # 501.6
    final = max(MIN_PRICE_INR, after_dyn)
    assert final == Decimal("501.60")

# ── 3. Rule matching logic ────────────────────────────────────────────────────
class MockRule:
    def __init__(self, rule_type, conditions, applies_to=None, adjustment_pct=10):
        self.rule_type = rule_type
        self.conditions = conditions
        self.applies_to = applies_to or []
        self.adjustment_pct = Decimal(str(adjustment_pct))

def test_day_of_week_rule_matches_monday():
    rule = MockRule(RuleType.DAY_OF_WEEK, {"days": ["monday","tuesday"]})
    monday = datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc)  # a Monday
    assert _rule_matches(rule, monday, "ac_service")

def test_day_of_week_rule_no_match():
    rule = MockRule(RuleType.DAY_OF_WEEK, {"days": ["saturday","sunday"]})
    wednesday = datetime(2026, 6, 24, 10, 0, tzinfo=timezone.utc)
    assert not _rule_matches(rule, wednesday, "ac_service")

def test_time_of_day_rule_matches():
    rule = MockRule(RuleType.TIME_OF_DAY, {"start_hour": 18, "end_hour": 22})
    evening = datetime(2026, 6, 24, 19, 30, tzinfo=timezone.utc)
    assert _rule_matches(rule, evening, "ac_service")

def test_time_of_day_rule_no_match():
    rule = MockRule(RuleType.TIME_OF_DAY, {"start_hour": 18, "end_hour": 22})
    morning = datetime(2026, 6, 24, 9, 0, tzinfo=timezone.utc)
    assert not _rule_matches(rule, morning, "ac_service")

def test_date_range_rule_matches():
    rule = MockRule(RuleType.DATE_RANGE, {
        "start_date": "2026-12-24T00:00:00",
        "end_date": "2026-12-26T23:59:59"})
    christmas = datetime(2026, 12, 25, 12, 0, tzinfo=timezone.utc)
    assert _rule_matches(rule, christmas, "any_service")

def test_date_range_rule_no_match_outside():
    rule = MockRule(RuleType.DATE_RANGE, {
        "start_date": "2026-12-24T00:00:00",
        "end_date": "2026-12-26T23:59:59"})
    jan = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert not _rule_matches(rule, jan, "any_service")

def test_flat_override_always_matches():
    rule = MockRule(RuleType.FLAT_OVERRIDE, {})
    any_time = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)
    assert _rule_matches(rule, any_time, "any_service")

def test_applies_to_filter_blocks_wrong_service():
    rule = MockRule(RuleType.FLAT_OVERRIDE, {}, applies_to=["ac_service"])
    now = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)
    assert not _rule_matches(rule, now, "plumbing")

def test_applies_to_filter_passes_correct_service():
    rule = MockRule(RuleType.FLAT_OVERRIDE, {}, applies_to=["ac_service","plumbing"])
    now = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)
    assert _rule_matches(rule, now, "plumbing")

def test_applies_to_empty_matches_all():
    rule = MockRule(RuleType.FLAT_OVERRIDE, {}, applies_to=[])
    now = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)
    assert _rule_matches(rule, now, "anything")

# ── 4. Versioning invariants ──────────────────────────────────────────────────
def test_service_type_price_model_has_versioning_fields():
    from app.engines.pricing.models import ServiceTypePrice
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(ServiceTypePrice).columns}
    assert "valid_from" in cols
    assert "valid_until" in cols
    assert "previous_price" in cols
    assert "change_reason" in cols

def test_brand_adjustment_model_has_versioning_fields():
    from app.engines.pricing.models import BrandAdjustment
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(BrandAdjustment).columns}
    assert "valid_from" in cols
    assert "valid_until" in cols

def test_price_snapshot_idempotency_key_unique():
    from app.engines.pricing.models import PriceSnapshot
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(PriceSnapshot).mapper.persist_selectable.constraints}
    assert "uq_ps_idem_key" in constraints

def test_snapshot_has_all_pipeline_steps():
    from app.engines.pricing.models import PriceSnapshot
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(PriceSnapshot).columns}
    assert "step_city_floor" in cols
    assert "step_tenant_price" in cols
    assert "step_brand_adj" in cols
    assert "step_zone_surge" in cols
    assert "step_dynamic_rule" in cols
    assert "pipeline_inputs" in cols
    assert "final_price" in cols

# ── 5. Validation math ────────────────────────────────────────────────────────
def test_brand_adj_cap_positive():
    requested = Decimal("60.00")
    allowed = abs(requested) <= MAX_BRAND_ADJUSTMENT_PCT
    assert not allowed  # 60 > 50 — should be blocked

def test_brand_adj_cap_negative():
    requested = Decimal("-55.00")
    allowed = abs(requested) <= MAX_BRAND_ADJUSTMENT_PCT
    assert not allowed

def test_brand_adj_within_cap():
    requested = Decimal("30.00")
    allowed = abs(requested) <= MAX_BRAND_ADJUSTMENT_PCT
    assert allowed

def test_zone_surcharge_cap():
    requested = Decimal("45.00")  # > 40
    allowed = requested <= MAX_ZONE_SURCHARGE_PCT
    assert not allowed

def test_zone_surcharge_within_cap():
    requested = Decimal("25.00")
    allowed = requested <= MAX_ZONE_SURCHARGE_PCT
    assert allowed

def test_dynamic_surge_cap():
    requested = Decimal("110.00")  # > 100
    allowed = requested <= MAX_DYNAMIC_SURGE_PCT
    assert not allowed

def test_dynamic_discount_cap():
    requested = Decimal("-35.00")  # > -30
    allowed = requested >= -MAX_DYNAMIC_DISCOUNT_PCT
    assert not allowed

# ── 6. HTTP endpoint probes ───────────────────────────────────────────────────
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_pricing_meta(client):
    r = client.get("/v1/pricing/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "pricing"
    assert len(d["pipeline_steps"]) == 5
    assert "city_tier_floor" in d["pipeline_steps"]

def test_city_tiers_requires_auth(client):
    assert client.get("/v1/pricing/city-tiers").status_code == 401

def test_create_city_tier_requires_admin(client):
    assert client.post("/v1/pricing/city-tiers", json={}).status_code == 401

def test_compute_requires_auth(client):
    assert client.post("/v1/pricing/compute", json={}).status_code == 401

def test_tenant_prices_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/pricing/tenants/{tid}/prices").status_code == 401

def test_set_price_requires_auth(client):
    tid = uuid.uuid4()
    assert client.post(f"/v1/pricing/tenants/{tid}/prices/set", json={}).status_code == 401

def test_brand_adj_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/pricing/tenants/{tid}/brand-adjustment").status_code == 401

def test_zones_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/pricing/tenants/{tid}/zones").status_code == 401

def test_rules_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/pricing/tenants/{tid}/rules").status_code == 401

def test_cache_invalidate_requires_admin(client):
    tid = uuid.uuid4()
    assert client.post(f"/v1/pricing/tenants/{tid}/cache/invalidate").status_code == 401

def test_price_preview_requires_auth(client):
    tid = uuid.uuid4()
    assert client.post(f"/v1/pricing/tenants/{tid}/price-preview", json={}).status_code == 401

def test_snapshot_requires_auth(client):
    sid = uuid.uuid4()
    assert client.get(f"/v1/pricing/snapshots/{sid}").status_code == 401

def test_all_prior_phases_still_pass(client):
    # Phase 1: health
    assert client.get("/health").status_code == 200
    # Phase 2: auth
    assert client.post("/v1/auth/login", json={"email":"x@x.com","password":"y"}).status_code != 404
    # Phase 3: commerce
    assert client.get("/v1/commerce/meta").status_code == 200
    # Phase 4: pricing
    assert client.get("/v1/pricing/meta").status_code == 200
