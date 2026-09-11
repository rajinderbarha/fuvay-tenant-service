"""
Tenant Engine — Health Score Computation
7 signals → weighted composite → band → commission adjustment.
Most signals are contributed by each engine via Redis. usage_credit_health
(FINAL-L5-05J, formerly credit_wallet_health) is computed directly from
tenant_billing.credit_balance instead — its only prior writer
(CommerceService._update_wallet_signal) was unreachable in practice
(gated on the legacy field_ops jobs table, 0 real rows), so the signal
always silently defaulted to 100.0 for every tenant. See
docs/final-l5-05/FINAL_L5_05J_TENANT_HEALTH_REPAIR.md.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog

from app.engines.tenant_engine.constants import HEALTH_BANDS, HEALTH_SCORE_WEIGHTS, COMMISSION_ADJUSTMENT_BY_BAND

logger = structlog.get_logger("tenant.health")

# Redis key pattern for each signal per tenant
# Each engine writes: "serviceos:health:{tenant_id}:{signal_name}" → float 0-100
# usage_credit_health is intentionally excluded — computed live, not cached.
SIGNAL_REDIS_KEYS = {
    "job_completion_rate":   "serviceos:health:{tenant_id}:job_completion_rate",
    "customer_satisfaction": "serviceos:health:{tenant_id}:customer_satisfaction",
    "warranty_claim_rate":   "serviceos:health:{tenant_id}:warranty_claim_rate",
    "staff_compliance_rate": "serviceos:health:{tenant_id}:staff_compliance_rate",
    "response_time":         "serviceos:health:{tenant_id}:response_time",
    "platform_engagement":   "serviceos:health:{tenant_id}:platform_engagement",
}

# Defaults while signals haven't been contributed yet (new tenants start at Gold)
DEFAULT_SIGNAL_VALUES = {
    "job_completion_rate":   80.0,
    "customer_satisfaction": 80.0,
    "warranty_claim_rate":   90.0,
    "staff_compliance_rate": 75.0,
    "response_time":         80.0,
    "platform_engagement":   70.0,
}


async def _compute_usage_credit_health(db, tenant_id: uuid.UUID) -> tuple[float, dict]:
    """Deterministic, real-data signal: 100 at/above threshold, scaling
    linearly to 0 at/below zero balance. Missing tenant_billing record is
    handled honestly (0.0, not a silent 100 default)."""
    from app.engines.usage_credits.constants import DEFAULT_LOW_USAGE_CREDIT_THRESHOLD
    from app.engines.usage_credits.service import UsageCreditService

    svc = UsageCreditService(db)
    check = await svc.check_threshold(tenant_id, DEFAULT_LOW_USAGE_CREDIT_THRESHOLD)
    balance = Decimal(str(check["balance"]))
    threshold = Decimal(str(check["threshold"]))

    if not check["has_billing_record"]:
        score = 0.0
    elif threshold <= 0:
        score = 100.0
    elif balance >= threshold:
        score = 100.0
    elif balance <= 0:
        score = 0.0
    else:
        score = float((balance / threshold) * 100)

    return round(score, 2), {
        "balance": float(balance), "threshold": float(threshold),
        "has_billing_record": check["has_billing_record"],
        "source": "tenant_billing.credit_balance",
    }


def _resolve_health_band(score: float) -> str:
    """Resolve decimal scores without gaps between the configured bands.

    ``HEALTH_BANDS`` is also used for human-readable integer ranges such as
    75-89 and 90-100. Comparing a decimal score to both endpoints left values
    such as 89.5 unmatched and incorrectly fell them back to ``at_risk``.
    The lower bound is the actual policy threshold, so evaluate thresholds in
    descending order and let the next band own every value below it.
    """
    for band_name, (lower_bound, _upper_bound) in sorted(
        HEALTH_BANDS.items(), key=lambda item: item[1][0], reverse=True
    ):
        if score >= lower_bound:
            return band_name
    return "critical"


async def compute_health_score(tenant_id: uuid.UUID, db=None) -> dict:
    """
    Compute health score. usage_credit_health is read live from
    tenant_billing.credit_balance when a db session is provided; falls
    back to the old default only when no db session is available (should
    not happen in the real request path — every caller now passes db).
    All other 6 signals still come from Redis, unchanged.
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

    usage_credit_detail = None
    if db is not None:
        signals["usage_credit_health"], usage_credit_detail = await _compute_usage_credit_health(db, tenant_id)
    else:
        signals["usage_credit_health"] = DEFAULT_SIGNAL_VALUES.get("job_completion_rate", 80.0)

    # Weighted sum
    score = sum(
        signals[signal] * HEALTH_SCORE_WEIGHTS[signal]
        for signal in HEALTH_SCORE_WEIGHTS
        if signal in signals
    )
    score = round(min(100.0, max(0.0, score)), 2)

    # Determine band
    band = _resolve_health_band(score)

    # ``tenants.health_score`` / ``health_band`` power the Admin tenant list,
    # detail view, filters, exports and aggregate dashboard. Previously the
    # live endpoint returned the newly calculated value but never updated that
    # canonical projection, so Admin could show 100 while the same tenant saw
    # 83.5. Persist in the caller's transaction whenever a real DB session is
    # available; FastAPI's DB dependency commits only after a successful
    # response, keeping the calculation and projection atomic.
    if db is not None:
        from sqlalchemy import update
        from app.engines.tenant_engine.models import Tenant

        await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(health_score=Decimal(str(score)), health_band=band)
        )

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
                **({"detail": usage_credit_detail} if name == "usage_credit_health" and usage_credit_detail else {}),
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


