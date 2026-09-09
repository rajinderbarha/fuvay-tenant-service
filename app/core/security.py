"""
Fuvay — Security Utilities
Rate limiting (sliding window via Redis Lua), idempotency key handling,
IP-based threat detection, security event publishing.
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings

logger = structlog.get_logger("security")

# ── Rate Limiter ──────────────────────────────────────────────────────────────
# Sliding window via a single Redis Lua script — atomic, no race conditions
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local window_ms = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - window_ms

redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_at = tonumber(oldest[2]) + window_ms
    return {0, count, reset_at}
end
redis.call('ZADD', key, now, ARGV[4])
redis.call('EXPIRE', key, math.ceil(window_ms / 1000))
return {1, count + 1, now + window_ms}
"""

# Rate limit configs: (window_seconds, max_requests)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    # Auth endpoints — strict
    "auth:login":            (900,  30),   # 30 per 15 min per IP
    "auth:login_account":    (900,  10),   # 10 per 15 min per account
    "auth:login_phone":      (3600, 5),    # 5 per hour
    "auth:otp_send":         (3600, 3),    # 3 per hour per recipient
    "auth:otp_send_ip":      (3600, 10),   # 10 per hour per source IP
    "auth:otp_send_source":  (3600, 5),    # 5 per hour per device/social identity
    "auth:otp_daily_recipient": (86400, 5),
    "auth:otp_daily_ip":     (86400, 20),
    "auth:otp_daily_source": (86400, 20),
    "auth:otp_daily_global": (86400, 1000),
    "auth:otp_verify":       (300,  5),    # 5 per 5 min
    "auth:otp_verify_ip":    (300,  20),   # 20 per 5 min per source IP
    "auth:otp_verify_source":(300,  8),    # 8 per 5 min per device/social identity
    "auth:password_reset":   (3600, 3),    # 3 per hour
    "auth:refresh":          (3600, 60),   # 60 per hour
    "auth:mfa_verify":       (300,  5),    # 5 per 5 min
    "auth:register":         (3600, 3),    # 3 per hour per IP
    "booking:draft_user":    (900, 5),
    "booking:draft_ip":      (900, 20),
    "booking:answer_user":   (60, 60),
    "booking:confirm_user":  (86400, 5),
    "booking:confirm_ip":    (86400, 20),
    "booking:social_message": (600, 30),
    "booking:social_draft":  (3600, 5),
    #: A social sender may open this many fresh booking conversations per hour.
    #: `/fuvay` is the most expensive inbound message there is -- it resets the
    #: draft, re-reads the serviceable catalog and sends TWO outbound messages
    #: -- so the message limit above is not by itself a meaningful guard.
    "booking:social_session": (3600, 6),
    #: At most one "you are going too fast" reply per sender per window. The
    #: flood itself is dropped silently; going completely quiet just makes a
    #: real customer retry harder, so one notice is cheaper than the retries.
    "booking:social_notice": (600, 1),
    #: Whole-channel ceiling. Every limit above is per sender, and an Instagram
    #: id costs nothing to create, so a handful of throwaway accounts multiply
    #: the per-sender budget with nothing to stop them.
    "booking:social_channel": (600, 2000),
    # Found missing during the "make it 100% working" pass -- real,
    # tested rate-limit types for account-security-sensitive actions.
    "auth:password_change":  (3600, 10),   # 10 per hour per account
    "auth:mfa_confirm":      (300,  5),    # 5 per 5 min
    "auth:mfa_disable":      (3600, 5),    # 5 per hour per account
    # API endpoints — by tenant
    "api:read":              (60,   300),  # 300 reads per minute per tenant
    "api:write":             (60,   100),  # 100 writes per minute per tenant
    "api:ai":                (60,   20),   # 20 AI calls per minute (expensive)
    "api:export":            (3600, 5),    # 5 exports per hour
    # Webhook
    "webhook:delivery":      (60,   1000), # 1000/min per tenant
}

