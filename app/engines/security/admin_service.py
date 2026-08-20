"""Security Enterprise Upgrade — SecurityAdminService.

Backs the Admin -> Security & Threats SOC (7 tabs): Overview, Threats,
Active Sessions, IP Blocklist, API Keys, Audit Logs, Security Policies.

Composes the existing SecurityService (hash_api_key/generate_api_key/
Redis blocklist sync) rather than duplicating it. Sessions are read from
auth.UserSession/auth.LoginEvent (the tables actually written at login) —
security.SessionInventory has zero writers and is not used here.
"""
from __future__ import annotations
import csv
import io
import ipaddress
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update, func, or_, and_, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.security.constants import (
    APIKeyStatus, ActivityType, ThreatLevel, HIGH_RISK_OPERATIONS,
    generate_api_key, hash_api_key, extract_prefix, ALL_SCOPES,
    REDIS_IP_BLOCKLIST, REDIS_API_KEY_CACHE,
)
from app.engines.security.models import (
    APIKey, IPBlocklistEntry, SuspiciousActivityLog, PlatformAuditLog,
    IPBlockHit, ApiKeyUsageLog, SecurityPolicy,
)
from app.engines.security.service import SecurityService
from app.engines.auth.models import User, UserSession, LoginEvent
from app.exceptions import ServiceOSException, NotFoundException
from app.core.audit import record_platform_audit
from app.config import get_settings
from app.schemas.base import encode_cursor, decode_cursor

utcnow = lambda: datetime.now(timezone.utc)

THREAT_STATUSES = ("open", "investigating", "contained", "resolved", "false_positive", "ignored")
THREAT_LEVELS = (ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL)
IP_BLOCK_SCOPES = ("all", "admin", "tenant", "customer", "staff")
API_KEY_ENVIRONMENTS = ("live", "test")

POLICY_RULES = {
    "mfa_required_super_admin": (bool, None, None),
    "mfa_required_platform_admin": (bool, None, None),
    "failed_login_threshold": (int, 3, 20),
    "auto_lock_threshold": (int, 5, 50),
    "session_max_lifetime_minutes": (int, 15, 43200),
    "idle_timeout_minutes": (int, 5, 1440),
    "max_concurrent_sessions": (int, 1, 100),
    "api_key_max_expiry_days": (int, 1, 730),
    "ip_block_auto_expiry_default_days": (int, 1, 365),
    "export_audit_retention_days": (int, 30, 3650),
}