async def refresh_provider_operational_health(db, tenant_id: uuid.UUID) -> dict:
    """Refresh cancellation/response signals from canonical job history.

    Provider-initiated cancellations and 30-minute assignment timeouts are
    intentionally distinguished from customer cancellations. A small prior
    prevents one early incident from collapsing a new provider to zero while
    still making every incident visibly reduce health.
    """
    from sqlalchemy import text

    try:
        import inspect
        nested = db.begin_nested()
        if inspect.iscoroutine(nested):
            nested = await nested
        async with nested:
            row = (await db.execute(text("""
                SELECT
                  (SELECT count(*) FROM service_jobs
                   WHERE tenant_id=:tid AND status='completed') AS completed,
                  (SELECT count(DISTINCT job_id) FROM service_job_execution_events
                   WHERE tenant_id=:tid AND event_type='job_cancelled'
                     AND actor_role='provider') AS provider_cancelled,
                  (SELECT count(DISTINCT job_id) FROM service_job_execution_events
                   WHERE tenant_id=:tid AND event_type='provider_assignment_timeout') AS assignment_timeouts
            """), {"tid": str(tenant_id)})).mappings().first()
            completed = int((row or {}).get("completed") or 0)
            cancelled = int((row or {}).get("provider_cancelled") or 0)
            timeouts = int((row or {}).get("assignment_timeouts") or 0)
            prior = 4
            completion_score = round(100.0 * (completed + prior) / (completed + cancelled + prior), 2)
            response_score = round(100.0 * prior / (timeouts + prior), 2)
            await write_health_signal(tenant_id, "job_completion_rate", completion_score, ttl_hours=24)
            await write_health_signal(tenant_id, "response_time", response_score, ttl_hours=24)
            health = await compute_health_score(tenant_id, db=db)
    except Exception as exc:  # health telemetry must never strand job cancellation
        logger.warning("health.operational_refresh_failed", tenant_id=str(tenant_id), error=str(exc))
        return {"updated": False}
    return {
        "updated": True, "score": health["score"], "band": health["band"],
        "completion_score": completion_score, "response_score": response_score,
        "provider_cancellations": cancelled, "assignment_timeouts": timeouts,
    }
