"""
Fuvay — Observability
Prometheus metrics + Sentry error tracking.
Import setup_observability() in main.py startup.
"""
from __future__ import annotations
import os
import structlog

logger = structlog.get_logger("observability")


def setup_prometheus(app) -> None:
    """Attach Prometheus metrics endpoint (/metrics) to the FastAPI app."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/health", "/metrics", "/docs", "/openapi.json"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="serviceos_requests_inprogress",
            inprogress_labels=True,
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("prometheus.enabled", endpoint="/metrics")
    except ImportError:
        logger.warning("prometheus.not_installed", hint="pip install prometheus-fastapi-instrumentator")


def setup_sentry() -> None:
    """Initialise Sentry SDK if SENTRY_DSN is set."""
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        logger.info("sentry.disabled", reason="SENTRY_DSN not set")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("APP_ENV", "production"),
            release=os.environ.get("APP_VERSION", "unknown"),
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", "0.1")),
            profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_RATE", "0.05")),
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            before_send=_scrub_pii,
        )
        logger.info("sentry.enabled", environment=os.environ.get("APP_ENV", "production"))
    except ImportError:
        logger.warning("sentry.not_installed", hint="pip install sentry-sdk[fastapi]")


def _scrub_pii(event: dict, hint: dict) -> dict | None:
    """Strip PII from Sentry events before sending."""
    PII_KEYS = {
        "password", "token", "secret", "authorization",
        "phone", "email", "aadhaar", "pan",
        "api_key", "access_token", "refresh_token",
    }
    def _scrub(obj):
        if isinstance(obj, dict):
            return {
                k: "[Filtered]" if k.lower() in PII_KEYS else _scrub(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_scrub(i) for i in obj]
        return obj
    return _scrub(event)
