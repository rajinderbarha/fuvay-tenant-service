"""
Fuvay — Middleware Stack
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
import ipaddress
from datetime import datetime, timezone
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
        response.headers["X-Fuvay-Version"] = get_settings().APP_VERSION
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


class IPBlocklistMiddleware(BaseHTTPMiddleware):
    """Enforce the Security workspace blocklist on the request hot path.

    Redis narrows the request to an exact-IP/CIDR candidate.  Only a blocked
    candidate touches PostgreSQL, where expiry and role/tenant scope are
    verified and the append-only hit record is written.  Normal traffic stays
    O(1) and does not consume a database connection.
    """

    EXEMPT_PATHS = {"/health", "/ready", "/metrics"}

    @staticmethod
    def _actor_scope(request: Request) -> tuple[str | None, str | None]:
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return None, request.headers.get("X-Tenant-ID")
        try:
            from app.engines.auth.utils import decode_token
            payload = decode_token(auth.split(" ", 1)[1])
            return payload.get("role"), payload.get("tenant_id") or request.headers.get("X-Tenant-ID")
        except Exception:
            return None, request.headers.get("X-Tenant-ID")

    @staticmethod
    def _scope_matches(scope: str, role: str | None, tenant_id: str | None,
                       entry_tenant_id: str | None) -> bool:
        if scope == "all":
            return True
        if scope == "admin":
            return bool(role and (role == "super_admin" or role.startswith("admin_")))
        if scope in {"customer", "staff"}:
            return role == scope
        if scope == "tenant":
            return bool(entry_tenant_id and tenant_id == entry_tenant_id)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        from app.core.security import get_client_ip
        ip = get_client_ip(request)
        if not ip:
            return await call_next(request)
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return await call_next(request)

        candidates: list[str] = []
        try:
            from app.redis_client import get_redis
            redis = get_redis()
            if await redis.sismember("serviceos:security:ip_blocklist", ip):
                candidates.append(ip)
            for raw in await redis.smembers("serviceos:security:cidr_blocklist"):
                cidr = raw.decode() if isinstance(raw, bytes) else str(raw)
                try:
                    if address in ipaddress.ip_network(cidr, strict=False):
                        candidates.append(cidr)
                except ValueError:
                    continue
        except Exception:
            return await call_next(request)  # monitored fail-open if Redis is unavailable

        if not candidates:
            return await call_next(request)

        try:
            from sqlalchemy import select
            from app.database import get_db_session
            from app.engines.security.models import IPBlocklistEntry, IPBlockHit

            role, tenant_id = self._actor_scope(request)
            now = datetime.now(timezone.utc)
            async with get_db_session() as db:
                result = await db.execute(select(IPBlocklistEntry).where(
                    IPBlocklistEntry.ip_or_cidr.in_(candidates),
                    IPBlocklistEntry.status == "active",
                ).order_by(IPBlocklistEntry.is_global.desc(), IPBlocklistEntry.created_at.desc()))
                matched = None
                for entry in result.scalars().all():
                    if entry.expires_at and entry.expires_at <= now:
                        entry.status = "expired"
                        entry.is_active = False
                        try:
                            redis_set = "serviceos:security:ip_blocklist" if entry.entry_type == "ip" else "serviceos:security:cidr_blocklist"
                            await redis.srem(redis_set, entry.ip_or_cidr)
                        except Exception:
                            pass
                        continue
                    if self._scope_matches(entry.scope, role, tenant_id,
                                           str(entry.tenant_id) if entry.tenant_id else None):
                        matched = entry
                        break
                if matched is not None:
                    matched.hit_count += 1
                    matched.last_hit_at = now
                    db.add(IPBlockHit(
                        block_id=matched.id, ip_or_cidr=matched.ip_or_cidr,
                        hit_at=now, path=request.url.path, method=request.method,
                        user_agent=request.headers.get("user-agent"), blocked_scope=matched.scope,
                    ))
                    block_reference = str(matched.id)
            if matched is None:
                return await call_next(request)
        except Exception as exc:
            logger.error("security.ip_block_enforcement_failed", error=str(exc), ip=ip)
            return await call_next(request)

        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "error_code": "IP_BLOCKED",
                    "detail": "This network is blocked by platform security policy.",
                    "resolution": "Contact platform support and provide the request ID.",
                },
                "meta": {"block_reference": block_reference},
            },
        )


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
            "X-Request-ID", "X-Fuvay-Version",
            "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset",
            "X-Idempotency-Key", "X-Idempotency-Replayed",
            # CSV exports are capped server-side and report the cap through
            # these. A header the browser cannot read is a header the UI cannot
            # act on: without exposing them, an admin whose export was truncated
            # was told nothing and walked away believing a partial CSV was the
            # complete record.
            "X-Export-Total", "X-Export-Truncated",
        ],
    )
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(UsageQuotaMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(IPBlocklistMiddleware)
    app.add_middleware(RequestIDMiddleware)