class SecurityAdminService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None,
                 actor_ip: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_ip = actor_ip
        self.sec = SecurityService(db, request_id, actor_id, actor_role, actor_ip)

    async def _audit(self, operation: str, entity_id: str | None = None,
                      entity_type: str | None = None, tenant_id=None,
                      before: dict | None = None, after: dict | None = None) -> None:
        await record_platform_audit(
            self.db, operation=operation, engine_id="security",
            entity_id=entity_id, entity_type=entity_type, tenant_id=tenant_id,
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.actor_ip,
            request_id=self.request_id, before=before, after=after,
        )

    # ─────────────────────────────────────────────────────────────────────
    # OVERVIEW
    # ─────────────────────────────────────────────────────────────────────

    async def get_security_overview(self) -> dict:
        idle_cutoff = utcnow() - timedelta(minutes=int(await self._policy_value("idle_timeout_minutes", 30)))
        open_threats_r = await self.db.execute(select(func.count(SuspiciousActivityLog.id)).where(
            SuspiciousActivityLog.status.in_(("open", "investigating"))))
        open_threats = open_threats_r.scalar_one_or_none() or 0

        critical_threats_r = await self.db.execute(select(func.count(SuspiciousActivityLog.id)).where(
            SuspiciousActivityLog.status.in_(("open", "investigating")),
            SuspiciousActivityLog.threat_level == ThreatLevel.CRITICAL))
        critical_threats = critical_threats_r.scalar_one_or_none() or 0

        active_sessions_r = await self.db.execute(select(func.count(UserSession.id)).where(
            UserSession.revoked_at.is_(None),
            or_(UserSession.expires_at.is_(None), UserSession.expires_at > utcnow()),
            UserSession.last_active_at > idle_cutoff))
        active_sessions = active_sessions_r.scalar_one_or_none() or 0

        blocked_ips_r = await self.db.execute(select(func.count(IPBlocklistEntry.id)).where(
            IPBlocklistEntry.status == "active"))
        blocked_ips = blocked_ips_r.scalar_one_or_none() or 0

        active_keys = 0
        expiring_keys = 0
        if get_settings().API_KEYS_ENABLED:
            active_keys_r = await self.db.execute(select(func.count(APIKey.id)).where(
                APIKey.status == APIKeyStatus.ACTIVE))
            active_keys = active_keys_r.scalar_one_or_none() or 0

            expiring_keys_r = await self.db.execute(select(func.count(APIKey.id)).where(
                APIKey.status == APIKeyStatus.ACTIVE,
                APIKey.expires_at.isnot(None),
                APIKey.expires_at < utcnow() + timedelta(days=30)))
            expiring_keys = expiring_keys_r.scalar_one_or_none() or 0

        failed_logins_24h_r = await self.db.execute(select(func.count(LoginEvent.id)).where(
            LoginEvent.event_type == "login_failed",
            LoginEvent.created_at > utcnow() - timedelta(hours=24)))
        failed_logins_24h = failed_logins_24h_r.scalar_one_or_none() or 0

        high_risk_audit_24h_r = await self.db.execute(select(func.count(PlatformAuditLog.id)).where(
            PlatformAuditLog.is_high_risk == True,
            PlatformAuditLog.created_at > utcnow() - timedelta(hours=24)))
        high_risk_audit_24h = high_risk_audit_24h_r.scalar_one_or_none() or 0

        recent_threats_r = await self.db.execute(select(SuspiciousActivityLog).where(
            SuspiciousActivityLog.status.in_(("open", "investigating"))
        ).order_by(SuspiciousActivityLog.created_at.desc()).limit(5))
        recent_threats = [self._threat_to_dict(t) for t in recent_threats_r.scalars().all()]

        recent_audit_r = await self.db.execute(select(PlatformAuditLog).where(
            PlatformAuditLog.is_high_risk == True
        ).order_by(PlatformAuditLog.created_at.desc()).limit(5))
        recent_audit = [self._audit_to_dict(a) for a in recent_audit_r.scalars().all()]

        top_blocked_r = await self.db.execute(select(IPBlocklistEntry).where(
            IPBlocklistEntry.status == "active"
        ).order_by(IPBlocklistEntry.hit_count.desc()).limit(5))
        top_blocked = [self._ip_block_to_dict(e) for e in top_blocked_r.scalars().all()]

        return {
            "summary_cards": {
                "open_threats": open_threats, "critical_threats": critical_threats,
                "active_sessions": active_sessions, "blocked_ips": blocked_ips,
                "active_api_keys": active_keys, "expiring_api_keys": expiring_keys,
                "failed_logins_24h": failed_logins_24h,
                "high_risk_audit_events_24h": high_risk_audit_24h,
            },
            "recent_threats": recent_threats,
            "recent_high_risk_audit": recent_audit,
            "top_blocked_ips": top_blocked,
            "generated_at": utcnow().isoformat(),
        }

    # ─────────────────────────────────────────────────────────────────────
    # THREATS (SuspiciousActivityLog)
    # ─────────────────────────────────────────────────────────────────────

    def _threat_to_dict(self, t: SuspiciousActivityLog) -> dict:
        return {
            "threat_id": str(t.id), "threat_number": t.threat_number,
            "activity_type": t.activity_type, "threat_level": t.threat_level,
            "risk_score": t.risk_score, "source": t.source,
            "entity_id": t.entity_id, "entity_type": t.entity_type,
            "target_user_id": str(t.target_user_id) if t.target_user_id else None,
            "assigned_to_admin_id": str(t.assigned_to_admin_id) if t.assigned_to_admin_id else None,
            "description": t.description, "ip_address": t.ip_address,
            "detected_value": t.detected_value, "threshold": t.threshold,
            "status": t.status, "context": t.context,
            "last_seen_at": t.last_seen_at.isoformat() if t.last_seen_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            "created_at": t.created_at.isoformat(),
        }

    async def list_threats(self, status: str | None, threat_level: str | None,
                            activity_type: str | None, search: str | None,
                            limit: int, cursor: str | None) -> dict:
        q = select(SuspiciousActivityLog).order_by(
            SuspiciousActivityLog.created_at.desc(), SuspiciousActivityLog.id.desc())
        if status: q = q.where(SuspiciousActivityLog.status == status)
        if threat_level: q = q.where(SuspiciousActivityLog.threat_level == threat_level)
        if activity_type: q = q.where(SuspiciousActivityLog.activity_type == activity_type)
        if search:
            like = f"%{search}%"
            q = q.where(or_(SuspiciousActivityLog.threat_number.ilike(like),
                            SuspiciousActivityLog.description.ilike(like),
                            SuspiciousActivityLog.ip_address.ilike(like)))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(tuple_(SuspiciousActivityLog.created_at, SuspiciousActivityLog.id) < tuple_(
                    datetime.fromisoformat(c["created_at"]), uuid.UUID(c["id"])))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat(), "id": str(items[-1].id)}) if has_next and items else None
        return {"threats": [self._threat_to_dict(t) for t in items],
                "has_next": has_next, "next_cursor": nc}

    async def get_threat_detail(self, threat_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(SuspiciousActivityLog).where(SuspiciousActivityLog.id == threat_id))
        t = r.scalar_one_or_none()
        if not t: raise NotFoundException("SuspiciousActivityLog", str(threat_id))
        actions_r = await self.db.execute(select(PlatformAuditLog).where(
            PlatformAuditLog.entity_id == str(threat_id),
            PlatformAuditLog.engine_id == "security",
        ).order_by(PlatformAuditLog.created_at.desc()).limit(50))
        actions = [self._audit_to_dict(a) for a in actions_r.scalars().all()]
        return {**self._threat_to_dict(t), "actions_taken": actions}

    async def assign_threat(self, threat_id: uuid.UUID, admin_id: uuid.UUID) -> dict:
        t = await self._get_threat(threat_id)
        admin_r = await self.db.execute(select(User).where(
            User.id == admin_id, User.is_active.is_(True),
            or_(User.role == "super_admin", User.role.like("admin_%"))))
        if admin_r.scalar_one_or_none() is None:
            raise ServiceOSException("VALIDATION_ERROR", "Assignee must be an active platform administrator.")
        before = {"assigned_to_admin_id": str(t.assigned_to_admin_id) if t.assigned_to_admin_id else None}
        t.assigned_to_admin_id = admin_id
        await self._audit("threat.assign", str(threat_id), "security_threat",
                           before=before, after={"assigned_to_admin_id": str(admin_id)})
        return {"threat_id": str(threat_id), "assigned_to_admin_id": str(admin_id)}

    async def update_threat_status(self, threat_id: uuid.UUID, status: str, notes: str | None = None) -> dict:
        if status not in THREAT_STATUSES:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid status. Valid: {THREAT_STATUSES}")
        t = await self._get_threat(threat_id)
        before = {"status": t.status}
        t.status = status
        if status in ("resolved", "false_positive", "ignored"):
            t.resolved_at = utcnow()
        await self._audit(f"threat.mark_{status}", str(threat_id), "security_threat",
                           before=before, after={"status": status, "notes": notes})
        return {"threat_id": str(threat_id), "status": status}

    async def _get_threat(self, threat_id: uuid.UUID) -> SuspiciousActivityLog:
        r = await self.db.execute(select(SuspiciousActivityLog).where(SuspiciousActivityLog.id == threat_id))
        t = r.scalar_one_or_none()
        if not t: raise NotFoundException("SuspiciousActivityLog", str(threat_id))
        return t

    async def block_ip_from_threat(self, threat_id: uuid.UUID, reason: str, expires_hours: int | None = 720) -> dict:
        t = await self._get_threat(threat_id)
        if not t.ip_address:
            raise ServiceOSException("VALIDATION_ERROR", "Threat has no associated IP address.")
        result = await self.create_ip_block(t.ip_address, "ip", reason, t.threat_level,
                                             scope="all", tenant_id=t.tenant_id,
                                             expires_hours=expires_hours)
        await self._audit("threat.block_ip", str(threat_id), "security_threat",
                           after={"ip_address": t.ip_address, "block_entry_id": result["entry_id"]})
        return result

    async def revoke_sessions_from_threat(self, threat_id: uuid.UUID, reason: str) -> dict:
        t = await self._get_threat(threat_id)
        if not t.target_user_id:
            raise ServiceOSException("VALIDATION_ERROR", "Threat has no associated user.")
        result = await self.revoke_all_user_sessions(t.target_user_id, reason)
        await self._audit("threat.revoke_sessions", str(threat_id), "security_threat",
                           after={"user_id": str(t.target_user_id), "sessions_revoked": result["sessions_revoked"]})
        return result

    # ─────────────────────────────────────────────────────────────────────
    # ACTIVE SESSIONS (auth.UserSession + auth.LoginEvent)
    # ─────────────────────────────────────────────────────────────────────

    async def list_sessions(self, tenant_id: uuid.UUID | None, role: str | None,
                             active_only: bool, search: str | None,
                             limit: int, cursor: str | None) -> dict:
        q = select(UserSession, User).join(User, User.id == UserSession.user_id).order_by(
            UserSession.last_active_at.desc(), UserSession.id.desc())
        if active_only:
            idle_cutoff = utcnow() - timedelta(minutes=int(await self._policy_value("idle_timeout_minutes", 30)))
            q = q.where(UserSession.revoked_at.is_(None),
                        or_(UserSession.expires_at.is_(None), UserSession.expires_at > utcnow()),
                        UserSession.last_active_at > idle_cutoff)
        if tenant_id: q = q.where(UserSession.tenant_id == tenant_id)
        if role: q = q.where(User.role == role)
        if search:
            like = f"%{search}%"
            q = q.where(or_(User.email.ilike(like), User.full_name.ilike(like),
                            UserSession.ip_address.ilike(like),
                            UserSession.device_name.ilike(like),
                            UserSession.device_id.ilike(like)))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(tuple_(UserSession.last_active_at, UserSession.id) < tuple_(
                    datetime.fromisoformat(c["last_active_at"]), uuid.UUID(c["id"])))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        rows = r.all()
        has_next = len(rows) > limit; rows = rows[:limit]
        nc = encode_cursor({"last_active_at": rows[-1][0].last_active_at.isoformat(),
                            "id": str(rows[-1][0].id)}) if has_next and rows else None
        return {"sessions": [self._session_to_dict(s, u) for s, u in rows],
                "has_next": has_next, "next_cursor": nc}

    def _session_to_dict(self, s: UserSession, u: User) -> dict:
        is_active = s.revoked_at is None and (s.expires_at is None or s.expires_at > utcnow())
        return {
            "session_id": str(s.id), "user_id": str(s.user_id), "user_email": u.email,
            "user_name": u.full_name, "user_role": u.role, "tenant_id": str(s.tenant_id) if s.tenant_id else None,
            "device_id": s.device_id, "device_name": s.device_name, "device_type": s.device_type,
            "ip_address": s.ip_address, "is_trusted": s.is_trusted, "is_approved": s.is_approved,
            "status": "active" if is_active else "revoked",
            "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
            "revocation_reason": s.revocation_reason,
        }

    async def get_session_detail(self, session_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(UserSession, User).join(User, User.id == UserSession.user_id).where(
            UserSession.id == session_id))
        row = r.first()
        if not row: raise NotFoundException("UserSession", str(session_id))
        s, u = row
        history_r = await self.db.execute(select(LoginEvent).where(
            LoginEvent.user_id == s.user_id
        ).order_by(LoginEvent.created_at.desc()).limit(20))
        history = [{"event_type": e.event_type, "ip_address": e.ip_address,
                    "failure_reason": e.failure_reason, "created_at": e.created_at.isoformat()}
                   for e in history_r.scalars().all()]
        return {**self._session_to_dict(s, u), "login_history": history}

    async def revoke_session(self, session_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(UserSession).where(UserSession.id == session_id))
        s = r.scalar_one_or_none()
        if not s: raise NotFoundException("UserSession", str(session_id))
        if s.revoked_at is not None:
            raise ServiceOSException("CONFLICT", "Session already revoked.")
        s.revoked_at = utcnow()
        s.revoked_by_user_id = self.actor_id
        s.revocation_reason = reason
        try:
            from app.engines.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES
            await self.sec.redis.setex(
                f"serviceos:session:revoked:{session_id}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
        except Exception:
            pass
        await self._audit("session.revoke", str(session_id), "user_session",
                           tenant_id=s.tenant_id, after={"reason": reason})
        return {"session_id": str(session_id), "revoked": True, "reason": reason}

    async def revoke_all_user_sessions(self, user_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)))
        sessions = r.scalars().all()
        for s in sessions:
            s.revoked_at = utcnow(); s.revoked_by_user_id = self.actor_id; s.revocation_reason = reason
            try:
                from app.engines.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES
                await self.sec.redis.setex(
                    f"serviceos:session:revoked:{s.id}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
            except Exception:
                pass
        await self._audit("session.revoke_all", str(user_id), "user",
                           after={"reason": reason, "count": len(sessions)})
        return {"user_id": str(user_id), "sessions_revoked": len(sessions), "reason": reason}

    # ─────────────────────────────────────────────────────────────────────
    # IP BLOCKLIST
    # ─────────────────────────────────────────────────────────────────────

    def _ip_block_to_dict(self, e: IPBlocklistEntry) -> dict:
        return {
            "entry_id": str(e.id), "ip_or_cidr": e.ip_or_cidr, "entry_type": e.entry_type,
            "threat_level": e.threat_level, "reason": e.reason, "scope": e.scope,
            "status": e.status, "is_global": e.is_global,
            "tenant_id": str(e.tenant_id) if e.tenant_id else None,
            "hit_count": e.hit_count,
            "last_hit_at": e.last_hit_at.isoformat() if e.last_hit_at else None,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "revoked_at": e.revoked_at.isoformat() if e.revoked_at else None,
            "created_at": e.created_at.isoformat(),
        }

    async def list_ip_blocklist(self, status: str | None, scope: str | None,
                                 search: str | None, limit: int, cursor: str | None) -> dict:
        q = select(IPBlocklistEntry).order_by(
            IPBlocklistEntry.created_at.desc(), IPBlocklistEntry.id.desc())
        if status: q = q.where(IPBlocklistEntry.status == status)
        if scope: q = q.where(IPBlocklistEntry.scope == scope)
        if search: q = q.where(IPBlocklistEntry.ip_or_cidr.ilike(f"%{search}%"))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(tuple_(IPBlocklistEntry.created_at, IPBlocklistEntry.id) < tuple_(
                    datetime.fromisoformat(c["created_at"]), uuid.UUID(c["id"])))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat(), "id": str(items[-1].id)}) if has_next and items else None
        return {"entries": [self._ip_block_to_dict(e) for e in items],
                "has_next": has_next, "next_cursor": nc}

    async def create_ip_block(self, ip_or_cidr: str, entry_type: str, reason: str,
                               threat_level: str, scope: str = "all",
                               tenant_id: uuid.UUID | None = None,
                               expires_hours: int | None = None,
                               override_self_block: bool = False,
                               permanent: bool = False) -> dict:
        try:
            network = ipaddress.ip_network(ip_or_cidr, strict=False)
        except ValueError:
            raise ServiceOSException("VALIDATION_ERROR", f"'{ip_or_cidr}' is not a valid IP or CIDR.")

        entry_type = "ip" if network.prefixlen == network.max_prefixlen else "cidr"
        ip_or_cidr = str(network.network_address) if entry_type == "ip" else str(network)
        reason = reason.strip()
        if len(reason) < 5:
            raise ServiceOSException("VALIDATION_ERROR", "A meaningful block reason is required (minimum 5 characters).")
        if threat_level not in THREAT_LEVELS:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid threat level. Valid: {THREAT_LEVELS}")
        if scope not in IP_BLOCK_SCOPES:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid scope. Valid: {IP_BLOCK_SCOPES}")
        if scope == "tenant" and tenant_id is None:
            raise ServiceOSException("VALIDATION_ERROR", "A tenant is required for a tenant-scoped block.")

        existing_r = await self.db.execute(select(IPBlocklistEntry.id).where(
            IPBlocklistEntry.ip_or_cidr == ip_or_cidr,
            IPBlocklistEntry.status == "active",
            IPBlocklistEntry.tenant_id.is_(None) if tenant_id is None else IPBlocklistEntry.tenant_id == tenant_id,
        ).limit(1))
        if existing_r.scalar_one_or_none():
            raise ServiceOSException("CONFLICT", "This IP or CIDR is already actively blocked in the selected scope.")

        if self.actor_ip and not override_self_block:
            try:
                if ipaddress.ip_address(self.actor_ip) in ipaddress.ip_network(ip_or_cidr, strict=False):
                    raise ServiceOSException("VALIDATION_ERROR",
                        "This would block your own current IP address. Pass override_self_block=true to confirm.")
            except ValueError:
                pass

        if expires_hours is None and not permanent:
            expires_hours = int(await self._policy_value("ip_block_auto_expiry_default_days", 30)) * 24
        expires_at = utcnow() + timedelta(hours=expires_hours) if expires_hours else None
        entry = IPBlocklistEntry(
            ip_or_cidr=ip_or_cidr, entry_type=entry_type, reason=reason,
            threat_level=threat_level, is_global=(scope == "all"), scope=scope,
            status="active", tenant_id=tenant_id, expires_at=expires_at,
            blocked_by=self.actor_id,
        )
        self.db.add(entry); await self.db.flush()
        try:
            redis_set = REDIS_IP_BLOCKLIST if entry_type == "ip" else "serviceos:security:cidr_blocklist"
            await self.sec.redis.sadd(redis_set, ip_or_cidr)
        except Exception:
            pass
        await self._audit("ip.block", str(entry.id), "ip_blocklist_entry", tenant_id=tenant_id,
                           after={"ip_or_cidr": ip_or_cidr, "reason": reason, "threat_level": threat_level,
                                  "scope": scope})
        return {"entry_id": str(entry.id), "ip_or_cidr": ip_or_cidr, "status": "active"}

    async def update_ip_block(self, entry_id: uuid.UUID, **fields) -> dict:
        r = await self.db.execute(select(IPBlocklistEntry).where(IPBlocklistEntry.id == entry_id))
        e = r.scalar_one_or_none()
        if not e: raise NotFoundException("IPBlocklistEntry", str(entry_id))
        if fields.get("scope") is not None and fields["scope"] not in IP_BLOCK_SCOPES:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid scope. Valid: {IP_BLOCK_SCOPES}")
        if fields.get("threat_level") is not None and fields["threat_level"] not in THREAT_LEVELS:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid threat level. Valid: {THREAT_LEVELS}")
        if fields.get("reason") is not None and len(fields["reason"].strip()) < 5:
            raise ServiceOSException("VALIDATION_ERROR", "A meaningful reason is required (minimum 5 characters).")
        before = self._ip_block_to_dict(e)
        for k, v in fields.items():
            if v is not None and hasattr(e, k):
                setattr(e, k, v)
        await self._audit("ip.update", str(entry_id), "ip_blocklist_entry",
                           before=before, after=self._ip_block_to_dict(e))
        return self._ip_block_to_dict(e)

    async def revoke_ip_block(self, entry_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(IPBlocklistEntry).where(IPBlocklistEntry.id == entry_id))
        e = r.scalar_one_or_none()
        if not e: raise NotFoundException("IPBlocklistEntry", str(entry_id))
        if e.status != "active":
            raise ServiceOSException("CONFLICT", f"Entry is already {e.status}.")
        e.status = "revoked"; e.is_active = False
        e.revoked_at = utcnow(); e.revoked_by_user_id = self.actor_id
        try:
            redis_set = REDIS_IP_BLOCKLIST if e.entry_type == "ip" else "serviceos:security:cidr_blocklist"
            await self.sec.redis.srem(redis_set, e.ip_or_cidr)
        except Exception:
            pass
        await self._audit("ip.unblock", str(entry_id), "ip_blocklist_entry", after={"reason": reason})
        return {"entry_id": str(entry_id), "revoked": True, "reason": reason}

    async def get_ip_block_hits(self, entry_id: uuid.UUID, limit: int = 50) -> dict:
        r = await self.db.execute(select(IPBlockHit).where(
            IPBlockHit.block_id == entry_id
        ).order_by(IPBlockHit.hit_at.desc()).limit(limit))
        hits = r.scalars().all()
        return {"entry_id": str(entry_id), "hits": [{
            "hit_at": h.hit_at.isoformat(), "path": h.path, "method": h.method,
            "user_agent": h.user_agent, "blocked_scope": h.blocked_scope} for h in hits]}

    # ─────────────────────────────────────────────────────────────────────
    # API KEYS
    # ─────────────────────────────────────────────────────────────────────

    def _api_key_to_dict(self, k: APIKey) -> dict:
        return {
            "key_id": str(k.id), "tenant_id": str(k.tenant_id) if k.tenant_id else None,
            "name": k.name, "description": k.description,
            "key_prefix": f"sk_{k.environment}_{k.key_prefix}...",
            "environment": k.environment, "scopes": k.scopes,
            "owner_type": k.owner_type, "rate_limit_per_minute": k.rate_limit_per_minute,
            "permissions": k.permissions_json, "status": k.status,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "use_count": k.use_count, "created_at": k.created_at.isoformat(),
        }

    async def list_api_keys(self, tenant_id: uuid.UUID | None, status: str | None,
                             search: str | None, limit: int, cursor: str | None) -> dict:
        q = select(APIKey).order_by(APIKey.created_at.desc(), APIKey.id.desc())
        if tenant_id: q = q.where(APIKey.tenant_id == tenant_id)
        if status: q = q.where(APIKey.status == status)
        if search: q = q.where(APIKey.name.ilike(f"%{search}%"))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(tuple_(APIKey.created_at, APIKey.id) < tuple_(
                    datetime.fromisoformat(c["created_at"]), uuid.UUID(c["id"])))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat(), "id": str(items[-1].id)}) if has_next and items else None
        return {"api_keys": [self._api_key_to_dict(k) for k in items],
                "has_next": has_next, "next_cursor": nc}

    async def create_api_key(self, tenant_id: uuid.UUID, name: str, description: str | None,
                              scopes: list, environment: str, expires_days: int | None,
                              owner_type: str = "tenant", allowed_ips: list | None = None,
                              rate_limit_per_minute: int | None = None,
                              permissions: list | None = None) -> dict:
        name = name.strip()
        if len(name) < 3:
            raise ServiceOSException("VALIDATION_ERROR", "API key name must contain at least 3 characters.")
        if not scopes:
            raise ServiceOSException("VALIDATION_ERROR", "Select at least one API scope.")
        if environment not in API_KEY_ENVIRONMENTS:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid environment. Valid: {API_KEY_ENVIRONMENTS}")
        max_expiry = int(await self._policy_value("api_key_max_expiry_days", 365))
        if expires_days is not None and not 1 <= expires_days <= max_expiry:
            raise ServiceOSException("VALIDATION_ERROR", f"Expiry must be between 1 and {max_expiry} days.")
        if rate_limit_per_minute is not None and not 1 <= rate_limit_per_minute <= 100000:
            raise ServiceOSException("VALIDATION_ERROR", "Rate limit must be between 1 and 100,000 requests per minute.")
        for raw_ip in allowed_ips or []:
            try:
                ipaddress.ip_network(raw_ip.strip(), strict=False)
            except ValueError:
                raise ServiceOSException("VALIDATION_ERROR", f"'{raw_ip}' is not a valid allowed IP or CIDR.")
        result = await self.sec.create_api_key(tenant_id, name, description, scopes,
                                                environment, expires_days)
        r = await self.db.execute(select(APIKey).where(APIKey.id == uuid.UUID(result["key_id"])))
        key = r.scalar_one_or_none()
        if key:
            key.owner_type = owner_type
            key.allowed_ips_json = allowed_ips
            key.rate_limit_per_minute = rate_limit_per_minute
            key.permissions_json = permissions or []
        # audit already written by sec.create_api_key with key_prefix only — never the raw key/hash
        return result

    async def get_api_key_detail(self, key_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(APIKey).where(APIKey.id == key_id))
        k = r.scalar_one_or_none()
        if not k: raise NotFoundException("APIKey", str(key_id))
        return self._api_key_to_dict(k)

    async def rotate_api_key(self, key_id: uuid.UUID, tenant_id: uuid.UUID, reason: str) -> dict:
        reason = reason.strip()
        if len(reason) < 5:
            raise ServiceOSException("VALIDATION_ERROR", "A meaningful rotation reason is required.")
        result = await self.sec.rotate_api_key(key_id, tenant_id)
        await self._audit("api_key.rotate_reason", str(key_id), "api_key",
                          tenant_id=tenant_id, after={"reason": reason,
                          "new_key_id": result.get("key_id")})
        return result

    async def revoke_api_key(self, key_id: uuid.UUID, tenant_id: uuid.UUID, reason: str) -> dict:
        return await self.sec.revoke_api_key(key_id, tenant_id, reason)

    async def get_api_key_usage(self, key_id: uuid.UUID, limit: int = 50) -> dict:
        r = await self.db.execute(select(ApiKeyUsageLog).where(
            ApiKeyUsageLog.api_key_id == key_id
        ).order_by(ApiKeyUsageLog.used_at.desc()).limit(limit))
        logs = r.scalars().all()
        return {"key_id": str(key_id), "usage": [{
            "used_at": u.used_at.isoformat(), "endpoint": u.endpoint, "method": u.method,
            "status_code": u.status_code, "ip_address": u.ip_address,
            "response_ms": u.response_ms} for u in logs]}

    # ─────────────────────────────────────────────────────────────────────
    # AUDIT LOGS
    # ─────────────────────────────────────────────────────────────────────

    def _audit_to_dict(self, a: PlatformAuditLog) -> dict:
        return {
            "log_id": str(a.id), "operation": a.operation, "engine_id": a.engine_id,
            "entity_type": a.entity_type, "entity_id": a.entity_id,
            "tenant_id": str(a.tenant_id) if a.tenant_id else None,
            "actor_id": str(a.actor_id) if a.actor_id else None,
            "actor_role": a.actor_role, "actor_ip": a.actor_ip,
            "is_high_risk": a.is_high_risk,
            "before_state": a.before_state, "after_state": a.after_state,
            "created_at": a.created_at.isoformat(),
        }

    async def list_audit_logs(self, engine_id: str | None, operation: str | None,
                               actor_role: str | None, tenant_id: uuid.UUID | None,
                               is_high_risk: bool | None, search: str | None,
                               date_from: datetime | None, date_to: datetime | None,
                               limit: int, cursor: str | None) -> dict:
        q = select(PlatformAuditLog).order_by(
            PlatformAuditLog.created_at.desc(), PlatformAuditLog.id.desc())
        if engine_id: q = q.where(PlatformAuditLog.engine_id == engine_id)
        if operation: q = q.where(PlatformAuditLog.operation == operation)
        if actor_role: q = q.where(PlatformAuditLog.actor_role == actor_role)
        if tenant_id: q = q.where(PlatformAuditLog.tenant_id == tenant_id)
        if is_high_risk is not None: q = q.where(PlatformAuditLog.is_high_risk == is_high_risk)
        if date_from: q = q.where(PlatformAuditLog.created_at >= date_from)
        if date_to: q = q.where(PlatformAuditLog.created_at <= date_to)
        if search:
            like = f"%{search}%"
            q = q.where(or_(PlatformAuditLog.operation.ilike(like),
                            PlatformAuditLog.entity_id.ilike(like),
                            PlatformAuditLog.actor_ip.ilike(like)))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(tuple_(PlatformAuditLog.created_at, PlatformAuditLog.id) < tuple_(
                    datetime.fromisoformat(c["created_at"]), uuid.UUID(c["id"])))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat(), "id": str(items[-1].id)}) if has_next and items else None
        return {"audit_logs": [self._audit_to_dict(a) for a in items],
                "has_next": has_next, "next_cursor": nc,
                "note": "Audit log is append-only. No entries can be modified or deleted."}

    async def get_audit_log_detail(self, log_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(PlatformAuditLog).where(PlatformAuditLog.id == log_id))
        a = r.scalar_one_or_none()
        if not a: raise NotFoundException("PlatformAuditLog", str(log_id))
        return self._audit_to_dict(a)

    async def export_audit_logs(self, engine_id: str | None, operation: str | None,
                                 date_from: datetime | None, date_to: datetime | None) -> str:
        retention_days = int(await self._policy_value("export_audit_retention_days", 365))
        earliest = utcnow() - timedelta(days=retention_days)
        if date_from is None or date_from < earliest:
            date_from = earliest
        result = await self.list_audit_logs(engine_id, operation, None, None, None, None,
                                             date_from, date_to, limit=5000, cursor=None)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["log_id", "operation", "engine_id", "entity_type", "entity_id",
                          "actor_role", "actor_ip", "is_high_risk", "created_at"])
        for row in result["audit_logs"]:
            writer.writerow([row["log_id"], row["operation"], row["engine_id"],
                              row["entity_type"], row["entity_id"], row["actor_role"],
                              row["actor_ip"], row["is_high_risk"], row["created_at"]])
        await self._audit("audit.export", entity_type="audit_export",
                           after={"engine_id": engine_id, "operation": operation,
                                  "row_count": len(result["audit_logs"])})
        return buf.getvalue()

    # ─────────────────────────────────────────────────────────────────────
    # SECURITY POLICIES
    # ─────────────────────────────────────────────────────────────────────

    async def get_policies(self) -> dict:
        r = await self.db.execute(select(SecurityPolicy).order_by(SecurityPolicy.policy_key.asc()))
        items = [p.to_dict() for p in r.scalars().all()]
        if not get_settings().API_KEYS_ENABLED:
            items = [item for item in items if item["policy_key"] != "api_key_max_expiry_days"]
        for item in items:
            item["value_type"] = "boolean" if isinstance(item["policy_value"], bool) else "number"
            rule = POLICY_RULES.get(item["policy_key"])
            item["minimum"] = rule[1] if rule else None
            item["maximum"] = rule[2] if rule else None
            item["enforcement"] = "runtime"
        return {"policies": items}

    async def _policy_value(self, policy_key: str, default):
        r = await self.db.execute(select(SecurityPolicy.policy_value_json).where(
            SecurityPolicy.policy_key == policy_key))
        value = r.scalar_one_or_none()
        return default if value is None else value

    async def update_policy(self, policy_key: str, value, reason: str) -> dict:
        if policy_key == "api_key_max_expiry_days" and not get_settings().API_KEYS_ENABLED:
            raise NotFoundException("SecurityPolicy", policy_key)
        reason = reason.strip()
        if len(reason) < 8:
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to update a security policy.")
        rule = POLICY_RULES.get(policy_key)
        if not rule:
            raise ServiceOSException("VALIDATION_ERROR", "This policy is not runtime-editable.")
        expected, minimum, maximum = rule
        if expected is int and (isinstance(value, bool) or not isinstance(value, int)):
            raise ServiceOSException("VALIDATION_ERROR", "This policy requires a whole-number value.")
        if expected is bool and not isinstance(value, bool):
            raise ServiceOSException("VALIDATION_ERROR", "This policy requires an enabled/disabled value.")
        if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            raise ServiceOSException("VALIDATION_ERROR", f"Value must be between {minimum} and {maximum}.")
        if policy_key == "failed_login_threshold":
            hard = int(await self._policy_value("auto_lock_threshold", 10))
            if value >= hard:
                raise ServiceOSException("VALIDATION_ERROR", "Warning threshold must be lower than auto-lock threshold.")
        if policy_key == "auto_lock_threshold":
            warning = int(await self._policy_value("failed_login_threshold", 5))
            if value <= warning:
                raise ServiceOSException("VALIDATION_ERROR", "Auto-lock threshold must be higher than warning threshold.")
        if value is True and policy_key in ("mfa_required_super_admin", "mfa_required_platform_admin"):
            roles = ("super_admin",) if policy_key == "mfa_required_super_admin" else (
                "admin_operations", "admin_finance", "admin_support", "admin_security", "admin_readonly")
            missing_r = await self.db.execute(select(func.count(User.id)).where(
                User.role.in_(roles), User.is_active.is_(True), User.is_mfa_enabled.is_(False)))
            missing = int(missing_r.scalar_one_or_none() or 0)
            if missing:
                raise ServiceOSException(
                    "VALIDATION_ERROR",
                    f"MFA cannot be required yet: {missing} active administrator account(s) are not enrolled.")
        r = await self.db.execute(select(SecurityPolicy).where(SecurityPolicy.policy_key == policy_key))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("SecurityPolicy", policy_key)
        before = p.policy_value_json
        p.policy_value_json = value
        p.updated_by_user_id = self.actor_id
        p.updated_reason = reason
        await self._audit("policy.update", policy_key, "security_policy",
                           before={"value": before}, after={"value": value, "reason": reason})
        result = p.to_dict()
        result.update({"value_type": "boolean" if isinstance(value, bool) else "number",
                       "minimum": minimum, "maximum": maximum, "enforcement": "runtime"})
        return result