# Dev-only override: local testing (repeated manual OTP send/verify/register
# attempts against the same phone number) hits the strict production limits
# above almost immediately. Applied only when APP_ENV is development/testing
# (see RateLimiter.check) -- production and staging always use RATE_LIMITS
# unchanged.
DEV_RATE_LIMIT_OVERRIDES: dict[str, tuple[int, int]] = {
    "auth:login":         (900, 500),
    "auth:login_account": (900, 200),
    "auth:login_phone":   (3600, 100),
    "auth:otp_send":    (3600, 100),
    "auth:otp_send_ip": (3600, 500),
    "auth:otp_send_source": (3600, 500),
    "auth:otp_daily_recipient": (86400, 500),
    "auth:otp_daily_ip": (86400, 2000),
    "auth:otp_daily_source": (86400, 2000),
    "auth:otp_daily_global": (86400, 100000),
    "auth:otp_verify":  (300,  100),
    "auth:otp_verify_ip": (300, 1000),
    "auth:otp_verify_source": (300, 1000),
    "auth:register":    (3600, 100),
    "booking:draft_user": (900, 500),
    "booking:draft_ip": (900, 2000),
    "booking:answer_user": (60, 5000),
    "booking:confirm_user": (86400, 500),
    "booking:confirm_ip": (86400, 2000),
    "booking:social_message": (600, 5000),
    "booking:social_draft": (3600, 500),
    "booking:social_session": (3600, 500),
    "booking:social_notice": (600, 500),
    "booking:social_channel": (600, 100000),
}


