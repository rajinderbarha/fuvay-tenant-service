"""
ServiceOS — Middleware Stack
Order (last registered = first executed):
  RequestID → StructuredLogging → UsageQuota → Idempotency → CORS → SecurityHeaders

Rate limiting is applied inside route handlers via core/security.py
(not as middleware, so it can be per-endpoint with correct identifiers).
Daily API-call quota counting IS middleware (see UsageQuotaMiddleware) since
it's a blanket per-tenant counter across all routes, not endpoint-specific.
"""
import time
import uuid
import json
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.logging import bind_request_context, clear_request_context

logger = structlog.get_logger("middleware")

# Write methods that support idempotency
IDEMPOTENCY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request_id to every request.
    Honors X-Request-ID if client sends one (distributed tracing).
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = (
            request.headers.get("X-Request-ID")
            or f"req_{uuid.uuid4().hex[:12]}"
        )
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-ServiceOS-Version"] = get_settings().APP_VERSION
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Every log line carries request_id, tenant_id, user_id, engine_id."""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        tenant_id = request.headers.get("X-Tenant-ID")
        user_id = request.headers.get("X-User-ID")
        request_id = getattr(request.state, "request_id", "—")

        bind_request_context(request_id=request_id, tenant_id=tenant_id, user_id=user_id)

        try:
            response = await call_next(request)
        except Exception:
            clear_request_context()
            raise

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            request_id=request_id,
            tenant_id=tenant_id or "—",
        )
        clear_request_context()
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response


class UsageQuotaMiddleware(BaseHTTPMiddleware):
    """Counts API calls per tenant per day in Redis (TTL'd to auto-reset at
    next UTC midnight — see app/core/usage_quota.py). Counting only: actual
    enforcement happens at TenantService.check_limit() call sites, matching
    this app's existing pattern of blocking at specific business actions
    rather than via a blanket per-request 429 on arbitrary routes."""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            try:
                from app.redis_client import get_redis
                from app.core.usage_quota import increment_api_calls
                await increment_api_calls(get_redis(), tenant_id)
            except Exception as e:
                logger.warning("usage_quota.increment_failed", error=str(e))
        return await call_next(request)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Idempotency key middleware for write endpoints.
    If X-Idempotency-Key is present and we've seen it before,
    return the cached response immediately without re-processing.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        idempotency_key = request.headers.get("X-Idempotency-Key")

        if not idempotency_key or request.method not in IDEMPOTENCY_METHODS:
            return await call_next(request)

        # Scope the key to tenant + endpoint for safety
        tenant_id = request.headers.get("X-Tenant-ID", "platform")
        scoped_key = f"{tenant_id}:{request.url.path}:{idempotency_key}"

        try:
            from app.core.security import idempotency_store
            cached = await idempotency_store.get(scoped_key)
            if cached:
                logger.info(
                    "idempotency.cache_hit",
                    key=idempotency_key[:8] + "...",
                    path=request.url.path,
                )
                cached_body = cached["body"]
                if isinstance(cached_body, dict):
                    cached_body["meta"] = {**cached_body.get("meta", {}), "idempotent": True}
                response = JSONResponse(
                    status_code=cached["status_code"],
                    content=cached_body,
                )
                response.headers["X-Idempotency-Replayed"] = "true"
                response.headers["X-Idempotency-Key"] = idempotency_key
                return response
        except Exception as e:
            logger.warning("idempotency.check_failed", error=str(e))

        response = await call_next(request)

        # Cache successful responses (2xx)
        if 200 <= response.status_code < 300:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk
                body = json.loads(body_bytes.decode())
                from app.core.security import idempotency_store
                await idempotency_store.store(scoped_key, response.status_code, body)
                response = JSONResponse(
                    status_code=response.status_code,
                    content=body,
                    headers=dict(response.headers),
                )
                response.headers["X-Idempotency-Key"] = idempotency_key
            except Exception as e:
                logger.warning("idempotency.store_failed", error=str(e))

        return response


def register_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order."""
    settings = get_settings()

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID", "X-ServiceOS-Version",
            "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset",
            "X-Idempotency-Key", "X-Idempotency-Replayed",
        ],
    )
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(UsageQuotaMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
