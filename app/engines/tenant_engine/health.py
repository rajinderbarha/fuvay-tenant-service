"""
Tenant Engine — Health Score Computation
7 signals → weighted composite → band → commission adjustment.
Signals are contributed by each engine via Redis.
Phase 2: stub signal readers (each engine writes real values in later phases).
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog

from app.engines.tenant_engine.constants import HEALTH_BANDS, HEALTH_SCORE_WEIGHTS, COMMISSION_ADJUSTMENT_BY_BAND

logger = structlog.get_logger("tenant.health")

# Redis key pattern for each signal per tenant
# Each engine writes: "serviceos:health:{tenant_id}:{signal_name}" → float 0-100
SIGNAL_REDIS_KEYS = {
    "job_completion_rate":   "serviceos:health:{tenant_id}:job_completion_rate",
    "customer_satisfaction": "serviceos:health:{tenant_id}:customer_satisfaction",
    "warranty_claim_rate":   "serviceos:health:{tenant_id}:warranty_claim_rate",
    "credit_wallet_health":  "serviceos:health:{tenant_id}:credit_wallet_health",
    "staff_compliance_rate": "serviceos:health:{tenant_id}:staff_compliance_rate",
    "response_time":         "serviceos:health:{tenant_id}:response_time",
    "platform_engagement":   "serviceos:health:{tenant_id}:platform_engagement",
}

# Defaults while signals haven't been contributed yet (new tenants start at Gold)
DEFAULT_SIGNAL_VALUES = {
    "job_completion_rate":   80.0,
    "customer_satisfaction": 80.0,
    "warranty_claim_rate":   90.0,
    "credit_wallet_health":  100.0,
    "staff_compliance_rate": 75.0,
    "response_time":         80.0,
    "platform_engagement":   70.0,
}


async def compute_health_score(tenant_id: uuid.UUID) -> dict:
    """
    Compute health score from Redis signal values.
    Falls back to defaults for missing signals (new tenants).
    Each engine writes its signals independently.
    """
    from app.redis_client import get_redis
    redis = get_redis()

    signals = {}
    for signal_name, key_pattern in SIGNAL_REDIS_KEYS.items():
        key = key_pattern.format(tenant_id=str(tenant_id))
        try:
            raw = await redis.get(key)
            signals[signal_name] = float(raw) if raw else DEFAULT_SIGNAL_VALUES[signal_name]
        except Exception:
            signals[signal_name] = DEFAULT_SIGNAL_VALUES[signal_name]

    # Weighted sum
    score = sum(
        signals[signal] * HEALTH_SCORE_WEIGHTS[signal]
        for signal in HEALTH_SCORE_WEIGHTS
        if signal in signals
    )
    score = round(min(100.0, max(0.0, score)), 2)

    # Determine band
    band = "at_risk"
    for band_name, (lo, hi) in HEALTH_BANDS.items():
        if lo <= score <= hi:
            band = band_name
            break

    commission_adj = COMMISSION_ADJUSTMENT_BY_BAND.get(band, 0.0)

    return {
        "score": score,
        "band": band,
        "commission_adjustment_pct": commission_adj,
        "effective_commission_note": (
            f"Base commission {'reduced by' if commission_adj < 0 else 'increased by'} "
            f"{abs(commission_adj)}% due to {band} health band."
        ) if commission_adj != 0 else "Base commission rate — no adjustment.",
        "signals": {
            name: {
                "value": round(val, 2),
                "weight": HEALTH_SCORE_WEIGHTS.get(name, 0),
                "contribution": round(val * HEALTH_SCORE_WEIGHTS.get(name, 0), 2),
            }
            for name, val in signals.items()
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "platinum": "90-100 → base commission - 1%",
            "gold": "75-89 → base commission",
            "silver": "60-74 → base commission + 2%",
            "bronze": "40-59 → base commission + 5%",
            "at_risk": "20-39 → base commission + 10% + advance commission required",
            "critical": "0-19 → base commission + 10% + mandatory admin review",
        },
    }


async def write_health_signal(tenant_id: uuid.UUID, signal_name: str, value: float, ttl_hours: int = 2) -> None:
    """Called by each engine to update its health signal."""
    from app.redis_client import get_redis
    redis = get_redis()
    if signal_name not in SIGNAL_REDIS_KEYS:
        logger.warning("health.unknown_signal", signal=signal_name)
        return
    key = SIGNAL_REDIS_KEYS[signal_name].format(tenant_id=str(tenant_id))
    await redis.setex(key, ttl_hours * 3600, str(round(max(0.0, min(100.0, value)), 2)))
