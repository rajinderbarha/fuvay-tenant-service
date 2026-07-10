"""Settings Engine — Models (4 tables)."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class PlatformSetting(ServiceOSBase):
    """Global defaults set by super admin. Fallback when no plan/tenant override."""
    __tablename__ = "platform_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_ps_key"),)

    key:          Mapped[str]          = mapped_column(String(200), nullable=False, unique=True)
    value:        Mapped[dict]         = mapped_column(JSONB, nullable=False)
    setting_type: Mapped[str]          = mapped_column(String(20), nullable=False)
    description:  Mapped[str|None]     = mapped_column(Text, nullable=True)
    is_public:    Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    set_by:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Settings Enterprise Upgrade (migration 088)
    label:                Mapped[str|None]  = mapped_column(String(200), nullable=True)
    category:              Mapped[str]       = mapped_column(String(60), default="general_platform", nullable=False)
    allowed_values_json:   Mapped[list|None] = mapped_column(JSONB, nullable=True)
    is_secret:             Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    risk_level:            Mapped[str]       = mapped_column(String(20), default="low", nullable=False)
    requires_approval:     Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    requires_restart:      Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    is_runtime_editable:   Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    owner_module:          Mapped[str|None]  = mapped_column(String(60), nullable=True)
    status:                Mapped[str]       = mapped_column(String(20), default="active", nullable=False)


class PlanSetting(ServiceOSBase):
    """Per-plan-type overrides. Overrides platform defaults for a plan."""
    __tablename__ = "plan_settings"
    __table_args__ = (UniqueConstraint("plan_type","key", name="uq_plan_setting"),
                      Index("ix_plan_setting_key","plan_type","key"))

    plan_type:    Mapped[str]          = mapped_column(String(30), nullable=False)
    key:          Mapped[str]          = mapped_column(String(200), nullable=False)
    value:        Mapped[dict]         = mapped_column(JSONB, nullable=False)
    setting_type: Mapped[str]          = mapped_column(String(20), nullable=False)
    set_by:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class TenantSetting(ServiceOSBase):
    """Tenant-level overrides. Highest priority in resolution chain."""
    __tablename__ = "tenant_settings"
    __table_args__ = (UniqueConstraint("tenant_id","key", name="uq_tenant_setting"),
                      Index("ix_tenant_setting_key","tenant_id","key"))

    tenant_id:    Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    key:          Mapped[str]          = mapped_column(String(200), nullable=False)
    value:        Mapped[dict]         = mapped_column(JSONB, nullable=False)
    setting_type: Mapped[str]          = mapped_column(String(20), nullable=False)
    set_by:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason:       Mapped[str|None]     = mapped_column(String(500), nullable=True)
    # Settings Enterprise Upgrade (migration 088)
    expires_at:         Mapped["datetime|None"] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_approval:  Mapped[bool]            = mapped_column(Boolean, default=False, nullable=False)
    status:             Mapped[str]             = mapped_column(String(20), default="active", nullable=False)


class SettingAuditLog(ServiceOSBase):
    """Append-only audit trail for every setting change."""
    __tablename__ = "setting_audit_logs"
    __table_args__ = (Index("ix_sal_tenant_key","tenant_id","key"),)

    tenant_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tier:         Mapped[str]            = mapped_column(String(20), nullable=False)
    key:          Mapped[str]            = mapped_column(String(200), nullable=False)
    old_value:    Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    new_value:    Mapped[dict]           = mapped_column(JSONB, nullable=False)
    changed_by:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason:       Mapped[str|None]       = mapped_column(String(500), nullable=True)
    # Settings Enterprise Upgrade (migration 088)
    request_id:   Mapped[str|None]       = mapped_column(String(100), nullable=True)
    risk_level:   Mapped[str]            = mapped_column(String(20), default="low", nullable=False)
    action_type:  Mapped[str]            = mapped_column(String(30), default="updated", nullable=False)


class FeatureFlag(ServiceOSBase):
    """Platform-wide feature flag with rollout controls (Settings Enterprise Upgrade)."""
    __tablename__ = "feature_flags"
    __table_args__ = (UniqueConstraint("flag_key", name="uq_ff_flag_key"),)

    flag_key:        Mapped[str]            = mapped_column(String(120), nullable=False, unique=True)
    label:           Mapped[str]            = mapped_column(String(200), nullable=False)
    description:     Mapped[str|None]       = mapped_column(Text, nullable=True)
    status:          Mapped[str]            = mapped_column(String(20), default="disabled", nullable=False)
    rollout_type:    Mapped[str]            = mapped_column(String(30), default="global", nullable=False)
    rollout_percent: Mapped[int|None]       = mapped_column(nullable=True)
    category_scope:  Mapped[str|None]       = mapped_column(String(60), nullable=True)
    tenant_scope:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    start_date:      Mapped["datetime|None"] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date:        Mapped["datetime|None"] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_module:    Mapped[str|None]       = mapped_column(String(60), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "flag_key": self.flag_key, "label": self.label,
            "description": self.description, "status": self.status,
            "rollout_type": self.rollout_type, "rollout_percent": self.rollout_percent,
            "category_scope": self.category_scope,
            "tenant_scope": str(self.tenant_scope) if self.tenant_scope else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "owner_module": self.owner_module,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
