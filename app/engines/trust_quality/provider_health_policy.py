"""Governed rolling-evidence policy for canonical provider health."""
from __future__ import annotations

import structlog

from app.engines.settings_engine.configuration_service import ConfigurationService


logger = structlog.get_logger("trust_quality.provider_health_policy")

DEFAULT_HISTORY_WINDOW_DAYS = 180
DEFAULT_RESCHEDULE_GRACE_COUNT = 3
DEFAULT_CONFIDENCE_PRIOR_JOBS = 5
DEFAULT_RATING_PRIOR_COUNT = 5
DEFAULT_NEUTRAL_RATING_SCORE = 80.0


async def resolve_provider_health_policy(db) -> dict:
    values = {
        "provider_health_history_window_days": DEFAULT_HISTORY_WINDOW_DAYS,
        "provider_health_reschedule_grace_count": DEFAULT_RESCHEDULE_GRACE_COUNT,
        "provider_health_confidence_prior_jobs": DEFAULT_CONFIDENCE_PRIOR_JOBS,
        "provider_health_rating_prior_count": DEFAULT_RATING_PRIOR_COUNT,
        "provider_health_neutral_rating_score": DEFAULT_NEUTRAL_RATING_SCORE,
    }
    service = ConfigurationService(db, request_id="provider-health-runtime")
    for key in tuple(values):
        try:
            resolved = await service.resolve_effective_value(key, vertical_key="home_services")
            values[key] = resolved["effective_value"]
        except Exception as exc:  # trust telemetry must never block operations
            logger.warning("provider_health.policy_fallback", key=key, error=str(exc))
    return {
        "history_window_days": min(730, max(30, int(values["provider_health_history_window_days"]))),
        "reschedule_grace_count": min(20, max(0, int(values["provider_health_reschedule_grace_count"]))),
        "confidence_prior_jobs": min(50, max(1, int(values["provider_health_confidence_prior_jobs"]))),
        "rating_prior_count": min(50, max(1, int(values["provider_health_rating_prior_count"]))),
        "neutral_rating_score": min(90.0, max(60.0, float(values["provider_health_neutral_rating_score"]))),
    }


def smoothed_provider_outcomes(done: int, cancelled: int, prior_jobs: int) -> dict:
    """Completion/cancellation rates with a transparent successful prior."""
    done = max(0, int(done))
    cancelled = max(0, int(cancelled))
    prior = max(1, int(prior_jobs))
    terminal = done + cancelled
    if not terminal:
        return {"terminal_jobs_count": 0}
    denominator = terminal + prior
    return {
        "terminal_jobs_count": terminal,
        "job_completion_rate": round((done + prior) * 100.0 / denominator, 2),
        "cancellation_rate": round(cancelled * 100.0 / denominator, 2),
    }


def smoothed_rating_score(
    average_rating: float, review_count: int, prior_count: int, neutral_score: float,
) -> float:
    observed_score = max(0.0, min(100.0, float(average_rating) * 20.0))
    reviews = max(0, int(review_count))
    prior = max(1, int(prior_count))
    return round(
        (observed_score * reviews + float(neutral_score) * prior) / (reviews + prior),
        2,
    )


def provider_reschedule_metrics(
    approved_provider_reschedules: int,
    terminal_jobs: int,
    grace_count: int,
    prior_jobs: int,
) -> dict:
    """First N approved provider changes are neutral; customer changes never enter."""
    total = max(0, int(approved_provider_reschedules))
    grace = max(0, int(grace_count))
    excess = max(0, total - grace)
    baseline = max(0, int(terminal_jobs)) + max(1, int(prior_jobs))
    score = round(baseline * 100.0 / (baseline + excess), 2)
    return {
        "provider_reschedule_count": total,
        "provider_reschedule_grace_count": grace,
        "provider_reschedule_grace_remaining": max(0, grace - total),
        "provider_reschedules_over_grace": excess,
        "provider_reschedule_score": score,
    }
