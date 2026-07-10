"""
ServiceOS — Structured Logging
Every log line carries: request_id, tenant_id, engine_id, user_id, env.
Uses structlog for machine-parseable JSON in production, pretty-print in dev.
"""
import logging
import sys
from typing import Any

import structlog
from app.core.pii_filter import mask_pii_processor
from structlog.contextvars import merge_contextvars, clear_contextvars, bind_contextvars

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON for log aggregators (Loki, CloudWatch, Datadog)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            mask_pii_processor,
        structlog.processors.JSONRenderer(),
        ]
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # Pretty-print for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
        handler = logging.StreamHandler(sys.stdout)

    # Configure stdlib logging (uvicorn, sqlalchemy, etc.)
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        handlers=[handler],
        format="%(message)s",
    )

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "serviceos") -> structlog.BoundLogger:
    return structlog.get_logger(name)


# Context helpers used by middleware
def bind_request_context(
    request_id: str,
    tenant_id: str | None = None,
    user_id: str | None = None,
    engine_id: str | None = None,
) -> None:
    bind_contextvars(
        request_id=request_id,
        tenant_id=tenant_id or "—",
        user_id=user_id or "—",
        engine_id=engine_id or "—",
    )


def clear_request_context() -> None:
    clear_contextvars()
