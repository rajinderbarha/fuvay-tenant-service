"""
GET /health      — Load balancer / uptime health check (fast)
GET /v1/health   — Same check, versioned alias for API clients
GET /v1/ready    — Readiness: confirms DB + Redis are live before accepting traffic
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import get_session_factory
from app.engine_registry.registry import registry
from app.redis_client import get_redis
from app.schemas.health import HealthResponse, ServiceHealth

router = APIRouter(tags=["Health"])

_start_time = time.monotonic()


async def _build_health() -> tuple[HealthResponse, bool]:
    """Shared logic for both /health and /v1/health."""
    settings = get_settings()
    services: list[ServiceHealth] = []

    # ── Database ───────────────────────────────────────────────────
    try:
        factory = get_session_factory()
        t0 = time.perf_counter()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - t0) * 1000, 2)
        services.append(ServiceHealth(service="postgresql", status="ok", latency_ms=db_latency))
    except Exception as e:
        services.append(ServiceHealth(service="postgresql", status="down", detail=str(e)))

    # ── Redis ──────────────────────────────────────────────────────
    try:
        r = get_redis()
        t0 = time.perf_counter()
        await r.ping()
        redis_latency = round((time.perf_counter() - t0) * 1000, 2)
        services.append(ServiceHealth(service="redis", status="ok", latency_ms=redis_latency))
    except Exception as e:
        services.append(ServiceHealth(service="redis", status="down", detail=str(e)))

    any_down = any(s.status == "down" for s in services)
    any_degraded = any(s.status == "degraded" for s in services)
    overall = "down" if any_down else ("degraded" if any_degraded else "ok")

    response = HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.monotonic() - _start_time, 2),
        services=services,
        engines=registry.summary(),
    )
    return response, any_down


@router.get(
    "/health",
    summary="Platform health check",
    response_model=HealthResponse,
    include_in_schema=True,
)
async def health_check() -> HealthResponse:
    result, _ = await _build_health()
    return result


@router.get(
    "/v1/health",
    summary="Platform health check (versioned alias)",
    response_model=HealthResponse,
    include_in_schema=True,
)
async def health_check_v1() -> HealthResponse:
    result, _ = await _build_health()
    return result


@router.get(
    "/v1/ready",
    summary="Readiness check — returns 200 only when DB and Redis are reachable",
    include_in_schema=True,
    tags=["Health"],
)
async def readiness_check() -> JSONResponse:
    """
    Used by orchestrators (k8s, ECS, Railway) to gate traffic.
    Returns 200 if ready, 503 if any critical dependency is down.
    Does NOT include engine registry — that should not block readiness.
    """
    settings = get_settings()
    checks: dict[str, str] = {}
    ready = True

    # Database
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"down: {e}"
        ready = False

    # Redis
    try:
        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"down: {e}"
        ready = False

    # Config sanity — warn if using dev secrets in production
    if settings.is_production:
        dev_secrets = (
            "dev-secret-key" in settings.SECRET_KEY
            or "dev-jwt-secret" in settings.JWT_SECRET_KEY
        )
        checks["config"] = "WARNING: dev secrets detected in production" if dev_secrets else "ok"
        if dev_secrets:
            ready = False
    else:
        checks["config"] = "ok"

    payload = {
        "ready": ready,
        "service": "serviceos-api",
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)