class RateLimiter:
    """Sliding window rate limiter using Redis sorted sets + Lua script."""

    def __init__(self) -> None:
        self._script_sha: str | None = None

    async def _get_redis(self):
        from app.redis_client import get_redis
        return get_redis()

    async def _load_script(self, redis):
        if not self._script_sha:
            self._script_sha = await redis.script_load(_RATE_LIMIT_SCRIPT)
        return self._script_sha

    async def check(
        self,
        limit_key: str,
        limit_type: str,
        identifier: str,
        *,
        fail_closed: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Returns (is_allowed, headers_dict).
        headers_dict contains X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        """
        try:
            redis = await self._get_redis()
            from app.config import get_settings
            settings = get_settings()
            if settings.APP_ENV in ("development", "testing") and limit_type in DEV_RATE_LIMIT_OVERRIDES:
                config = DEV_RATE_LIMIT_OVERRIDES[limit_type]
            else:
                config = RATE_LIMITS.get(limit_type, (60, 100))
                dynamic_limits = {
                    "auth:otp_daily_recipient": (86400, settings.OTP_DAILY_RECIPIENT_LIMIT),
                    "auth:otp_daily_ip": (86400, settings.OTP_DAILY_IP_LIMIT),
                    "auth:otp_daily_source": (86400, settings.OTP_DAILY_SOURCE_LIMIT),
                    "auth:otp_daily_global": (86400, settings.OTP_DAILY_GLOBAL_LIMIT),
                    "booking:confirm_user": (86400, settings.BOOKING_MAX_CONFIRMATIONS_PER_DAY),
                }
                config = dynamic_limits.get(limit_type, config)
            window, limit = config
            now_ms = int(time.time() * 1000)
            redis_key = f"serviceos:ratelimit:{limit_key}:{identifier}"
            entry_id = str(uuid.uuid4())

            sha = await self._load_script(redis)
            result = await redis.evalsha(sha, 1, redis_key, window * 1000, limit, now_ms, entry_id)
            allowed, count, reset_ms = int(result[0]), int(result[1]), int(result[2])
            reset_at = int(reset_ms / 1000)

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - count)),
                "X-RateLimit-Reset": str(reset_at),
                "X-RateLimit-Window": str(window),
            }
            return bool(allowed), headers

        except Exception as e:
            logger.warning("rate_limiter.redis_error", error=str(e))
            if fail_closed:
                from app.exceptions import ServiceOSException
                raise ServiceOSException(
                    error_code="SECURITY_CONTROL_UNAVAILABLE",
                    detail="This security-sensitive action is temporarily unavailable.",
                    status_code=503,
                    resolution="Please wait a moment and try again.",
                ) from e
            return True, {}

    async def check_and_raise(
        self, limit_key: str, limit_type: str, identifier: str, *, fail_closed: bool = False
    ) -> dict:
        """Raises 429 ServiceOSException if rate limited."""
        from app.exceptions import ServiceOSException
        allowed, headers = await self.check(
            limit_key, limit_type, identifier, fail_closed=fail_closed
        )
        if not allowed:
            reset = headers.get("X-RateLimit-Reset", "unknown")
            raise ServiceOSException(
                error_code="RATE_LIMITED",
                detail="Too many attempts. Please wait before trying again.",
                status_code=429,
                resolution="Wait and retry later.",
                context={"retry_after_seconds": int(reset) - int(time.time()) if reset != "unknown" else 60},
            )
        return headers


rate_limiter = RateLimiter()


def opaque_rate_identifier(value: str | None) -> str:
    """Stable one-way identifier for Redis keys and security telemetry."""
    return hashlib.sha256((value or "unknown").strip().lower().encode()).hexdigest()[:24]


async def record_abuse_event(
    activity_type: str,
    *,
    entity_id: str,
    entity_type: str,
    ip_address: str | None = None,
    threat_level: str = "medium",
    context: dict[str, Any] | None = None,
) -> None:
    """Persist an admin-visible threat using an independent transaction."""
    try:
        from app.redis_client import get_redis

        dedupe_key = (
            f"serviceos:abuse:event:{activity_type}:"
            f"{opaque_rate_identifier(entity_id)}"
        )
        if not await get_redis().set(dedupe_key, "1", ex=300, nx=True):
            return
    except Exception:
        # The application limits fail closed in production, but evidence
        # capture must still work when Redis itself is the incident.
        pass
    try:
        from app.database import get_db_session
        from sqlalchemy import func, select
        from app.engines.auth.models import User
        from app.engines.platform_notifications.models import InAppNotification
        from app.engines.security.models import SuspiciousActivityLog

        async with get_db_session() as db:
            threat = SuspiciousActivityLog(
                entity_id=opaque_rate_identifier(entity_id),
                entity_type=entity_type,
                activity_type=activity_type,
                threat_level=threat_level,
                description=f"{activity_type} was blocked by an abuse-control threshold",
                ip_address=ip_address,
                detected_value=1,
                threshold=1,
                context=context or {},
                auto_actioned=True,
                risk_score=80 if threat_level == "high" else 60,
                source="abuse_guard",
            )
            db.add(threat)
            await db.flush()

            # High-risk booking/OTP spikes also create one admin notification
            # per 15-minute window. The threat queue still records every block,
            # while the bell remains useful instead of becoming its own flood.
            if threat_level == "high":
                notification_type = f"security.abuse.{activity_type}"
                recent = int((await db.execute(
                    select(func.count()).select_from(InAppNotification).where(
                        InAppNotification.notification_type == notification_type,
                        InAppNotification.created_at >= datetime.now(timezone.utc) - timedelta(minutes=15),
                    )
                )).scalar_one() or 0)
                if recent == 0:
                    admin_ids = (await db.execute(
                        select(User.id).where(
                            User.role == "super_admin",
                            User.is_active.is_(True),
                        )
                    )).scalars().all()
                    for admin_id in admin_ids:
                        db.add(InAppNotification(
                            user_id=admin_id,
                            tenant_id=None,
                            notification_type=notification_type,
                            title="Automated abuse protection triggered",
                            body=f"Fuvay blocked suspicious {activity_type.replace('_', ' ')} activity.",
                            action_url=f"/admin/security/threats/{threat.id}",
                            action_label="Review threat",
                            source_record_type="suspicious_activity_logs",
                            source_record_id=threat.id,
                            severity="critical",
                            read_status="unread",
                            is_mandatory=True,
                        ))
    except Exception as exc:
        # Enforcement must not depend on observability being writable.
        logger.warning("abuse_event.persist_failed", activity_type=activity_type, error=str(exc))


async def enforce_otp_send_limits(
    recipient: str,
    *,
    ip_address: str | None = None,
    source_id: str | None = None,
    costed_delivery: bool = True,
) -> None:
    """Apply every OTP cost/abuse limit from the shared service layer.

    This must be called immediately before delivery. Keeping it below the
    HTTP router also protects Instagram, WhatsApp, and internal signup calls.
    """
    recipient_id = opaque_rate_identifier(recipient)
    checks = [
        ("otp:recipient:hour", "auth:otp_send", recipient_id),
        ("otp:recipient:day", "auth:otp_daily_recipient", recipient_id),
    ]
    if ip_address:
        ip_id = opaque_rate_identifier(ip_address)
        checks.extend((
            ("otp:ip:hour", "auth:otp_send_ip", ip_id),
            ("otp:ip:day", "auth:otp_daily_ip", ip_id),
        ))
    if costed_delivery:
        checks.append(("otp:global:day", "auth:otp_daily_global", "all"))
    if source_id and source_id.strip().lower() not in {"mobile", "web", "unknown"}:
        source_hash = opaque_rate_identifier(source_id)
        checks.extend((
            ("otp:source:hour", "auth:otp_send_source", source_hash),
            ("otp:source:day", "auth:otp_daily_source", source_hash),
        ))
    fail_closed = get_settings().APP_ENV in ("staging", "production")
    for key, limit_type, identifier in checks:
        try:
            await rate_limiter.check_and_raise(
                limit_key=key,
                limit_type=limit_type,
                identifier=identifier,
                fail_closed=fail_closed,
            )
        except Exception:
            await record_abuse_event(
                "otp_send_blocked",
                entity_id=recipient_id,
                entity_type="otp_recipient",
                ip_address=ip_address,
                threat_level="high",
                context={"limit_type": limit_type, "source": opaque_rate_identifier(source_id)},
            )
            raise


async def enforce_otp_delivery_budget(*, ip_address: str | None = None) -> None:
    """Consume one unit from the global paid-OTP delivery circuit breaker.

    Enumeration-safe flows must call this only after they know a real account
    exists. Otherwise an attacker can submit random recipients and exhaust the
    platform-wide SMS budget without causing a single delivery.
    """
    fail_closed = get_settings().APP_ENV in ("staging", "production")
    try:
        await rate_limiter.check_and_raise(
            limit_key="otp:global:day",
            limit_type="auth:otp_daily_global",
            identifier="all",
            fail_closed=fail_closed,
        )
    except Exception:
        await record_abuse_event(
            "otp_delivery_budget_blocked",
            entity_id="global",
            entity_type="otp_budget",
            ip_address=ip_address,
            threat_level="high",
            context={"limit_type": "auth:otp_daily_global"},
        )
        raise


async def enforce_otp_verify_limits(
    recipient: str,
    *,
    ip_address: str | None = None,
    source_id: str | None = None,
) -> None:
    """Bound OTP guesses consistently across API and social entry points."""
    checks = [
        ("otp:verify:recipient", "auth:otp_verify", opaque_rate_identifier(recipient)),
    ]
    if ip_address:
        checks.append(("otp:verify:ip", "auth:otp_verify_ip", opaque_rate_identifier(ip_address)))
    if source_id and source_id.strip().lower() not in {"mobile", "web", "unknown"}:
        checks.append(("otp:verify:source", "auth:otp_verify_source", opaque_rate_identifier(source_id)))
    fail_closed = get_settings().APP_ENV in ("staging", "production")
    for key, limit_type, identifier in checks:
        try:
            await rate_limiter.check_and_raise(
                limit_key=key,
                limit_type=limit_type,
                identifier=identifier,
                fail_closed=fail_closed,
            )
        except Exception:
            await record_abuse_event(
                "otp_verify_blocked",
                entity_id=recipient,
                entity_type="otp_recipient",
                ip_address=ip_address,
                threat_level="high",
                context={"limit_type": limit_type},
            )
            raise


async def enforce_booking_action_limits(
    action: str,
    *,
    actor_id: str,
    ip_address: str | None = None,
) -> None:
    """Apply booking velocity controls at shared service choke points."""
    if action not in {"draft", "answer", "confirm"}:
        raise ValueError(f"Unsupported booking abuse-control action: {action}")
    fail_closed = get_settings().APP_ENV in ("staging", "production")
    try:
        await rate_limiter.check_and_raise(
            limit_key=f"booking:{action}:actor",
            limit_type=f"booking:{action}_user",
            identifier=opaque_rate_identifier(actor_id),
            fail_closed=fail_closed,
        )
        if ip_address and action != "answer":
            ip_limit_type = "booking:confirm_ip" if action == "confirm" else "booking:draft_ip"
            await rate_limiter.check_and_raise(
                limit_key=f"booking:{action}:ip",
                limit_type=ip_limit_type,
                identifier=opaque_rate_identifier(ip_address),
                fail_closed=fail_closed,
            )
    except Exception:
        await record_abuse_event(
            f"booking_{action}_blocked",
            entity_id=actor_id,
            entity_type="booking_actor",
            ip_address=ip_address,
            threat_level="high" if action == "confirm" else "medium",
        )
        raise


async def enforce_social_draft_limit(social_identity: str) -> None:
    """Cap how many booking drafts one chat identity may open per hour.

    The generic `booking:draft_user` limit above keys on customer_id, falling
    back to the AI session id -- and a social session id is rotated by every
    `/fuvay`, so for an unregistered chat sender that limit resets exactly when
    the abuse repeats. `social_identity` is the channel-scoped sender id, which
    a restart cannot change.
    """
    fail_closed = get_settings().APP_ENV in ("staging", "production")
    try:
        await rate_limiter.check_and_raise(
            limit_key="booking:social:draft",
            limit_type="booking:social_draft",
            identifier=opaque_rate_identifier(social_identity),
            fail_closed=fail_closed,
        )
    except Exception:
        await record_abuse_event(
            "social_draft_flood",
            entity_id=social_identity,
            entity_type="social_sender",
            threat_level="medium",
        )
        raise


# ── Idempotency ───────────────────────────────────────────────────────────────
class IdempotencyStore:
    """
    Redis-based idempotency key store.
    Write endpoints accept X-Idempotency-Key header.
    If we've seen this key before, return the cached response.
    Key TTL: 24 hours.
    """

    IDEMPOTENCY_KEY_TTL = 86400  # 24 hours

    async def get(self, key: str) -> dict | None:
        from app.redis_client import get_redis
        r = get_redis()
        raw = await r.get(f"serviceos:idempotency:{key}")
        if raw:
            return json.loads(raw)
        return None

    async def store(self, key: str, status_code: int, body: dict) -> None:
        from app.redis_client import get_redis
        r = get_redis()
        await r.setex(
            f"serviceos:idempotency:{key}",
            self.IDEMPOTENCY_KEY_TTL,
            json.dumps({"status_code": status_code, "body": body, "cached_at": datetime.now(timezone.utc).isoformat()}),
        )


idempotency_store = IdempotencyStore()


# ── IP Utilities ──────────────────────────────────────────────────────────────
def get_client_ip(request: Request) -> str:
    """Return the real IP only when forwarded by an explicitly trusted peer."""
    peer = request.client.host if request.client else "unknown"
    try:
        peer_ip = ipaddress.ip_address(peer)
        trusted = any(
            peer_ip in ipaddress.ip_network(cidr, strict=False)
            for cidr in get_settings().TRUSTED_PROXY_CIDRS
        )
    except (ValueError, TypeError):
        trusted = False
    if not trusted:
        return peer

    for header in ("CF-Connecting-IP", "X-Real-IP", "X-Forwarded-For"):
        raw = request.headers.get(header)
        if not raw:
            continue
        candidate = raw.split(",", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return peer


def hash_ip(ip: str) -> str:
    """One-way hash of IP for rate limit keys — never store raw IPs in keys."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# ── Security Event Publisher ───────────────────────────────────────────────────
async def publish_security_event(
    event_type: str,
    severity: str,
    actor_id: str | None,
    tenant_id: str | None,
    ip_address: str,
    details: dict,
) -> None:
    """Publish security events to the event bus for monitoring."""
    try:
        from app.core.events import get_event_bus, DomainEvent
        bus = get_event_bus()
        event = DomainEvent.create(
            event_type=f"security.{event_type}",
            engine_id="auth",
            tenant_id=tenant_id or "platform",
            entity_type="security_event",
            entity_id=actor_id or "anonymous",
            payload={
                "severity": severity,
                "ip_address": ip_address,
                "details": details,
            },
            actor_id=actor_id,
        )
        await bus.publish(event)
    except Exception as e:
        logger.error("security_event.publish_failed", error=str(e), event_type=event_type)
