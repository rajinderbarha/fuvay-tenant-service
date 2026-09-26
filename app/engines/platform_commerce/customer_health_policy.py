"""Governed runtime policy for evidence-based customer health."""
from __future__ import annotations

import structlog

from app.engines.settings_engine.configuration_service import ConfigurationService


logger = structlog.get_logger("platform_commerce.customer_health_policy")

DEFAULT_PAYMENT_WEIGHT_PERCENTAGE = 80
DEFAULT_MINIMUM_EVIDENCE_EVENTS = 1
DEFAULT_NEUTRAL_PRIOR_SCORE = 80


async def resolve_customer_health_policy(db) -> dict:
    """Resolve the live admin policy, with safe code defaults on read failure.

    A single payment-weight control makes the two weights impossible to drift
    away from 100%.  The behaviour weight is always its complement.
    """
    values = {
        "customer_health_payment_weight_percentage": DEFAULT_PAYMENT_WEIGHT_PERCENTAGE,
        "customer_health_minimum_evidence_events": DEFAULT_MINIMUM_EVIDENCE_EVENTS,
        "customer_health_neutral_prior_score": DEFAULT_NEUTRAL_PRIOR_SCORE,
    }
    service = ConfigurationService(db, request_id="customer-health-runtime")
    for key in tuple(values):
        try:
            resolved = await service.resolve_effective_value(key, vertical_key="home_services")
            values[key] = resolved["effective_value"]
        except Exception as exc:  # configuration availability must not block dispatch
            logger.warning("customer_health.policy_fallback", key=key, error=str(exc))

    payment_pct = min(95, max(51, int(values["customer_health_payment_weight_percentage"])))
    minimum_evidence = min(20, max(1, int(values["customer_health_minimum_evidence_events"])))
    neutral_prior = min(90.0, max(60.0, float(values["customer_health_neutral_prior_score"])))
    return {
        "payment_weight": payment_pct / 100.0,
        "behavior_weight": (100 - payment_pct) / 100.0,
        "payment_weight_percentage": payment_pct,
        "behavior_weight_percentage": 100 - payment_pct,
        "minimum_evidence_events": minimum_evidence,
        "neutral_prior_score": neutral_prior,
    }
