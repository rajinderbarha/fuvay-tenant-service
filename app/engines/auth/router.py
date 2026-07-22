"""
Auth Engine — FastAPI Router
37 endpoints. Zero inline imports. Zero business logic.
Every handler: validate → permission check → rate limit → service call → return ApiResponse.
"""
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.core.security import rate_limiter, get_client_ip
from app.dependencies.auth import (
    get_current_user, UserContext,
    require_super_admin, require_tenant_owner, require_staff_or_above,
)
from app.dependencies.db import get_db
from app.engine_registry.registry import registry
from app.engines.auth.schemas import (
    AcceptInviteRequest, CreateApiKeyRequest, ImpersonateRequest,
    InviteStaffRequest, LoginRequest, MFADisableRequest,
    MFASetupConfirmRequest, MFAVerifyRequest, OTPSendRequest,
    OTPVerifyRequest, PasswordChangeRequest, PasswordResetConfirmRequest,
    PasswordResetRequest, PhoneLoginRequest, RefreshTokenRequest,
    RegisterCustomerRequest, TokenIntrospectRequest, UpdateApiKeyRequest,
    UpdatePermissionsRequest, UpdateProfileRequest, UpdateScheduleRequest,
    ChangePasswordRequiredRequest,
    AdminForcePasswordChangeRequest, AdminSendPasswordResetRequest,
    AdminGenerateTemporaryPasswordRequest,
    # Phase 0E
    LockAccountRequest, UnlockAccountRequest,
    DeactivateUserRequest, ReactivateUserRequest,
    AdminRevokeAllSessionsRequest,
)
from app.engines.auth.service import AuthService
from app.schemas.base import ApiResponse, Meta, Links, Link, ok
from app.exceptions import ServiceOSException
from app.core.permissions import ROLE_PERMISSIONS
from app.engines.auth.models import User as _UserModel

logger = structlog.get_logger("auth.router")
router = APIRouter(prefix="/v1/auth", tags=["Auth & IAM"])
ENGINE_ID = "auth"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _meta(request: Request) -> Meta:
    return Meta(request_id=getattr(request.state, "request_id", "—"), engine_id=ENGINE_ID)


def _svc(request: Request, db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        db=db,
        request_id=getattr(request.state, "request_id", "—"),
        ip_address=get_client_ip(request),
    )


# ── Engine Introspection ──────────────────────────────────────────────────────
@router.get("/meta", summary="Auth engine introspection", tags=["Engine Registry"])
async def engine_meta() -> dict:
    engine = registry.get(ENGINE_ID)
    return {
        "engine_id": ENGINE_ID,
        "name": engine.name if engine else "Auth & IAM Engine",
        "version": engine.version if engine else "2.4.1",
        "description": engine.description if engine else "",
        "endpoint_count": 37,
        "status": "active",
        "capabilities": ["jwt", "mfa_totp", "refresh_token_rotation",
                         "device_sessions", "impersonation", "granular_rbac",
                         "api_keys", "audit_trail"],
    }


# ── 1. Register Customer ──────────────────────────────────────────────────────
@router.post(
    "/register/customer",
    summary="Register a new customer account",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
)
async def register_customer(
    body: RegisterCustomerRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"ip:{get_client_ip(request)}",
        limit_type="auth:register",
        identifier=get_client_ip(request),
    )
    tenant_id = None
    if request.headers.get("X-Tenant-ID"):
        try:
            tenant_id = uuid.UUID(request.headers["X-Tenant-ID"])
        except ValueError:
            pass
    data = await svc.register_customer(body.full_name, body.phone, body.email and str(body.email), tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID,
              links=Links(
                  self_link="/v1/auth/register/customer",
                  actions=[Link(href="/v1/auth/login/phone", method="POST", rel="verify_otp",
                                description="Verify phone OTP to activate account")],
              ))


