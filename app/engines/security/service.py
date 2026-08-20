"""Security Engine — SecurityService. Proven Level 5.
  ✅ API key: HMAC-SHA256 hash stored, raw key NEVER persisted
  ✅ IP blocklist: Redis SET for O(1) lookup, DB as source of truth
  ✅ Suspicious activity: Redis sliding window counters (Lua script)
  ✅ Platform audit log: append-only, no UPDATE/DELETE ever
  ✅ Session management: Redis primary, DB audit, force-logout atomic
  ✅ API key rotation: old key marked ROTATED, new key issued atomically
"""
from __future__ import annotations
import ipaddress
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.security.constants import (
    APIKeyStatus, ActivityType, ThreatLevel, HIGH_RISK_OPERATIONS,
    ACTIVITY_THRESHOLDS, REDIS_IP_BLOCKLIST, REDIS_CIDR_BLOCKLIST, REDIS_SESSION,
    REDIS_USER_SESSIONS, REDIS_ACTIVITY_COUNTER, REDIS_API_KEY_CACHE,
    MAX_CONCURRENT_SESSIONS, AUDIT_RETENTION_DAYS,
    generate_api_key, hash_api_key, extract_prefix, ALL_SCOPES,
)
from app.engines.security.models import (
    APIKey, IPBlocklistEntry, SuspiciousActivityLog,
    PlatformAuditLog, SessionInventory, ApiKeyUsageLog,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.config import get_settings
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("security.service")
utcnow = lambda: datetime.now(timezone.utc)


async def warm_ip_blocklist_cache() -> dict:
    """Rebuild the Redis enforcement sets from PostgreSQL without loading all rows."""
    from app.database import get_db_session
    redis = get_redis()
    await redis.delete(REDIS_IP_BLOCKLIST, REDIS_CIDR_BLOCKLIST)
    exact = cidr = 0
    async with get_db_session() as db:
        stream = await db.stream_scalars(select(IPBlocklistEntry).where(
            IPBlocklistEntry.status == "active",
            or_(IPBlocklistEntry.expires_at.is_(None), IPBlocklistEntry.expires_at > utcnow()),
        ).execution_options(yield_per=1000))
        async for entry in stream:
            target = REDIS_IP_BLOCKLIST if entry.entry_type == "ip" else REDIS_CIDR_BLOCKLIST
            await redis.sadd(target, entry.ip_or_cidr)
            if entry.entry_type == "ip":
                exact += 1
            else:
                cidr += 1
    return {"exact": exact, "cidr": cidr}


class SecurityService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None,
                 actor_ip: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_ip = actor_ip
        # Phase 2A Slice 2F-35: the authoritative tenant of the calling
        # principal, derived server-side from the token. rotate_api_key/
        # revoke_api_key MUST scope by this value (never trust a
        # client-supplied tenant_id as ownership evidence).
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID | None = None) -> uuid.UUID | None:
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="security_mutation_requires_trusted_tenant_context")
        if requested_tenant_id is not None and requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's API keys.",
                blocking_rule="security_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="security",
                tenant_id=tenant_id, entity_type="security", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("security.event_failed", error=str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # API KEY MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────

    async def create_api_key(self, tenant_id: uuid.UUID, name: str,
                              description: str | None, scopes: list,
                              environment: str, expires_days: int | None) -> dict:
        """PROVEN: raw key returned ONCE. Only hash+prefix stored in DB."""
        # Validate scopes
        invalid = [s for s in scopes if s not in ALL_SCOPES]
        if invalid:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Invalid scopes: {invalid}. Valid: {ALL_SCOPES}")

        raw_key, key_hash = generate_api_key(environment)
        prefix = extract_prefix(raw_key)
        expires_at = utcnow() + timedelta(days=expires_days) if expires_days else None

        key = APIKey(
            tenant_id=tenant_id, name=name, description=description,
            key_hash=key_hash,    # PROVEN: hash only
            key_prefix=prefix,    # PROVEN: prefix only
            environment=environment, scopes=scopes,
            status=APIKeyStatus.ACTIVE,
            expires_at=expires_at, created_by=self.actor_id,
        )
        self.db.add(key); await self.db.flush()

        await self._write_audit("api_key.create", "security", str(key.id),
                                 after={"name": name, "scopes": scopes, "env": environment})
        await self._publish("security.api_key_created", str(tenant_id), str(key.id),
                            {"name": name, "scopes": scopes})

        logger.info("security.api_key_created", key_id=str(key.id), tenant_id=str(tenant_id))
        return {
            "key_id": str(key.id),
            "raw_key": raw_key,   # PROVEN: shown ONCE, never stored
            "key_prefix": prefix,
            "name": name, "scopes": scopes, "environment": environment,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "warning": "Store this key securely. It will NOT be shown again.",
        }

    async def verify_api_key(self, raw_key: str) -> dict:
        """PROVEN: hash the incoming key, look up by hash — never compare plaintext."""
        key_hash = hash_api_key(raw_key)

        # Cache check by prefix
        prefix = extract_prefix(raw_key)
        try:
            import json
            cached = await self.redis.get(REDIS_API_KEY_CACHE.format(key_prefix=prefix))
            if cached:
                data = json.loads(cached)
                if data.get("key_hash") == key_hash and data.get("status") == APIKeyStatus.ACTIVE:
                    denial = await self._api_key_runtime_denial(
                        data["key_id"], data.get("allowed_ips"), data.get("rate_limit_per_minute"))
                    if denial:
                        self.db.add(ApiKeyUsageLog(
                            api_key_id=uuid.UUID(data["key_id"]), endpoint="api_key.verify",
                            method="POST", status_code=403, ip_address=self.actor_ip,
                        ))
                        return {"valid": False, "reason": denial}
                    await self.db.execute(update(APIKey).where(
                        APIKey.id == uuid.UUID(data["key_id"])
                    ).values(last_used_at=utcnow(), last_used_ip=self.actor_ip,
                             use_count=APIKey.use_count + 1))
                    self.db.add(ApiKeyUsageLog(
                        api_key_id=uuid.UUID(data["key_id"]), endpoint="api_key.verify",
                        method="POST", status_code=200, ip_address=self.actor_ip,
                    ))
                    return {"valid": True, "key_id": data["key_id"],
                            "tenant_id": data["tenant_id"], "scopes": data["scopes"],
                            "from_cache": True}
        except Exception:
            pass

        r = await self.db.execute(select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.status == APIKeyStatus.ACTIVE))
        key = r.scalar_one_or_none()
        if not key:
            await self._record_suspicious_activity(
                None, str(raw_key[:8]), "api_key",
                ActivityType.API_KEY_BRUTE, self.actor_ip or "unknown")
            return {"valid": False, "reason": "Invalid or revoked API key"}

        if key.expires_at and key.expires_at < utcnow():
            key.status = APIKeyStatus.EXPIRED
            return {"valid": False, "reason": "API key has expired"}

        denial = await self._api_key_runtime_denial(
            str(key.id), key.allowed_ips_json, key.rate_limit_per_minute)
        if denial:
            self.db.add(ApiKeyUsageLog(
                api_key_id=key.id, endpoint="api_key.verify", method="POST",
                status_code=403, ip_address=self.actor_ip,
            ))
            return {"valid": False, "reason": denial}

        key.last_used_at = utcnow()
        key.last_used_ip = self.actor_ip
        key.use_count += 1
        self.db.add(ApiKeyUsageLog(
            api_key_id=key.id, endpoint="api_key.verify", method="POST",
            status_code=200, ip_address=self.actor_ip,
        ))

        # Cache for 5 min
        try:
            import json
            await self.redis.setex(
                REDIS_API_KEY_CACHE.format(key_prefix=prefix), 300,
                json.dumps({"key_id": str(key.id), "key_hash": key_hash,
                             "tenant_id": str(key.tenant_id), "scopes": key.scopes,
                             "status": key.status, "allowed_ips": key.allowed_ips_json,
                             "rate_limit_per_minute": key.rate_limit_per_minute}))
        except Exception:
            pass

        return {"valid": True, "key_id": str(key.id), "tenant_id": str(key.tenant_id),
                "scopes": key.scopes, "environment": key.environment, "from_cache": False}

    async def _api_key_runtime_denial(self, key_id: str, allowed_ips: list | None,
                                      rate_limit_per_minute: int | None) -> str | None:
        """Apply the controls configured in the admin API-key workspace."""
        if allowed_ips:
            try:
                caller = ipaddress.ip_address(self.actor_ip or "")
                if not any(caller in ipaddress.ip_network(raw, strict=False) for raw in allowed_ips):
                    return "API key is not permitted from this IP address"
            except ValueError:
                return "API key is not permitted from this IP address"
        if rate_limit_per_minute:
            try:
                minute_bucket = int(utcnow().timestamp() // 60)
                rate_key = f"serviceos:security:api_key_rate:{key_id}:{minute_bucket}"
                count = await self.redis.incr(rate_key)
                if count == 1:
                    await self.redis.expire(rate_key, 90)
                if count > rate_limit_per_minute:
                    return "API key rate limit exceeded"
            except Exception as exc:
                logger.warning("security.api_key_rate_limit_unavailable", key_id=key_id, error=str(exc))
        return None

    async def get_api_key(self, key_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(APIKey).where(
            APIKey.id == key_id, APIKey.tenant_id == tenant_id))
        key = r.scalar_one_or_none()
        if not key: raise NotFoundException("APIKey", str(key_id))
        return {"key_id": str(key.id), "name": key.name, "key_prefix": key.key_prefix,
                "environment": key.environment, "scopes": key.scopes, "status": key.status,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "use_count": key.use_count, "created_at": key.created_at.isoformat(),
                "note": "Full key not stored — cannot be retrieved"}

    async def list_api_keys(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(APIKey).where(
            APIKey.tenant_id == tenant_id,
            APIKey.status != APIKeyStatus.REVOKED,
        ).order_by(APIKey.created_at.desc()))
        keys = r.scalars().all()
        return {"api_keys": [{"key_id": str(k.id), "name": k.name,
                "key_prefix": f"sk_{k.environment}_{k.key_prefix}...",
                "scopes": k.scopes, "status": k.status, "use_count": k.use_count,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None}
               for k in keys], "total": len(keys)}

    async def rotate_api_key(self, key_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """PROVEN: old key marked ROTATED atomically. New key issued. One transaction."""
        # Phase 2A Slice 2F-35: tenant_id previously arrived straight from
        # the request Query param and was never compared to the actor's
        # own tenant -- verified server-side before the query runs.
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(APIKey).where(
            APIKey.id == key_id, APIKey.tenant_id == tenant_id))
        old_key = r.scalar_one_or_none()
        if not old_key: raise NotFoundException("APIKey", str(key_id))
        if old_key.status != APIKeyStatus.ACTIVE:
            raise ServiceOSException("CONFLICT", f"Key is {old_key.status}. Only active keys can be rotated.")

        # Preserve every policy control on rotation; rotation must never widen
        # access or silently turn an expiring key into a permanent one.
        expires_days = None
        if old_key.expires_at:
            remaining_seconds = max(1, int((old_key.expires_at - utcnow()).total_seconds()))
            expires_days = max(1, (remaining_seconds + 86399) // 86400)
        new_result = await self.create_api_key(tenant_id, f"{old_key.name} (rotated)",
                                                old_key.description, old_key.scopes,
                                                old_key.environment, expires_days)
        new_key_id = uuid.UUID(new_result["key_id"])
        new_r = await self.db.execute(select(APIKey).where(APIKey.id == new_key_id))
        new_key = new_r.scalar_one()
        new_key.owner_type = old_key.owner_type
        new_key.allowed_ips_json = old_key.allowed_ips_json
        new_key.rate_limit_per_minute = old_key.rate_limit_per_minute
        new_key.permissions_json = old_key.permissions_json

        # Mark old key as rotated — atomically in same transaction
        old_key.status = APIKeyStatus.ROTATED
        old_key.rotated_to = new_key_id
        old_key.revoked_at = utcnow()

        # Invalidate cache
        try:
            await self.redis.delete(REDIS_API_KEY_CACHE.format(key_prefix=old_key.key_prefix))
        except Exception:
            pass

        await self._write_audit("api_key.rotate", "security", str(key_id),
                                 after={"new_key_id": str(new_key_id)})
        return {**new_result, "previous_key_id": str(key_id),
                "note": "Previous key is now invalid. Store the new key immediately."}

    async def revoke_api_key(self, key_id: uuid.UUID, tenant_id: uuid.UUID,
                              reason: str) -> dict:
        # Phase 2A Slice 2F-35: same cross-tenant fix as rotate_api_key.
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(APIKey).where(
            APIKey.id == key_id, APIKey.tenant_id == tenant_id))
        key = r.scalar_one_or_none()
        if not key: raise NotFoundException("APIKey", str(key_id))
        if key.status == APIKeyStatus.REVOKED:
            raise ServiceOSException("CONFLICT", "Key is already revoked.")
        key.status = APIKeyStatus.REVOKED
        key.revoked_at = utcnow(); key.revoked_by = self.actor_id
        key.revoke_reason = reason
        try:
            await self.redis.delete(REDIS_API_KEY_CACHE.format(key_prefix=key.key_prefix))
        except Exception:
            pass
        await self._write_audit("api_key.revoke", "security", str(key_id),
                                 after={"reason": reason})
        await self._publish("security.api_key_revoked", str(tenant_id), str(key_id),
                            {"reason": reason})
        return {"key_id": str(key_id), "revoked": True, "reason": reason}

    # ─────────────────────────────────────────────────────────────────────────
    # IP BLOCKLIST
    # ─────────────────────────────────────────────────────────────────────────

    async def block_ip(self, ip_or_cidr: str, entry_type: str, reason: str,
                        threat_level: str, is_global: bool,
                        tenant_id: uuid.UUID | None, expires_hours: int | None) -> dict:
        """PROVEN: DB write first, then Redis SET — DB is source of truth."""
        expires_at = utcnow() + timedelta(hours=expires_hours) if expires_hours else None
        entry = IPBlocklistEntry(
            ip_or_cidr=ip_or_cidr, entry_type=entry_type, reason=reason,
            threat_level=threat_level, is_global=is_global, tenant_id=tenant_id,
            expires_at=expires_at, blocked_by=self.actor_id,
        )
        self.db.add(entry); await self.db.flush()

        # Sync to Redis SET — O(1) lookup for middleware
        try:
            await self.redis.sadd(REDIS_IP_BLOCKLIST, ip_or_cidr)
            if expires_at:
                ttl = int((expires_at - utcnow()).total_seconds())
                # Note: Redis SADD does not support TTL per member — use separate key
                await self.redis.setex(f"{REDIS_IP_BLOCKLIST}:expire:{ip_or_cidr}", ttl, "1")
        except Exception:
            pass

        await self._write_audit("ip.block", "security", ip_or_cidr,
                                 after={"reason": reason, "threat_level": threat_level,
                                        "is_global": is_global})
        logger.warning("security.ip_blocked", ip=ip_or_cidr, threat=threat_level)
        return {"entry_id": str(entry.id), "ip_or_cidr": ip_or_cidr,
                "threat_level": threat_level, "blocked": True,
                "expires_at": expires_at.isoformat() if expires_at else "permanent"}

    async def unblock_ip(self, ip_or_cidr: str, tenant_id: uuid.UUID | None) -> dict:
        r = await self.db.execute(select(IPBlocklistEntry).where(
            IPBlocklistEntry.ip_or_cidr == ip_or_cidr,
            IPBlocklistEntry.is_active == True))
        entry = r.scalar_one_or_none()
        if not entry: raise NotFoundException("IPBlocklistEntry", ip_or_cidr)
        entry.is_active = False
        try:
            await self.redis.srem(REDIS_IP_BLOCKLIST, ip_or_cidr)
        except Exception:
            pass
        await self._write_audit("ip.unblock", "security", ip_or_cidr, after={})
        return {"ip_or_cidr": ip_or_cidr, "unblocked": True}

    async def check_ip(self, ip_address: str) -> dict:
        """PROVEN: Redis SISMEMBER — O(1), no DB query for hot path."""
        try:
            in_blocklist = await self.redis.sismember(REDIS_IP_BLOCKLIST, ip_address)
            if in_blocklist:
                return {"ip": ip_address, "blocked": True, "source": "redis_cache"}
        except Exception:
            pass
        # DB fallback
        r = await self.db.execute(select(IPBlocklistEntry).where(
            IPBlocklistEntry.ip_or_cidr == ip_address,
            IPBlocklistEntry.is_active == True))
        entry = r.scalar_one_or_none()
        return {"ip": ip_address, "blocked": entry is not None,
                "reason": entry.reason if entry else None,
                "threat_level": entry.threat_level if entry else None,
                "source": "database"}

    async def list_blocklist(self, tenant_id: uuid.UUID | None,
                              limit: int, cursor: str | None) -> dict:
        q = select(IPBlocklistEntry).where(IPBlocklistEntry.is_active == True)            .order_by(IPBlocklistEntry.created_at.desc())
        if tenant_id: q = q.where(IPBlocklistEntry.tenant_id == tenant_id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(IPBlocklistEntry.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"entries": [{"entry_id": str(e.id), "ip_or_cidr": e.ip_or_cidr,
                "entry_type": e.entry_type, "threat_level": e.threat_level,
                "reason": e.reason, "is_global": e.is_global,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
                "created_at": e.created_at.isoformat()} for e in items],
                "has_next": has_next, "next_cursor": nc}

    # ─────────────────────────────────────────────────────────────────────────
    # SUSPICIOUS ACTIVITY DETECTION
    # ─────────────────────────────────────────────────────────────────────────

    async def _record_suspicious_activity(self, tenant_id: uuid.UUID | None,
                                           entity_id: str, entity_type: str,
                                           activity_type: str, ip_address: str) -> dict | None:
        """PROVEN: Redis sliding window counter — same Lua pattern as auth engine."""
        threshold_config = ACTIVITY_THRESHOLDS.get(activity_type)
        if not threshold_config:
            return None

        window = threshold_config["window_seconds"]
        threshold = threshold_config["count"]
        redis_key = REDIS_ACTIVITY_COUNTER.format(
            entity_id=entity_id, activity_type=activity_type)

        # Sliding window Lua script — same as Phase 2 auth
        lua_script = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window * 1000)
redis.call('ZADD', key, now, now)
redis.call('EXPIRE', key, window)
return redis.call('ZCARD', key)
"""
        try:
            now_ms = int(utcnow().timestamp() * 1000)
            count = await self.redis.eval(lua_script, 1, redis_key, str(now_ms), str(window))
            count = int(count)
        except Exception:
            count = 1

        if count < threshold:
            return None

        # Threshold exceeded — write to DB
        threat_level = (ThreatLevel.CRITICAL if count >= threshold * 3
                        else ThreatLevel.HIGH if count >= threshold * 2
                        else ThreatLevel.MEDIUM)
        log = SuspiciousActivityLog(
            tenant_id=tenant_id, entity_id=entity_id, entity_type=entity_type,
            activity_type=activity_type, threat_level=threat_level,
            description=f"{activity_type} threshold exceeded: {count}/{threshold} in {window}s",
            ip_address=ip_address, detected_value=count, threshold=threshold,
            context={"window_seconds": window, "count": count},
        )
        self.db.add(log); await self.db.flush()

        if threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            await self._publish("security.threat_detected", str(tenant_id) if tenant_id else "platform",
                                str(log.id), {"activity_type": activity_type,
                                               "threat_level": threat_level, "count": count})
        logger.warning("security.suspicious_activity", activity=activity_type,
                        entity=entity_id, count=count, threat=threat_level)
        return {"log_id": str(log.id), "threat_level": threat_level, "count": count}

    async def record_activity(self, tenant_id: uuid.UUID | None, entity_id: str,
                               entity_type: str, activity_type: str,
                               ip_address: str) -> dict:
        # Slice 2F-39A2R fix: any authenticated caller could previously
        # attribute suspicious-activity log entries to any tenant via a
        # client-supplied tenant_id -- observed and recorded, unremediated,
        # since Slice 2F-26D/F/G/H's security-observations-not-remediated.md
        # ("same family as the audit-log observation"). tenant_id is now
        # cross-checked against the caller's own tenant (super_admin
        # exempt), matching the same _require_trusted_tenant pattern
        # already used for the API-key mutations in this service.
        tenant_id = self._require_trusted_tenant(tenant_id)
        result = await self._record_suspicious_activity(
            tenant_id, entity_id, entity_type, activity_type, ip_address)
        return result or {"recorded": True, "threshold_not_reached": True}

    async def list_suspicious_activity(self, tenant_id: uuid.UUID | None,
                                        threat_level: str | None, status: str | None,
                                        limit: int, cursor: str | None) -> dict:
        q = select(SuspiciousActivityLog).order_by(SuspiciousActivityLog.created_at.desc())
        if tenant_id:    q = q.where(SuspiciousActivityLog.tenant_id == tenant_id)
        if threat_level: q = q.where(SuspiciousActivityLog.threat_level == threat_level)
        if status:       q = q.where(SuspiciousActivityLog.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(SuspiciousActivityLog.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"activities": [{"log_id": str(l.id), "activity_type": l.activity_type,
                "threat_level": l.threat_level, "entity_id": l.entity_id,
                "description": l.description, "ip_address": l.ip_address,
                "detected_value": l.detected_value, "threshold": l.threshold,
                "status": l.status, "created_at": l.created_at.isoformat()} for l in items],
                "has_next": has_next, "next_cursor": nc}

    async def acknowledge_activity(self, log_id: uuid.UUID, notes: str | None) -> dict:
        r = await self.db.execute(select(SuspiciousActivityLog).where(
            SuspiciousActivityLog.id == log_id))
        log = r.scalar_one_or_none()
        if not log: raise NotFoundException("SuspiciousActivityLog", str(log_id))
        if log.status == "acknowledged":
            raise ServiceOSException("CONFLICT", "Already acknowledged.")
        log.status = "acknowledged"
        log.acknowledged_by = self.actor_id; log.acknowledged_at = utcnow()
        return {"log_id": str(log_id), "acknowledged": True}

    # ─────────────────────────────────────────────────────────────────────────
    # PLATFORM AUDIT LOG
    # ─────────────────────────────────────────────────────────────────────────

    async def _write_audit(self, operation: str, engine_id: str,
                            entity_id: str, tenant_id: uuid.UUID | None = None,
                            entity_type: str | None = None,
                            before: dict | None = None, after: dict | None = None) -> None:
        """PROVEN: append-only — only INSERT, never UPDATE or DELETE."""
        is_high_risk = operation in HIGH_RISK_OPERATIONS
        self.db.add(PlatformAuditLog(
            tenant_id=tenant_id, actor_id=self.actor_id, actor_role=self.actor_role,
            actor_ip=self.actor_ip, operation=operation, engine_id=engine_id,
            entity_type=entity_type, entity_id=entity_id,
            before_state=before, after_state=after,
            request_id=self.request_id, is_high_risk=is_high_risk,
        ))

    async def write_audit_entry(self, operation: str, engine_id: str,
                                 entity_id: str, tenant_id: uuid.UUID | None,
                                 entity_type: str | None,
                                 before: dict | None, after: dict | None) -> dict:
        # Slice 2F-39A2R fix: any authenticated caller could previously
        # append arbitrary audit entries attributed to another tenant --
        # observed and recorded, unremediated, since Slice
        # 2F-26D/F/G/H's security-observations-not-remediated.md
        # ("weakening every control that cites the audit log as
        # evidence"). tenant_id is now cross-checked against the caller's
        # own tenant (super_admin exempt).
        tenant_id = self._require_trusted_tenant(tenant_id)
        await self._write_audit(operation, engine_id, entity_id,
                                 tenant_id, entity_type, before, after)
        await self.db.flush()
        return {"operation": operation, "engine_id": engine_id, "recorded": True}

    async def search_audit_log(self, actor_id: uuid.UUID | None,
                                tenant_id: uuid.UUID | None,
                                operation: str | None, engine_id: str | None,
                                is_high_risk: bool | None,
                                limit: int, cursor: str | None) -> dict:
        q = select(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc())
        if actor_id:    q = q.where(PlatformAuditLog.actor_id == actor_id)
        if tenant_id:   q = q.where(PlatformAuditLog.tenant_id == tenant_id)
        if operation:   q = q.where(PlatformAuditLog.operation == operation)
        if engine_id:   q = q.where(PlatformAuditLog.engine_id == engine_id)
        if is_high_risk is not None:
            q = q.where(PlatformAuditLog.is_high_risk == is_high_risk)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(PlatformAuditLog.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"audit_logs": [{"log_id": str(l.id), "operation": l.operation,
                "engine_id": l.engine_id, "entity_type": l.entity_type,
                "entity_id": l.entity_id, "actor_role": l.actor_role,
                "actor_ip": l.actor_ip, "is_high_risk": l.is_high_risk,
                "created_at": l.created_at.isoformat()} for l in items],
                "has_next": has_next, "next_cursor": nc,
                "note": "Audit log is append-only. No entries can be modified or deleted."}

    # ─────────────────────────────────────────────────────────────────────────
    # SESSION MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────

    async def create_session(self, user_id: uuid.UUID, tenant_id: uuid.UUID | None,
                              session_id: str, device_info: dict,
                              ip_address: str | None, user_agent: str | None,
                              ttl_seconds: int) -> dict:
        """Register session in both Redis (primary) and DB (audit)."""
        # Slice 2F-39A2R fix: user_id/tenant_id previously arrived
        # unchecked from the request body -- any authenticated caller
        # could register a session record attributed to a different user.
        # Only the caller's own user_id is accepted (super_admin exempt,
        # matching every other server-derived-identity guard in this
        # service).
        if self.actor_role != "super_admin" and self.actor_id is not None and user_id != self.actor_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "Cannot create a session for another user.",
                blocking_rule="security_session_create_actor_mismatch")
        tenant_id = self._require_trusted_tenant(tenant_id)
        # Enforce max concurrent sessions
        active_r = await self.db.execute(select(func.count(SessionInventory.id)).where(
            SessionInventory.user_id == user_id,
            SessionInventory.is_active == True))
        active_count = active_r.scalar_one_or_none() or 0
        if active_count >= MAX_CONCURRENT_SESSIONS:
            # Revoke oldest session
            oldest_r = await self.db.execute(select(SessionInventory).where(
                SessionInventory.user_id == user_id,
                SessionInventory.is_active == True,
            ).order_by(SessionInventory.last_seen_at.asc()).limit(1))
            oldest = oldest_r.scalar_one_or_none()
            if oldest:
                await self._revoke_session_record(oldest, "max_sessions_exceeded")

        expires_at = utcnow() + timedelta(seconds=ttl_seconds)
        session = SessionInventory(
            user_id=user_id, tenant_id=tenant_id, session_id=session_id,
            device_info=device_info, ip_address=ip_address, user_agent=user_agent,
            expires_at=expires_at,
        )
        self.db.add(session); await self.db.flush()

        # Redis primary
        try:
            redis_key = REDIS_SESSION.format(session_id=session_id)
            import json
            await self.redis.setex(redis_key, ttl_seconds,
                                    json.dumps({"user_id": str(user_id),
                                                "tenant_id": str(tenant_id) if tenant_id else None,
                                                "session_id": session_id}))
            await self.redis.sadd(REDIS_USER_SESSIONS.format(user_id=user_id), session_id)
        except Exception:
            pass

        return {"session_id": session_id, "expires_at": expires_at.isoformat(),
                "concurrent_sessions": active_count + 1}

    async def list_user_sessions(self, user_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(SessionInventory).where(
            SessionInventory.user_id == user_id,
            SessionInventory.is_active == True,
        ).order_by(SessionInventory.last_seen_at.desc()))
        sessions = r.scalars().all()
        return {"user_id": str(user_id), "active_sessions": len(sessions),
                "sessions": [{"session_id": s.session_id, "device_info": s.device_info,
                               "ip_address": s.ip_address, "last_seen_at": s.last_seen_at.isoformat(),
                               "expires_at": s.expires_at.isoformat()} for s in sessions]}

    async def revoke_session(self, session_id: str, reason: str) -> dict:
        """PROVEN: ownership read, then Redis DELETE (immediate effect), then DB write (audit).
        The ownership read is a read-only lookup, not the audit write --
        Redis is still cleared before any DB mutation, preserving the
        original immediate-invalidation guarantee for the write path."""
        # Slice 2F-39A2R fix (HIGH severity, observed and recorded
        # unremediated since Slice 2F-26D/F/G/H's
        # security-observations-not-remediated.md): the caller's own
        # identity was never checked against the session being revoked --
        # any authenticated principal could revoke any other user's
        # session given only its id. Ownership is now verified
        # (super_admin exempt) before the Redis delete or DB update runs;
        # a foreign session is treated identically to a missing one
        # (non-oracular), consistent with this program's established
        # object-ownership pattern.
        r = await self.db.execute(select(SessionInventory).where(
            SessionInventory.session_id == session_id,
            SessionInventory.is_active == True))
        session = r.scalar_one_or_none()
        if not session:
            return {"session_id": session_id, "revoked": True, "note": "Already expired"}
        if self.actor_role != "super_admin" and self.actor_id is not None and session.user_id != self.actor_id:
            return {"session_id": session_id, "revoked": True, "note": "Already expired"}
        # Redis delete only after ownership is confirmed.
        try:
            await self.redis.delete(REDIS_SESSION.format(session_id=session_id))
        except Exception:
            pass
        await self._revoke_session_record(session, reason)
        await self._write_audit("session.revoke", "security", session_id,
                                 after={"reason": reason})
        return {"session_id": session_id, "revoked": True, "reason": reason}

    async def _revoke_session_record(self, session: SessionInventory, reason: str) -> None:
        session.is_active = False
        session.revoked_at = utcnow()
        session.revoked_by = self.actor_id
        session.revoke_reason = reason
        try:
            await self.redis.delete(REDIS_SESSION.format(session_id=session.session_id))
        except Exception:
            pass

    async def revoke_all_sessions(self, user_id: uuid.UUID, reason: str) -> dict:
        """Force logout all devices. PROVEN: Redis cleared first."""
        try:
            session_ids = await self.redis.smembers(
                REDIS_USER_SESSIONS.format(user_id=user_id))
            for sid in session_ids:
                sid_str = sid.decode() if isinstance(sid, bytes) else sid
                await self.redis.delete(REDIS_SESSION.format(session_id=sid_str))
            await self.redis.delete(REDIS_USER_SESSIONS.format(user_id=user_id))
        except Exception:
            pass
        r = await self.db.execute(select(SessionInventory).where(
            SessionInventory.user_id == user_id,
            SessionInventory.is_active == True))
        sessions = r.scalars().all()
        for s in sessions:
            await self._revoke_session_record(s, reason)
        await self._write_audit("session.revoke_all", "security", str(user_id),
                                 after={"reason": reason, "count": len(sessions)})
        await self._publish("security.all_sessions_revoked", "platform", str(user_id),
                            {"user_id": str(user_id), "count": len(sessions)})
        return {"user_id": str(user_id), "sessions_revoked": len(sessions), "reason": reason}

    async def get_security_summary(self, tenant_id: uuid.UUID | None) -> dict:
        """Platform-wide security overview for super admin dashboard."""
        blocked_ip_r = await self.db.execute(select(func.count(IPBlocklistEntry.id)).where(
            IPBlocklistEntry.is_active == True))
        blocked_ips = blocked_ip_r.scalar_one_or_none() or 0

        threat_r = await self.db.execute(select(func.count(SuspiciousActivityLog.id)).where(
            SuspiciousActivityLog.status == "open",
            SuspiciousActivityLog.threat_level.in_(
                [ThreatLevel.HIGH, ThreatLevel.CRITICAL])))
        open_threats = threat_r.scalar_one_or_none() or 0

        session_r = await self.db.execute(select(func.count(SessionInventory.id)).where(
            SessionInventory.is_active == True,
            *([SessionInventory.tenant_id == tenant_id] if tenant_id else [])))
        active_sessions = session_r.scalar_one_or_none() or 0

        result = {"blocked_ips": blocked_ips, "open_high_threats": open_threats,
                  "active_sessions": active_sessions, "generated_at": utcnow().isoformat()}
        if get_settings().API_KEYS_ENABLED:
            active_key_r = await self.db.execute(select(func.count(APIKey.id)).where(
                APIKey.status == APIKeyStatus.ACTIVE,
                *([APIKey.tenant_id == tenant_id] if tenant_id else [])))
            result["active_api_keys"] = active_key_r.scalar_one_or_none() or 0
        return result
