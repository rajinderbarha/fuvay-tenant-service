"""Auth Engine — Complete Pydantic v2 Schemas (all 37 endpoint schemas). v2."""
import uuid
from datetime import datetime
from typing import Any, Literal

import re as _re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

_EMAIL_RE = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", _re.IGNORECASE)


# ── Registration ──────────────────────────────────────────────────────────────
class RegisterCustomerRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(pattern=r"^\+?[1-9]\d{7,14}$")
    email: EmailStr | None = None
    # Stable installation/browser identifier used as an additional abuse-control
    # dimension. Optional so existing clients continue to work.
    device_id: str | None = Field(default=None, max_length=255)


# ── Login ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    # str (not EmailStr) so .local / .test / .dev domains are accepted in dev/staging
    email: str
    password: str
    device_id: str = Field(default="web", max_length=255)
    device_name: str | None = Field(None, max_length=255)
    user_agent: str | None = None

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            # Signup stores E.164; accept the same Indian local formats here.
            digits = _re.sub(r"[\s()-]", "", v)
            if _re.fullmatch(r"\d{10}", digits):
                v = "+91" + digits
            elif _re.fullmatch(r"0\d{10}", digits):
                v = "+91" + digits[1:]
            elif _re.fullmatch(r"91\d{10}", digits):
                v = "+" + digits
            else:
                v = digits
        if not (_EMAIL_RE.match(v) or _re.match(r"^\+?[1-9]\d{7,14}$", v)):
            raise ValueError("Invalid email address or mobile number")
        return v

class PhoneLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^\+?[1-9]\d{7,14}$")
    device_id: str = Field(default="mobile", max_length=255)
    device_name: str | None = None

class OTPVerifyRequest(BaseModel):
    # Either channel. `phone` was required, so the emailed code this endpoint's sibling
    # now sends had no way to be redeemed.
    phone: str | None = None
    email: EmailStr | None = None
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    device_id: str = Field(default="mobile")
    device_name: str | None = None

    @model_validator(mode="after")
    def phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError("Either phone or email is required.")
        return self

class OTPSendRequest(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    # `email_login` is what an emailed sign-in code is stored under; the purpose is
    # ignored for the email branch, which always uses it.
    purpose: Literal["phone_login", "phone_verification", "password_reset",
                     "job_approval", "email_login"] = "phone_login"
    # A stable installation/browser identifier adds a third throttle dimension.
    # Optional for backward compatibility; recipient and IP limits always apply.
    device_id: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError("Either phone or email is required.")
        return self


# ── MFA ───────────────────────────────────────────────────────────────────────
class MFAVerifyRequest(BaseModel):
    mfa_challenge_token: str
    code: str = Field(min_length=6, max_length=8)
    device_id: str = Field(default="web", max_length=255)
    device_name: str | None = Field(default=None, max_length=255)
    remember_device: bool = False

class MFASetupConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

class MFADisableRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=8, description="TOTP code or backup code")


# ── Token ─────────────────────────────────────────────────────────────────────
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenIntrospectRequest(BaseModel):
    token: str


# ── Password ──────────────────────────────────────────────────────────────────
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        return self

class PasswordResetRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError("Either phone or email is required.")
        return self

class PasswordResetConfirmRequest(BaseModel):
    # Added (Account Security phase): confirm_password_reset previously had
    # no way to identify which account's password to reset -- OTPRecord is
    # keyed by a one-way recipient_hash, not a reversible user id, so the
    # same identifier used to request the OTP must be supplied again here.
    email: EmailStr | None = None
    phone: str | None = None
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self

    @model_validator(mode="after")
    def phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError("Either phone or email is required.")
        return self


