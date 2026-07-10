"""Pricing Engine — constants."""
from decimal import Decimal

# ── City tier definitions ──────────────────────────────────────────────────
CITY_TIERS = {
    "tier_1": {"label": "Metro", "cities": ["Mumbai","Delhi","Bengaluru","Chennai","Hyderabad","Kolkata","Pune","Ahmedabad"]},
    "tier_2": {"label": "Tier 2", "cities": ["Jaipur","Lucknow","Kanpur","Nagpur","Indore","Bhopal","Visakhapatnam","Patna"]},
    "tier_3": {"label": "Tier 3", "cities": []},  # all others
}

# ── Platform caps ──────────────────────────────────────────────────────────
MAX_BRAND_ADJUSTMENT_PCT  = Decimal("50.00")   # ±50%
MAX_ZONE_SURCHARGE_PCT    = Decimal("40.00")   # +40%
MAX_DYNAMIC_DISCOUNT_PCT  = Decimal("30.00")   # -30%
MAX_DYNAMIC_SURGE_PCT     = Decimal("100.00")  # +100%
MIN_PRICE_INR             = Decimal("50.00")   # absolute floor

# ── Pipeline step names (for snapshot audit trail) ─────────────────────────
class PipelineStep:
    CITY_FLOOR      = "city_tier_floor"
    TENANT_PRICE    = "tenant_type_price"
    BRAND_ADJ       = "brand_adjustment"
    ZONE_SURCHARGE  = "zone_surcharge"
    DYNAMIC_RULE    = "dynamic_rule"

# ── Price snapshot TTL (idempotency window) ────────────────────────────────
SNAPSHOT_IDEMPOTENCY_TTL_SECONDS = 300   # 5 min — same booking+service = same price

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_PRICE_CACHE      = "serviceos:pricing:computed:{tenant_id}:{service_type_id}:{city}"
REDIS_CITY_TIER        = "serviceos:pricing:city_tier:{city}"
REDIS_TENANT_PRICE     = "serviceos:pricing:tenant_price:{tenant_id}:{service_type_id}"
REDIS_DYNAMIC_RULES    = "serviceos:pricing:dynamic_rules:{tenant_id}"
REDIS_ZONE_CONFIG      = "serviceos:pricing:zones:{tenant_id}"
REDIS_BRAND_ADJ        = "serviceos:pricing:brand_adj:{tenant_id}"

# ── Day-of-week labels ─────────────────────────────────────────────────────
DOW = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]

# ── Dynamic rule types ─────────────────────────────────────────────────────
class RuleType:
    TIME_OF_DAY   = "time_of_day"
    DAY_OF_WEEK   = "day_of_week"
    DATE_RANGE    = "date_range"
    DEMAND_SURGE  = "demand_surge"
    FLAT_OVERRIDE = "flat_override"
