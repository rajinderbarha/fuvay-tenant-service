"""Platform Commerce Engine — constants."""
from decimal import Decimal

# ── Commission rates by plan ───────────────────────────────────────────────
COMMISSION_BASE_RATE: dict[str, Decimal] = {
    "starter":    Decimal("10.00"),
    "growth":     Decimal("7.00"),
    "enterprise": Decimal("5.00"),
}

# ── Health band commission adjustments (percentage points, additive) ───────
COMMISSION_HEALTH_ADJUSTMENT: dict[str, Decimal] = {
    "platinum": Decimal("-1.00"),
    "gold":     Decimal("0.00"),
    "silver":   Decimal("2.00"),
    "bronze":   Decimal("5.00"),
    "at_risk":  Decimal("10.00"),
    "critical": Decimal("10.00"),
}

# ── Customer health bands ──────────────────────────────────────────────────
CUSTOMER_HEALTH_BANDS = {
    "trusted":    (80, 100),
    "standard":   (60, 79),
    "cautious":   (40, 59),
    "restricted": (20, 39),
    "blocked":    (0,  19),
}

CUSTOMER_ADVANCE_REQUIRED_PCT: dict[str, Decimal] = {
    "trusted":    Decimal("0.00"),
    "standard":   Decimal("0.00"),
    "cautious":   Decimal("50.00"),
    "restricted": Decimal("100.00"),
    "blocked":    Decimal("100.00"),  # cannot book, moot
}

# ── Customer health signal weights ─────────────────────────────────────────
CUSTOMER_SIGNAL_WEIGHTS: dict[str, float] = {
    # Payment is the primary trust signal. Behavioural signals (avoidable
    # cancellations/no-shows) matter next; tenure is context, not character.
    "booking_completion_rate": 0.15,
    "payment_reliability":     0.55,
    "cancellation_rate":       0.10,
    "no_show_rate":            0.15,
    "platform_tenure":         0.05,
}

# Default signals for new customers
CUSTOMER_DEFAULT_SIGNALS: dict[str, float] = {
    "booking_completion_rate": 100.0,
    "payment_reliability":     100.0,
    "cancellation_rate":       100.0,
    "no_show_rate":            100.0,
    "platform_tenure":         50.0,  # new = lower tenure score
}

# ── Reservation TTL ────────────────────────────────────────────────────────
RESERVATION_TTL_HOURS = 48

# ── Wallet pre-flight: minimum buffer multiplier ───────────────────────────
# Wallet must have at least 1.5× estimated commission to allow booking
WALLET_BUFFER_MULTIPLIER = Decimal("1.50")

# ── Badge qualification thresholds ────────────────────────────────────────
BADGE_THRESHOLDS = {
    "platinum":      {"health_score_min": 90.0, "days_required": 30},
    "top_rated":     {"min_rating": 4.8, "min_reviews": 50},
    "fast_response": {"max_response_minutes": 30, "min_jobs": 100},
    "warranty_free": {"max_claims": 0, "lookback_days": 180},
    "verified":      {"documents_verified": True},
}

# ── Wallet transaction types ───────────────────────────────────────────────
class TxnType:
    PURCHASE               = "purchase"
    COMMISSION             = "commission"
    MANUAL_DEDUCT          = "manual_deduct"
    MANUAL_CREDIT          = "manual_credit"
    REFUND                 = "refund"
    WARRANTY_DRAW          = "warranty_draw"
    RESERVATION_CREATE     = "reservation_create"
    RESERVATION_RELEASE    = "reservation_release"
    RESERVATION_FORFEIT    = "reservation_forfeit"
    RESERVATION_EXPIRED    = "reservation_expired"
    RESERVATION_CONFIRM    = "reservation_confirm"

# ── Deposit transaction types ──────────────────────────────────────────────
# ── Redis key prefixes ─────────────────────────────────────────────────────
REDIS_WALLET_LOCK    = "serviceos:commerce:wallet_lock:{tenant_id}"
REDIS_PREFLIGHT      = "serviceos:commerce:preflight:{tenant_id}"
REDIS_COMMISSION_RATE = "serviceos:commerce:commission_rate:{tenant_id}"
REDIS_CUSTOMER_HEALTH = "serviceos:commerce:cust_health:{tenant_id}:{customer_id}"

# ── Rate limits ────────────────────────────────────────────────────────────
RATE_LIMIT_PURCHASE_INITIATE = (3600, 5)   # 5 per hour per tenant
RATE_LIMIT_WARRANTY_CLAIM    = (86400, 3)  # 3 per day per customer per tenant
RATE_LIMIT_PREFLIGHT         = (3600, 1000)
