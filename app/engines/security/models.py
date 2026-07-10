"""Security Engine — Models (5 tables). All append-only except SessionInventory."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class APIKey(ServiceOSBase):
    """PROVEN: key_hash stored, raw key NEVER persisted after creation.
    key_prefix stored plaintext for O(1) lookup without exposing full key."""
    __tablename__ = "tenant_api_keys"
    __table_args__ = (
        UniqueConstraint("key_hash",   name="uq_ak_hash"),
        UniqueConstraint("key_prefix", name="uq_ak_prefix"),
        Index("ix_ak_tenant", "tenant_id"),
        Index("ix_ak_status", "status"),
    )
    tenant_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    name:         Mapped[str]            = mapped_column(String(100), nullable=False)
    description:  Mapped[str|None]       = mapped_column(String(500), nullable=True)
    # PROVEN: only hash stored — raw key shown once and discarded
    key_hash:     Mapped[str]            = mapped_column(String(64), nullable=False, unique=True)
    # PROVEN: prefix stored for lookup — never the full key
    key_prefix:   Mapped[str]            = mapped_column(String(8), nullable=False, unique=True)
    environment:  Mapped[str]            = mapped_column(String(10), default="live", nullable=False)
    scopes:       Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    status:       Mapped[str]            = mapped_column(String(20), default="active", nullable=False)
    expires_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[str|None]       = mapped_column(String(50), nullable=True)
    use_count:    Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    created_by:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rotated_to:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    revoked_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    revoke_reason:Mapped[str|None]       = mapped_column(String(500), nullable=True)
    # SOC enterprise upgrade (migration 083)
    owner_type:   Mapped[str]            = mapped_column(String(20), default="tenant", nullable=False)
    allowed_ips_json: Mapped[list|None]  = mapped_column(JSONB, nullable=True)
    rate_limit_per_minute: Mapped[int|None] = mapped_column(Integer, nullable=True)
    permissions_json: Mapped[list]       = mapped_column(JSONB, default=list, nullable=False)


class IPBlocklistEntry(ServiceOSBase):
    """Blocked IPs and CIDR ranges. Redis SET is cache — DB is source of truth."""
    __tablename__ = "ip_blocklist"
    __table_args__ = (
        UniqueConstraint("ip_or_cidr", "tenant_id", name="uq_ibl_ip_tenant"),
        Index("ix_ibl_ip",     "ip_or_cidr"),
        Index("ix_ibl_tenant", "tenant_id"),
    )
    ip_or_cidr:  Mapped[str]            = mapped_column(String(50), nullable=False)
    entry_type:  Mapped[str]            = mapped_column(String(10), nullable=False)  # ip or cidr
    tenant_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason:      Mapped[str]            = mapped_column(String(500), nullable=False)
    threat_level:Mapped[str]            = mapped_column(String(20), nullable=False)
    is_global:   Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_active:   Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    expires_at:  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_by:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # SOC enterprise upgrade (migration 083)
    scope:       Mapped[str]            = mapped_column(String(30), default="all", nullable=False)
    status:      Mapped[str]            = mapped_column(String(20), default="active", nullable=False)
    hit_count:   Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at:  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class SuspiciousActivityLog(ServiceOSBase):
    """Real-time threat detection events. APPEND-ONLY."""
    __tablename__ = "suspicious_activity_logs"
    __table_args__ = (
        Index("ix_sal_entity",    "entity_id"),
        Index("ix_sal_type",      "activity_type"),
        Index("ix_sal_threat",    "threat_level"),
        Index("ix_sal_created",   "created_at"),
        Index("ix_sal_tenant",    "tenant_id"),
    )
    tenant_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    entity_id:     Mapped[str|None]       = mapped_column(String(100), nullable=True)
    entity_type:   Mapped[str|None]       = mapped_column(String(30), nullable=True)
    activity_type: Mapped[str]            = mapped_column(String(60), nullable=False)
    threat_level:  Mapped[str]            = mapped_column(String(20), nullable=False)
    description:   Mapped[str]            = mapped_column(String(500), nullable=False)
    ip_address:    Mapped[str|None]       = mapped_column(String(50), nullable=True)
    user_agent:    Mapped[str|None]       = mapped_column(String(500), nullable=True)
    detected_value:Mapped[int]            = mapped_column(Integer, nullable=False)
    threshold:     Mapped[int]            = mapped_column(Integer, nullable=False)
    context:       Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    status:        Mapped[str]            = mapped_column(String(20), default="open", nullable=False)
    acknowledged_by: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    acknowledged_at: Mapped[datetime|None] =mapped_column(DateTime(timezone=True), nullable=True)
    auto_actioned: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    # SOC enterprise upgrade (migration 083) — SuspiciousActivityLog doubles as "Threat" in the SOC UI.
    # status also supports: investigating | contained | resolved | false_positive | ignored (additive)
    threat_number: Mapped[str|None]       = mapped_column(String(60), nullable=True)
    risk_score:    Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    source:        Mapped[str|None]       = mapped_column(String(50), nullable=True)
    target_user_id: Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_to_admin_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_seen_at:  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)


class PlatformAuditLog(ServiceOSBase):
    """PROVEN: append-only centralised audit log.
    Covers ALL write operations across ALL engines.
    No UPDATE or DELETE ever — legally required retention."""
    __tablename__ = "platform_audit_logs"
    __table_args__ = (
        Index("ix_pal_actor",     "actor_id"),
        Index("ix_pal_tenant",    "tenant_id"),
        Index("ix_pal_operation", "operation"),
        Index("ix_pal_created",   "created_at"),
        Index("ix_pal_entity",    "entity_type", "entity_id"),
    )
    tenant_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:   Mapped[str|None]       = mapped_column(String(30), nullable=True)
    actor_ip:     Mapped[str|None]       = mapped_column(String(50), nullable=True)
    operation:    Mapped[str]            = mapped_column(String(100), nullable=False)
    engine_id:    Mapped[str]            = mapped_column(String(50), nullable=False)
    entity_type:  Mapped[str|None]       = mapped_column(String(50), nullable=True)
    entity_id:    Mapped[str|None]       = mapped_column(String(100), nullable=True)
    before_state: Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    after_state:  Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    request_id:   Mapped[str|None]       = mapped_column(String(100), nullable=True)
    is_high_risk: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    meta:         Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)


class SessionInventory(ServiceOSBase):
    """Active session tracking. Redis is primary — DB is the audit record.
    Force-logout deletes Redis key immediately, then marks DB row inactive."""
    __tablename__ = "session_inventory"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_si_session_id"),
        Index("ix_si_user",   "user_id"),
        Index("ix_si_tenant", "tenant_id"),
        Index("ix_si_active", "is_active"),
    )
    user_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    session_id:   Mapped[str]            = mapped_column(String(100), nullable=False, unique=True)
    device_info:  Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    ip_address:   Mapped[str|None]       = mapped_column(String(50), nullable=True)
    user_agent:   Mapped[str|None]       = mapped_column(String(500), nullable=True)
    is_active:    Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    revoke_reason:Mapped[str|None]       = mapped_column(String(200), nullable=True)


# ── SOC Enterprise Upgrade (migration 083) ─────────────────────────────────────

class IPBlockHit(ServiceOSBase):
    """APPEND-ONLY. One row per request rejected by an active IP block."""
    __tablename__ = "ip_block_hits"
    __table_args__ = (
        Index("ix_ibh_block_id", "block_id"),
        Index("ix_ibh_hit_at",   "hit_at"),
    )
    block_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    ip_or_cidr:   Mapped[str]            = mapped_column(String(50), nullable=False)
    hit_at:       Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    path:         Mapped[str|None]       = mapped_column(String(500), nullable=True)
    method:       Mapped[str|None]       = mapped_column(String(10), nullable=True)
    user_agent:   Mapped[str|None]       = mapped_column(String(500), nullable=True)
    blocked_scope:Mapped[str|None]       = mapped_column(String(30), nullable=True)


class ApiKeyUsageLog(ServiceOSBase):
    """APPEND-ONLY. One row per authenticated request made with a tenant API key."""
    __tablename__ = "api_key_usage_logs"
    __table_args__ = (
        Index("ix_akul_api_key_id", "api_key_id"),
        Index("ix_akul_used_at",    "used_at"),
    )
    api_key_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    used_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    endpoint:     Mapped[str|None]       = mapped_column(String(500), nullable=True)
    method:       Mapped[str|None]       = mapped_column(String(10), nullable=True)
    status_code:  Mapped[int|None]       = mapped_column(Integer, nullable=True)
    ip_address:   Mapped[str|None]       = mapped_column(String(50), nullable=True)
    response_ms:  Mapped[int|None]       = mapped_column(Integer, nullable=True)


class SecurityPolicy(ServiceOSBase):
    """One row per configurable security policy. Changes require reason + are audited."""
    __tablename__ = "security_policies"
    __table_args__ = (
        UniqueConstraint("policy_key", name="uq_secpol_key"),
    )
    policy_key:        Mapped[str]            = mapped_column(String(80), nullable=False, unique=True)
    policy_value_json: Mapped[dict]           = mapped_column(JSONB, nullable=False)
    description:       Mapped[str|None]       = mapped_column(String(500), nullable=True)
    updated_by_user_id:Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_reason:     Mapped[str|None]      = mapped_column(String(500), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "policy_key": self.policy_key,
            "policy_value": self.policy_value_json, "description": self.description,
            "updated_by_user_id": str(self.updated_by_user_id) if self.updated_by_user_id else None,
            "updated_reason": self.updated_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
