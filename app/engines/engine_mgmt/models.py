"""Enterprise Engine Management models — migration 081."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, Integer, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class PlatformEngine(Base):
    __tablename__ = "platform_engines"
    __table_args__ = (
        Index("ix_pe_engine_key", "engine_key"),
        Index("ix_pe_engine_type", "engine_type"),
        Index("ix_pe_global_status", "global_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    engine_type: Mapped[str] = mapped_column(String(30), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="active")
    global_status: Mapped[str] = mapped_column(String(30), default="enabled")
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_customer_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tenant_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    owner_team: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "engine_key": self.engine_key,
            "display_name": self.display_name,
            "description": self.description,
            "engine_type": self.engine_type,
            "lifecycle_status": self.lifecycle_status,
            "global_status": self.global_status,
            "is_core": self.is_core,
            "is_locked": self.is_locked,
            "is_customer_visible": self.is_customer_visible,
            "is_tenant_visible": self.is_tenant_visible,
            "version": self.version,
            "owner_team": self.owner_team,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EngineDependency(Base):
    __tablename__ = "engine_dependencies"
    __table_args__ = (
        UniqueConstraint("engine_id", "depends_on_engine_id", name="uq_engine_dep"),
        Index("ix_edep_engine_id", "engine_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    depends_on_engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    depends_on_engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(20), default="required")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "engine_key": self.engine_key,
            "depends_on_engine_key": self.depends_on_engine_key,
            "dependency_type": self.dependency_type,
            "status": self.status,
        }


class CategoryEngineMatrix(Base):
    __tablename__ = "category_engine_matrix"
    __table_args__ = (
        UniqueConstraint("category_id", "engine_id", name="uq_cat_engine"),
        Index("ix_cem_category", "category_id"),
        Index("ix_cem_engine", "engine_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # recommendation_status: required | optional | not_recommended | not_applicable
    recommendation_status: Mapped[str] = mapped_column(String(30), default="not_applicable")
    # dependency_status: met | missing | not_checked
    dependency_status: Mapped[str] = mapped_column(String(20), default="not_checked")
    # runtime_risk: low | medium | high | blocked
    runtime_risk: Mapped[str] = mapped_column(String(20), default="low")
    # status: active | inactive
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "category_id": str(self.category_id),
            "engine_key": self.engine_key,
            "is_enabled": self.is_enabled,
            "is_required": self.is_required,
            "recommendation_status": self.recommendation_status,
            "dependency_status": self.dependency_status,
            "runtime_risk": self.runtime_risk,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PackageEngineEntitlement(Base):
    __tablename__ = "package_engine_entitlements"
    __table_args__ = (
        UniqueConstraint("package_id", "engine_id", name="uq_pkg_engine"),
        Index("ix_pee_package", "package_id"),
        Index("ix_pee_engine", "engine_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    is_included: Mapped[bool] = mapped_column(Boolean, default=True)
    limits_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    feature_flags_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    added_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "package_id": str(self.package_id),
            "engine_key": self.engine_key,
            "is_included": self.is_included,
            "status": self.status,
            "limits": self.limits_json,
            "feature_flags": self.feature_flags_json,
        }


class TenantEngineOverride(Base):
    __tablename__ = "tenant_engine_overrides"
    __table_args__ = (
        Index("ix_teo_tenant", "tenant_id"),
        Index("ix_teo_engine", "engine_id"),
        Index("ix_teo_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    override_type: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), default="active")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "engine_key": self.engine_key,
            "override_type": self.override_type,
            "effective_status": self.effective_status,
            "reason": self.reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EngineHealthCheck(Base):
    __tablename__ = "engine_health_checks"
    __table_args__ = (
        Index("ix_ehc_engine_id", "engine_id"),
        Index("ix_ehc_checked_at", "checked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    check_type: Mapped[str] = mapped_column(String(40), default="manual")
    result_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "engine_key": self.engine_key,
            "health_status": self.health_status,
            "check_type": self.check_type,
            "result": self.result_json,
            "error_message": self.error_message,
            "response_ms": self.response_ms,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


class EnginePermission(Base):
    __tablename__ = "engine_permissions"
    __table_args__ = (
        Index("ix_eperm_engine", "engine_id"),
        Index("ix_eperm_key", "permission_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key: Mapped[str] = mapped_column(String(80), nullable=False)
    permission_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(30), default="platform_admin")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_mfa: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "engine_key": self.engine_key,
            "permission_key": self.permission_key,
            "label": self.label,
            "description": self.description,
            "scope": self.scope,
            "is_sensitive": self.is_sensitive,
            "requires_mfa": self.requires_mfa,
            "status": self.status,
        }


class EngineAuditLog(Base):
    __tablename__ = "engine_audit_logs"
    __table_args__ = (
        Index("ix_eal_engine_id", "engine_id"),
        Index("ix_eal_action", "action_type"),
        Index("ix_eal_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    engine_key: Mapped[str | None] = mapped_column(String(80))
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), default="global")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_role: Mapped[str | None] = mapped_column(String(40))
    old_value_json: Mapped[dict | None] = mapped_column(JSONB)
    new_value_json: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "engine_key": self.engine_key,
            "action_type": self.action_type,
            "scope_type": self.scope_type,
            "scope_id": str(self.scope_id) if self.scope_id else None,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "actor_role": self.actor_role,
            "old_value": self.old_value_json,
            "new_value": self.new_value_json,
            "reason": self.reason,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
