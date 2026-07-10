"""Auth Engine — SQLAlchemy Models (fixed: no reserved attribute names)."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class User(ServiceOSBase):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_role", "role"),
        Index("ix_users_phone", "phone"),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    force_password_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_photo_media_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")
    timezone: Mapped[str] = mapped_column(String(60), nullable=False, server_default="UTC")
    password_reset_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    temporary_password_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_password_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_password_reset_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Phase 0E — Account Security
    account_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    lock_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deactivation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_failed_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Platform Users Governance (migration 083)
    platform_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    access_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class UserSession(ServiceOSBase):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_tenant_id", "tenant_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LoginEvent(ServiceOSBase):
    """Login history — one row per auth event (success, failure, logout, refresh, revoke)."""
    __tablename__ = "login_events"
    __table_args__ = (
        Index("ix_login_events_user_id", "user_id"),
        Index("ix_login_events_email_attempted", "email_attempted"),
        Index("ix_login_events_created_at", "created_at"),
        Index("ix_login_events_event_type", "event_type"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    email_attempted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class RefreshTokenFamily(ServiceOSBase):
    __tablename__ = "refresh_token_families"
    __table_args__ = (Index("ix_rtf_user_id", "user_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_invalidated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def invalidate(self, reason: str = "theft_detected") -> None:
        self.is_invalidated = True
        self.invalidated_at = utcnow()
        self.invalidation_reason = reason


class RefreshToken(ServiceOSBase):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_family_id", "family_id"),
        Index("ix_refresh_tokens_jti", "jti"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    jti: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_token: Mapped[str] = mapped_column(String(255), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MFASecret(ServiceOSBase):
    __tablename__ = "mfa_secrets"
    __table_args__ = (UniqueConstraint("user_id", name="uq_mfa_user"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    encrypted_secret: Mapped[str] = mapped_column(String(500), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MFABackupCode(ServiceOSBase):
    __tablename__ = "mfa_backup_codes"
    __table_args__ = (Index("ix_mfa_backup_user_id", "user_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    hashed_code: Mapped[str] = mapped_column(String(255), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StaffPermission(ServiceOSBase):
    __tablename__ = "staff_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_key", name="uq_staff_permission"),
        Index("ix_staff_perms_user_id", "user_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    permission_key: Mapped[str] = mapped_column(String(100), nullable=False)
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ApiKey(ServiceOSBase):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_tenant_id", "tenant_id"),
        Index("ix_api_keys_key_prefix", "key_prefix"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_test_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calls_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calls_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class PasswordResetToken(ServiceOSBase):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_prt_user_id", "user_id"),
        Index("ix_prt_token_hash", "token_hash"),
        Index("ix_prt_status", "status"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    used_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)


class OTPRecord(ServiceOSBase):
    __tablename__ = "otp_records"
    __table_args__ = (Index("ix_otp_records_recipient", "recipient_hash"),)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_otp: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthAuditLog(ServiceOSBase):
    __tablename__ = "auth_audit_logs"
    __table_args__ = (
        Index("ix_auth_audit_actor_id", "actor_id"),
        Index("ix_auth_audit_tenant_id", "tenant_id"),
        Index("ix_auth_audit_action", "action_type"),
        Index("ix_auth_audit_created_at", "created_at"),
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