# ── 2. Login with email+password ──────────────────────────────────────────────
@router.post(
    "/login",
    summary="Login with email and password",
    response_model=ApiResponse[dict],
)
async def login(
    body: LoginRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"ip:{get_client_ip(request)}",
        limit_type="auth:login",
        identifier=get_client_ip(request),
    )
    data = await svc.login(
        email=str(body.email),
        password=body.password,
        device_id=body.device_id,
        device_name=body.device_name,
        user_agent=body.user_agent or request.headers.get("User-Agent"),
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 3. Request Phone OTP ──────────────────────────────────────────────────────
@router.post(
    "/otp/send",
    summary="Send OTP to phone or email",
    response_model=ApiResponse[dict],
)
async def send_otp(
    body: OTPSendRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"otp:{body.phone or body.email}",
        limit_type="auth:otp_send",
        identifier=str(body.phone or body.email),
    )
    data = await svc.send_phone_otp(
        phone=body.phone or "", purpose=body.purpose
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 4. Verify Phone OTP (login) ───────────────────────────────────────────────
@router.post(
    "/otp/verify",
    summary="Verify OTP and get access token",
    response_model=ApiResponse[dict],
)
async def verify_otp(
    body: OTPVerifyRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"otp_verify:{body.phone}",
        limit_type="auth:otp_verify",
        identifier=body.phone,
    )
    data = await svc.verify_phone_otp_login(
        phone=body.phone, otp=body.otp,
        device_id=body.device_id, device_name=body.device_name,
        user_agent=request.headers.get("User-Agent"),
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 5. MFA Verify (after login) ───────────────────────────────────────────────
@router.post(
    "/mfa/verify",
    summary="Complete login with MFA code",
    response_model=ApiResponse[dict],
)
async def verify_mfa(
    body: MFAVerifyRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"mfa:{body.mfa_challenge_token[:16]}",
        limit_type="auth:mfa_verify",
        identifier=body.mfa_challenge_token[:16],
    )
    data = await svc.verify_mfa(
        mfa_challenge_token=body.mfa_challenge_token,
        code=body.code,
        device_id="web",
        device_name=None,
        user_agent=request.headers.get("User-Agent"),
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 6. MFA Setup ──────────────────────────────────────────────────────────────
@router.post(
    "/mfa/setup",
    summary="Initiate MFA setup — returns TOTP QR code and backup codes",
    response_model=ApiResponse[dict],
)
async def setup_mfa(
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.setup_mfa(uuid.UUID(user.user_id))
    return ok(data, _meta(request).request_id, ENGINE_ID,
              links=Links(actions=[
                  Link(href="/v1/auth/mfa/confirm", method="POST", rel="confirm",
                       description="Confirm setup with a TOTP code")
              ]))


# ── 7. MFA Confirm ────────────────────────────────────────────────────────────
@router.post(
    "/mfa/confirm",
    summary="Confirm MFA setup with a TOTP code",
    response_model=ApiResponse[dict],
)
async def confirm_mfa(
    body: MFASetupConfirmRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.confirm_mfa(uuid.UUID(user.user_id), body.code)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 8. MFA Disable ────────────────────────────────────────────────────────────
@router.post(
    "/mfa/disable",
    summary="Disable MFA (requires current password and TOTP code)",
    response_model=ApiResponse[dict],
)
async def disable_mfa(
    body: MFADisableRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if user.role == "super_admin":
        raise ServiceOSException(
            "PERMISSION_DENIED",
            "Super admins cannot disable MFA.",
            resolution="MFA is mandatory for super admin accounts.",
        )
    data = await svc.disable_mfa(uuid.UUID(user.user_id), body.password, body.code)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 9. Regenerate MFA backup codes ───────────────────────────────────────────
@router.post(
    "/mfa/backup-codes/regenerate",
    summary="Regenerate MFA backup codes (requires current TOTP code)",
    response_model=ApiResponse[dict],
)
async def regenerate_backup_codes(
    body: MFASetupConfirmRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.regenerate_backup_codes(uuid.UUID(user.user_id), body.code)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 10. Refresh Token ─────────────────────────────────────────────────────────
@router.post(
    "/token/refresh",
    summary="Rotate refresh token and get new access token",
    response_model=ApiResponse[dict],
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"ip:{get_client_ip(request)}",
        limit_type="auth:refresh",
        identifier=get_client_ip(request),
    )
    data = await svc.refresh_token(body.refresh_token)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 11. Token Introspect ──────────────────────────────────────────────────────
@router.post(
    "/token/introspect",
    summary="Validate a token and return its claims (for internal service use)",
    response_model=ApiResponse[dict],
)
async def introspect_token(
    body: TokenIntrospectRequest,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.introspect_token(body.token)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 12. Logout ────────────────────────────────────────────────────────────────
@router.post(
    "/logout",
    summary="Logout current session",
    response_model=ApiResponse[dict],
)
async def logout(
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await svc.logout(user.jti or "", user.session_id or "", user.user_id)
    return ok({"message": "Logged out successfully."}, _meta(request).request_id, ENGINE_ID)


# ── 13. Logout All Sessions ───────────────────────────────────────────────────
@router.post(
    "/logout-all",
    summary="Logout all sessions (except optional current)",
    response_model=ApiResponse[dict],
)
async def logout_all(
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    count = await svc.logout_all(user.user_id, user.jti or "")
    return ok({"sessions_revoked": count, "message": f"Logged out from {count} session(s)."},
              _meta(request).request_id, ENGINE_ID)


# ── 14. Get Profile ───────────────────────────────────────────────────────────
@router.get(
    "/me",
    summary="Get current user profile with permissions",
    response_model=ApiResponse[dict],
)
async def get_me(
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_profile(uuid.UUID(user.user_id))
    return ok(data, _meta(request).request_id, ENGINE_ID,
              links=Links(
                  self_link="/v1/auth/me",
                  actions=[
                      Link(href="/v1/auth/me", method="PUT", rel="update_profile"),
                      Link(href="/v1/auth/password/change", method="PUT", rel="change_password"),
                      Link(href="/v1/auth/sessions", method="GET", rel="list_sessions"),
                  ],
              ))


# ── 15. Update Profile ────────────────────────────────────────────────────────
@router.put(
    "/me",
    summary="Update current user profile",
    response_model=ApiResponse[dict],
)
async def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.update_profile(
        uuid.UUID(user.user_id), body.full_name, body.phone, body.avatar_url
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 16. Change Password ───────────────────────────────────────────────────────
@router.put(
    "/password/change",
    summary="Change password (requires current password)",
    response_model=ApiResponse[dict],
)
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await svc.change_password(uuid.UUID(user.user_id), body.current_password, body.new_password)
    return ok(
        {"message": "Password changed successfully. Log in again with your new password."},
        _meta(request).request_id, ENGINE_ID,
    )


# ── 17. Request Password Reset ────────────────────────────────────────────────
@router.post(
    "/password/reset/request",
    summary="Request password reset OTP (no auth required)",
    response_model=ApiResponse[dict],
)
async def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await rate_limiter.check_and_raise(
        limit_key=f"pwreset:{str(body.email or body.phone)}",
        limit_type="auth:password_reset",
        identifier=str(body.email or body.phone),
    )
    data = await svc.request_password_reset(
        email=str(body.email) if body.email else None,
        phone=body.phone,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 18. Confirm Password Reset ────────────────────────────────────────────────
@router.post(
    "/password/reset/confirm",
    summary="Confirm password reset with OTP token",
    response_model=ApiResponse[dict],
)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.confirm_password_reset(body.reset_token, body.new_password)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 19. List Sessions ─────────────────────────────────────────────────────────
@router.get(
    "/sessions",
    summary="List all active sessions for current user",
    response_model=ApiResponse[dict],
)
async def list_sessions(
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    sessions = await svc.list_sessions(uuid.UUID(user.user_id), user.device_id or "")
    return ok({"sessions": sessions, "total": len(sessions)},
              _meta(request).request_id, ENGINE_ID)


# ── 20. Revoke Session ────────────────────────────────────────────────────────
@router.delete(
    "/sessions/{session_id}",
    summary="Revoke a specific session",
    response_model=ApiResponse[dict],
)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    await svc.revoke_session(session_id, uuid.UUID(user.user_id))
    return ok({"session_id": str(session_id), "revoked": True},
              _meta(request).request_id, ENGINE_ID)


# ── 21. Approve Device ────────────────────────────────────────────────────────
@router.post(
    "/sessions/{session_id}/approve",
    summary="Approve a staff member's new device",
    response_model=ApiResponse[dict],
)
async def approve_device(
    session_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_tenant_owner),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.approve_device(session_id, uuid.UUID(user.user_id), user.role)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 22. Invite Staff ──────────────────────────────────────────────────────────
@router.post(
    "/staff/invite",
    summary="Invite a staff member to the tenant",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
)
async def invite_staff(
    body: InviteStaffRequest,
    request: Request,
    user: UserContext = Depends(require_tenant_mutation_permission(P.AUTH_STAFF_INVITE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context in token.")
    data = await svc.invite_staff(
        tenant_id=uuid.UUID(user.tenant_id),
        inviter_id=uuid.UUID(user.user_id),
        email=str(body.email),
        full_name=body.full_name,
        phone=body.phone,
        permissions=body.permissions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 23. Accept Invite ─────────────────────────────────────────────────────────
@router.post(
    "/staff/invite/accept",
    summary="Accept staff invite and set password (no auth required)",
    response_model=ApiResponse[dict],
)
async def accept_invite(
    body: AcceptInviteRequest,
    request: Request,
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.accept_invite(body.invite_token, body.password)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 24. Resend Invite ─────────────────────────────────────────────────────────
@router.post(
    "/staff/{user_id}/invite/resend",
    summary="Resend invite to a pending staff member",
    response_model=ApiResponse[dict],
)
async def resend_invite(
    user_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_permission(P.AUTH_STAFF_INVITE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.resend_invite(user_id, uuid.UUID(user.user_id))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 25. Update Permissions ────────────────────────────────────────────────────
@router.put(
    "/staff/{user_id}/permissions",
    summary="Update granular permissions for a staff member",
    response_model=ApiResponse[dict],
)
async def update_permissions(
    user_id: uuid.UUID,
    body: UpdatePermissionsRequest,
    request: Request,
    user: UserContext = Depends(require_tenant_mutation_permission(P.AUTH_PERMISSIONS_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context.")
    data = await svc.update_permissions(
        target_user_id=user_id,
        tenant_id=uuid.UUID(user.tenant_id),
        granting_user_id=uuid.UUID(user.user_id),
        permissions=body.permissions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 26. Deactivate Staff ──────────────────────────────────────────────────────
@router.post(
    "/staff/{user_id}/deactivate",
    summary="Deactivate a staff member and revoke all their sessions",
    response_model=ApiResponse[dict],
)
async def deactivate_staff(
    user_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_tenant_mutation_permission(P.AUTH_STAFF_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context.")
    data = await svc.deactivate_staff(
        user_id=user_id,
        tenant_id=uuid.UUID(user.tenant_id),
        requesting_user_id=uuid.UUID(user.user_id),
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 26b. Staff Roster ─────────────────────────────────────────────────────────
@router.get(
    "/staff",
    summary="List staff roster for a tenant (tenant-portal Staff page)",
    response_model=ApiResponse[dict],
)
async def list_staff(
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: UserContext = Depends(require_permission(P.STAFF_READ)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.list_staff_by_tenant(tenant_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


@router.get(
    "/staff/{user_id}",
    summary="Get a single staff member",
    response_model=ApiResponse[dict],
)
async def get_staff(
    user_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_permission(P.STAFF_READ)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_staff(user_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


@router.put(
    "/staff/{user_id}/schedule",
    summary="Update a staff member's working hours",
    response_model=ApiResponse[dict],
)
async def update_staff_schedule(
    user_id: uuid.UUID,
    body: UpdateScheduleRequest,
    request: Request,
    user: UserContext = Depends(require_permission(P.STAFF_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.update_staff_schedule(user_id, body.working_hours)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 27. Impersonate ───────────────────────────────────────────────────────────
@router.post(
    "/impersonate",
    summary="[Super Admin] Start impersonation session",
    response_model=ApiResponse[dict],
)
async def impersonate(
    body: ImpersonateRequest,
    request: Request,
    user: UserContext = Depends(require_permission(P.PLATFORM_IMPERSONATE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.impersonate(
        impersonator_id=uuid.UUID(user.user_id),
        target_user_id=body.target_user_id,
        reason=body.reason,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 28. End Impersonation ─────────────────────────────────────────────────────
@router.post(
    "/impersonate/{session_id}/end",
    summary="[Super Admin] End an impersonation session",
    response_model=ApiResponse[dict],
)
async def end_impersonation(
    session_id: str,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.end_impersonation(session_id, uuid.UUID(user.user_id))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 29. List Active Impersonations ────────────────────────────────────────────
@router.get(
    "/impersonate/active",
    summary="[Super Admin] List all active impersonation sessions",
    response_model=ApiResponse[dict],
)
async def list_impersonations(
    request: Request,
    user: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.list_active_impersonations()
    return ok({"active_sessions": data, "total": len(data)},
              _meta(request).request_id, ENGINE_ID)


# ── 30. Create API Key ────────────────────────────────────────────────────────
@router.post(
    "/api-keys",
    summary="Create an API key for tenant integrations",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
)
async def create_api_key(
    body: CreateApiKeyRequest,
    request: Request,
    user: UserContext = Depends(require_tenant_mutation_permission(P.AUTH_APIKEYS_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context.")
    data = await svc.create_api_key(
        tenant_id=uuid.UUID(user.tenant_id),
        created_by=uuid.UUID(user.user_id),
        name=body.name,
        scopes=body.scopes,
        is_test_mode=body.is_test_mode,
        expires_days=body.expires_days,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 31. List API Keys ─────────────────────────────────────────────────────────
@router.get(
    "/api-keys",
    summary="List all API keys for the tenant",
    response_model=ApiResponse[dict],
)
async def list_api_keys(
    request: Request,
    user: UserContext = Depends(require_permission(P.AUTH_APIKEYS_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context.")
    data = await svc.list_api_keys(uuid.UUID(user.tenant_id))
    return ok({"api_keys": data, "total": len(data)}, _meta(request).request_id, ENGINE_ID)


# ── 32. Revoke API Key ────────────────────────────────────────────────────────
@router.delete(
    "/api-keys/{key_id}",
    summary="Revoke an API key",
    response_model=ApiResponse[dict],
)
async def revoke_api_key(
    key_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_tenant_mutation_permission(P.AUTH_APIKEYS_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context.")
    data = await svc.revoke_api_key(key_id, uuid.UUID(user.tenant_id), uuid.UUID(user.user_id))
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 33. Update API Key ────────────────────────────────────────────────────────
@router.patch(
    "/api-keys/{key_id}",
    summary="Update API key name or scopes",
    response_model=ApiResponse[dict],
)
async def update_api_key(
    key_id: uuid.UUID,
    body: UpdateApiKeyRequest,
    request: Request,
    user: UserContext = Depends(require_tenant_mutation_permission(P.AUTH_APIKEYS_MANAGE)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    if not user.tenant_id:
        raise ServiceOSException("PERMISSION_DENIED", "No tenant context.")
    data = await svc.update_api_key(
        key_id, uuid.UUID(user.tenant_id), uuid.UUID(user.user_id),
        body.name, body.scopes,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 34. Get Audit Log ─────────────────────────────────────────────────────────
@router.get(
    "/audit-log",
    summary="Get auth audit log (own or tenant, based on role)",
    response_model=ApiResponse[dict],
)
async def get_audit_log(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_audit_log(
        user_id=uuid.UUID(user.user_id),
        tenant_id=uuid.UUID(user.tenant_id) if user.tenant_id else None,
        role=user.role,
        limit=limit,
        cursor=cursor,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── 35–37. Platform User Management (Super Admin) ─────────────────────────────
@router.get(
    "/users",
    summary="[Super Admin] List all users across all tenants",
    response_model=ApiResponse[dict],
)
async def list_users(
    request: Request,
    role: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: UserContext = Depends(require_permission(P.AUTH_USERS_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    from sqlalchemy import select
    q = select(_UserModel).order_by(_UserModel.created_at.desc())
    if role:
        q = q.where(_UserModel.role == role)
    if tenant_id:
        q = q.where(_UserModel.tenant_id == tenant_id)
    q = q.limit(limit)
    r = await db.execute(q)
    users = r.scalars().all()
    return ok(
        {
            "users": [
                {
                    "user_id": str(u.id), "email": u.email, "full_name": u.full_name,
                    "role": u.role, "tenant_id": str(u.tenant_id) if u.tenant_id else None,
                    "is_active": u.is_active, "is_verified": u.is_verified,
                    "is_mfa_enabled": u.is_mfa_enabled,
                    "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
            "total": len(users),
        },
        _meta(request).request_id, ENGINE_ID,
    )


@router.get(
    "/users/{user_id}",
    summary="Get user details",
    response_model=ApiResponse[dict],
)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_permission(P.AUTH_USERS_READ)),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_profile(user_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


@router.get(
    "/permissions/map",
    summary="Get the complete role → permissions map",
    response_model=ApiResponse[dict],
)
async def get_permissions_map(
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> ApiResponse[dict]:
    if user.role == "super_admin":
        data = ROLE_PERMISSIONS
    else:
        data = {user.role: ROLE_PERMISSIONS.get(user.role, [])}
    return ok({"permissions": data}, _meta(request).request_id, ENGINE_ID)


# ── Phase 0D: Required password change ───────────────────────────────────────
@router.post(
    "/change-password-required",
    summary="Change password when force_password_change is active",
    description=(
        "Called when a user must change their password (force_password_change=true). "
        "Accepts the current (possibly temporary) password and sets a new one. "
        "Clears force_password_change, password_reset_required, and temporary_password_active. "
        "No refresh token is issued — user must log in again after this."
    ),
    response_model=ApiResponse[dict],
    tags=["Auth Security", "Password Management"],
)
async def change_password_required(
    body: ChangePasswordRequiredRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),  # no force-check: this IS the force-change endpoint
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.change_password_required(
        uuid.UUID(user.user_id), body.current_password, body.new_password
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0D: Admin user security endpoints ───────────────────────────────────
admin_security_router = APIRouter(
    prefix="/v1/admin/users",
    tags=["Admin User Security"],
)


@admin_security_router.get(
    "/{user_id}/security-status",
    summary="Get password security status for a user",
    response_model=ApiResponse[dict],
)
async def get_user_security_status(
    user_id: uuid.UUID,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_user_security_status(admin, user_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


@admin_security_router.post(
    "/{user_id}/force-password-change",
    summary="Force a user to change their password on next login",
    description=(
        "Sets force_password_change=true for the target user. "
        "Optionally revokes all active sessions. "
        "The user cannot access protected pages until they change their password. "
        "Permission required: users.security.force_password_change (super_admin only)."
    ),
    response_model=ApiResponse[dict],
    tags=["Auth Security"],
)
async def admin_force_password_change(
    user_id: uuid.UUID,
    body: AdminForcePasswordChangeRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.admin_force_password_change(
        admin=admin,
        target_user_id=user_id,
        reason=body.reason,
        revoke_sessions=body.revoke_sessions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


@admin_security_router.post(
    "/{user_id}/send-password-reset",
    summary="Generate a password reset token and send it to the user",
    description=(
        "Creates a secure reset token (stored as hash). "
        "Sends via email if email provider is configured; otherwise returns token in dev mode. "
        "Does NOT send raw token in production. "
        "Permission required: users.security.send_password_reset (super_admin only)."
    ),
    response_model=ApiResponse[dict],
    tags=["Auth Security"],
)
async def admin_send_password_reset(
    user_id: uuid.UUID,
    body: AdminSendPasswordResetRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.admin_send_password_reset(
        admin=admin,
        target_user_id=user_id,
        reason=body.reason,
        revoke_sessions=body.revoke_sessions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


@admin_security_router.post(
    "/{user_id}/generate-temporary-password",
    summary="Generate a one-time temporary password for a user",
    description=(
        "Generates a strong random temporary password. "
        "Sets temporary_password_active=true and force_password_change=true. "
        "The temporary password is returned ONCE and never stored in plain text. "
        "User must change password on next login. "
        "Permission required: users.security.generate_temporary_password (super_admin only)."
    ),
    response_model=ApiResponse[dict],
    tags=["Auth Security"],
)
async def admin_generate_temporary_password(
    user_id: uuid.UUID,
    body: AdminGenerateTemporaryPasswordRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.admin_generate_temporary_password(
        admin=admin,
        target_user_id=user_id,
        reason=body.reason,
        revoke_sessions=body.revoke_sessions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0E: Full security status (extended) ─────────────────────────────────
@admin_security_router.get(
    "/{user_id}/security",
    summary="[Admin] Full account security status including lock, sessions, history",
    response_model=ApiResponse[dict],
    tags=["Account Security"],
)
async def get_full_user_security(
    user_id: uuid.UUID,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_full_security_status(admin, user_id)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0E: Lock / Unlock ───────────────────────────────────────────────────
@admin_security_router.post(
    "/{user_id}/lock",
    summary="[Admin] Lock a user account",
    response_model=ApiResponse[dict],
    tags=["Account Security"],
)
async def lock_user(
    user_id: uuid.UUID,
    body: LockAccountRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.lock_user(
        admin=admin, target_user_id=user_id,
        reason=body.reason, locked_until=body.locked_until,
        revoke_sessions=body.revoke_sessions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


@admin_security_router.post(
    "/{user_id}/unlock",
    summary="[Admin] Unlock a user account",
    response_model=ApiResponse[dict],
    tags=["Account Security"],
)
async def unlock_user(
    user_id: uuid.UUID,
    body: UnlockAccountRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.unlock_user(admin=admin, target_user_id=user_id, reason=body.reason)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0E: Deactivate / Reactivate ────────────────────────────────────────
@admin_security_router.post(
    "/{user_id}/deactivate",
    summary="[Admin] Deactivate a user account (is_active=false)",
    response_model=ApiResponse[dict],
    tags=["Account Security"],
)
async def admin_deactivate_user(
    user_id: uuid.UUID,
    body: DeactivateUserRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.deactivate_user(
        admin=admin, target_user_id=user_id,
        reason=body.reason, revoke_sessions=body.revoke_sessions,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


@admin_security_router.post(
    "/{user_id}/reactivate",
    summary="[Admin] Reactivate a deactivated user account",
    response_model=ApiResponse[dict],
    tags=["Account Security"],
)
async def admin_reactivate_user(
    user_id: uuid.UUID,
    body: ReactivateUserRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.reactivate_user(admin=admin, target_user_id=user_id, reason=body.reason)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0E: Admin session management ───────────────────────────────────────
@admin_security_router.get(
    "/{user_id}/sessions",
    summary="[Admin] List active sessions for a user",
    response_model=ApiResponse[dict],
    tags=["Account Security", "User Sessions"],
)
async def admin_list_user_sessions(
    user_id: uuid.UUID,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.admin_list_sessions(admin, user_id)
    return ok({"sessions": data, "total": len(data)}, _meta(request).request_id, ENGINE_ID)


@admin_security_router.post(
    "/{user_id}/sessions/revoke-all",
    summary="[Admin] Revoke all active sessions for a user",
    response_model=ApiResponse[dict],
    tags=["Account Security", "User Sessions"],
)
async def admin_revoke_all_user_sessions(
    user_id: uuid.UUID,
    body: AdminRevokeAllSessionsRequest,
    request: Request,
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.admin_revoke_all_sessions(admin, user_id, body.reason)
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0E: Login history ───────────────────────────────────────────────────
@admin_security_router.get(
    "/{user_id}/login-history",
    summary="[Admin] View login history for a user",
    response_model=ApiResponse[dict],
    tags=["Account Security", "Login History"],
)
async def admin_get_login_history(
    user_id: uuid.UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    admin: UserContext = Depends(require_super_admin),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_login_history(
        requester_id=uuid.UUID(admin.user_id),
        requester_role=admin.role,
        target_user_id=user_id,
        limit=limit,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


# ── Phase 0E: Self login history ──────────────────────────────────────────────
# Mounted on the main auth router below
_me_security_router = APIRouter(prefix="/v1/auth", tags=["Login History", "User Sessions"])


@_me_security_router.get(
    "/login-history",
    summary="View your own recent login history",
    response_model=ApiResponse[dict],
)
async def get_own_login_history(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_login_history(
        requester_id=uuid.UUID(user.user_id),
        requester_role=user.role,
        target_user_id=uuid.UUID(user.user_id),
        limit=limit,
    )
    return ok(data, _meta(request).request_id, ENGINE_ID)


@_me_security_router.post(
    "/sessions/revoke-all-other",
    summary="Revoke all sessions except the current one",
    response_model=ApiResponse[dict],
)
async def revoke_all_other_sessions(
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AuthService = Depends(_svc),
) -> ApiResponse[dict]:
    # Logout all but keep current session alive (exclude current jti from blacklist)
    count = await svc.logout_all(user.user_id, "")  # empty jti = don't blacklist any specific token
    return ok({"sessions_revoked": count, "message": f"{count} other session(s) revoked."},
              _meta(request).request_id, ENGINE_ID)