class ChangePasswordRequiredRequest(BaseModel):
    """For force-change flow. Accepts current (possibly temp) password + new password."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("PASSWORD_CONFIRMATION_MISMATCH: Passwords do not match.")
        return self


# ── Phase 0E: Account security actions ───────────────────────────────────────
class LockAccountRequest(BaseModel):
    reason: str = Field(default="Security review", min_length=3, max_length=500)
    locked_until: datetime | None = Field(
        default=None,
        description="Optional lock expiry. If omitted lock is permanent until unlocked.",
    )
    revoke_sessions: bool = True


class UnlockAccountRequest(BaseModel):
    reason: str = Field(default="Issue resolved", min_length=3, max_length=500)


class DeactivateUserRequest(BaseModel):
    reason: str = Field(default="Account deactivated by admin", min_length=3, max_length=500)
    revoke_sessions: bool = True


class ReactivateUserRequest(BaseModel):
    reason: str = Field(default="Account reactivated by admin", min_length=3, max_length=500)


class AdminRevokeAllSessionsRequest(BaseModel):
    reason: str = Field(default="Security reset", min_length=3, max_length=500)


# ── Admin security actions ────────────────────────────────────────────────────
class AdminForcePasswordChangeRequest(BaseModel):
    reason: str = Field(default="Security review", min_length=3, max_length=500)
    revoke_sessions: bool = True


class AdminSendPasswordResetRequest(BaseModel):
    reason: str = Field(default="Admin-initiated password reset", min_length=3, max_length=500)
    revoke_sessions: bool = False


class AdminGenerateTemporaryPasswordRequest(BaseModel):
    reason: str = Field(default="Manual onboarding", min_length=3, max_length=500)
    revoke_sessions: bool = True


# ── P0 Platform Users ─────────────────────────────────────────────────────────
class SuspendUserRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    revoke_sessions: bool = True


class UnsuspendUserRequest(BaseModel):
    reason: str = Field(default="Suspension lifted by admin", min_length=3, max_length=500)


class RequireMfaRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ResetMfaRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RevokeSessionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ChangeRoleRequest(BaseModel):
    platform_role: str
    reason: str = Field(min_length=3, max_length=500)


class ChangeAccessScopeRequest(BaseModel):
    access_scope: str
    reason: str = Field(min_length=3, max_length=500)


class InvitePlatformUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: str
    phone: str | None = None
    platform_role: str
    access_scope: str
    require_mfa: bool = True
    invite_expiry_days: int = Field(default=7, ge=1, le=30)


class RevokeInviteRequest(BaseModel):
    reason: str = Field(default="Invite revoked by admin", min_length=3, max_length=500)


class BulkPlatformActionRequest(BaseModel):
    action: str
    user_ids: list[uuid.UUID]
    reason: str = Field(min_length=3, max_length=500)


# ── Sessions ──────────────────────────────────────────────────────────────────
class ApproveDeviceRequest(BaseModel):
    session_id: uuid.UUID


# ── Staff ─────────────────────────────────────────────────────────────────────
class InviteStaffRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{7,14}$")
    permissions: list[str] = Field(default_factory=list)
    role: Literal["staff"] = "staff"

class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self

class UpdatePermissionsRequest(BaseModel):
    permissions: dict[str, bool] = Field(
        description="Map of permission_key → granted. True=grant, False=revoke.",
        example={"field_ops:jobs:assign": True, "analytics:advanced:read": False}
    )


class UpdateScheduleRequest(BaseModel):
    working_hours: dict[str, dict] = Field(
        description="Map of day → {start, end, is_working}.",
        example={"monday": {"start": "09:00", "end": "18:00", "is_working": True}}
    )


# ── Impersonation ─────────────────────────────────────────────────────────────
class ImpersonateRequest(BaseModel):
    target_user_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=500)


# ── API Keys ──────────────────────────────────────────────────────────────────
class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    scopes: list[str] = Field(min_length=1, description="List of permission strings")
    is_test_mode: bool = False
    expires_days: int | None = Field(None, ge=1, le=365)

class UpdateApiKeyRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    scopes: list[str] | None = None


# ── Profile ───────────────────────────────────────────────────────────────────
class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{7,14}$")
    avatar_url: str | None = None


# ── Responses ─────────────────────────────────────────────────────────────────
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800

class UserProfile(BaseModel):
    user_id: str
    email: str
    phone: str | None
    full_name: str
    role: str
    tenant_id: str | None
    is_verified: bool
    is_mfa_enabled: bool
    onboarding_complete: bool
    force_password_change: bool
    avatar_url: str | None
    last_login_at: str | None
    created_at: str
    permissions: list[str] | None = None

class LoginResponse(BaseModel):
    tokens: TokenPair | None = None
    user: UserProfile | None = None
    mfa_required: bool = False
    mfa_challenge_token: str | None = None
    force_password_change: bool = False
    device_approval_required: bool = False
    tenant_context: dict | None = None

class MFASetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list[str]
    backup_codes_remaining: int
    message: str = "Scan the QR code in your authenticator app, then confirm with a code."

class SessionInfo(BaseModel):
    session_id: str
    device_name: str
    device_type: str
    ip_address: str | None
    last_active_at: str
    is_current: bool
    is_trusted: bool
    is_approved: bool
    created_at: str

class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    key_prefix: str
    full_key: str | None = None
    scopes: list[str]
    is_test_mode: bool
    calls_today: int
    calls_total: int
    last_used_at: str | None
    expires_at: str | None
    created_at: str

class ImpersonationResponse(BaseModel):
    impersonation_session_id: str
    access_token: str
    target_user: UserProfile
    expires_at: str
    warning: str = "All actions during impersonation are fully logged. Non-refreshable token expires in 60 minutes."

class TokenIntrospectResponse(BaseModel):
    active: bool
    user_id: str | None = None
    email: str | None = None
    role: str | None = None
    tenant_id: str | None = None
    expires_at: str | None = None
    jti: str | None = None
    is_impersonation: bool = False

class StaffInviteResponse(BaseModel):
    invite_id: str
    email: str
    expires_at: str
    message: str
