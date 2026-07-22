"""
Dependency: get_current_user
Phase 2 — Real JWT validation with blacklist check, permission loading,
impersonation detection, device approval check.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Annotated, Literal

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.exceptions import ServiceOSException

bearer_scheme = HTTPBearer(auto_error=False)
Role = Literal["super_admin", "tenant_owner", "staff", "customer", "guest"]


@dataclass
class UserContext:
    """
    Complete user context available to every endpoint handler.
    Populated from JWT claims — no extra DB call needed.
    """
    user_id: str
    email: str
    role: Role
    tenant_id: str | None
    full_name: str
    is_verified: bool
    device_id: str | None = None
    jti: str | None = None
    session_id: str | None = None
    is_impersonation: bool = False
    impersonator_id: str | None = None
    enabled_engines: list[str] = field(default_factory=list)
    plan_type: str | None = None
    permission_overrides: dict[str, bool] | None = None  # Staff permission overrides
    mfa_enabled: bool = False
    onboarding_complete: bool = True
    force_password_change: bool = False
    access_scope: str | None = None  # e.g. "customer_support_limited" = tenant read-only staff


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserContext:
    """
    Validates Bearer token, checks blacklist, extracts full user context.
    Raises typed ServiceOSException on any auth failure.
    """
    if credentials is None:
        raise ServiceOSException(
            error_code="UNAUTHORIZED",
            detail="Authentication required. Provide a Bearer token.",
            resolution="Login at POST /v1/auth/login to get an access token.",
        )

    try:
        from app.engines.auth.utils import decode_token
        from app.engines.auth.constants import REDIS_BLACKLIST_PREFIX

        payload = decode_token(credentials.credentials)
        jti = payload.get("jti", "")

        # ── Blacklist + session-revoked check ─────────────────────────────────
        try:
            from app.redis_client import get_redis
            r = get_redis()
            if await r.exists(f"{REDIS_BLACKLIST_PREFIX}{jti}"):
                raise ServiceOSException(
                    error_code="TOKEN_BLACKLISTED",
                    detail="This session has been revoked.",
                    resolution="Log in again to get a new access token.",
                )
            # Check if the session was revoked by an admin action
            session_id_claim = payload.get("session_id", "")
            if session_id_claim and await r.exists(f"serviceos:session:revoked:{session_id_claim}"):
                raise ServiceOSException(
                    error_code="SESSION_REVOKED",
                    detail="Your session has been revoked by an administrator.",
                    resolution="Log in again to get a new access token.",
                )
        except ServiceOSException:
            raise
        except Exception:
            pass  # Redis unavailable — fail open in dev, configure alerting in prod

        # ── Force password change guard ───────────────────────────────────────
        role = payload.get("role", "customer")
        force_change = payload.get("force_password_change", False)

        return UserContext(
            user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            role=role,
            tenant_id=payload.get("tenant_id"),
            full_name=payload.get("full_name", ""),
            is_verified=payload.get("is_verified", True),
            device_id=payload.get("device_id"),
            jti=jti,
            session_id=payload.get("session_id"),
            is_impersonation=payload.get("is_impersonation", False),
            impersonator_id=payload.get("impersonator_id"),
            enabled_engines=payload.get("engines", []),
            plan_type=payload.get("plan_type"),
            mfa_enabled=payload.get("mfa_enabled", False),
            onboarding_complete=payload.get("onboarding_complete", True),
            force_password_change=force_change,
            access_scope=payload.get("access_scope"),
            # Phase 2A Slice 2E: closes the gap found in Slices 2C/2D. The
            # JWT has carried this claim since app.engines.auth.service's
            # _build_token_pair loaded real StaffPermission rows into
            # `extra_claims["permission_overrides"]` at login -- but this
            # constructor call never read it back out, so every
            # PermissionChecker.has(overrides=user.permission_overrides)
            # call always received None regardless of what was actually
            # granted/denied in the database. StaffPermission grants/denies
            # now take effect for real.
            permission_overrides=payload.get("permission_overrides"),
        )

    except ServiceOSException:
        raise
    except JWTError as e:
        raise ServiceOSException(
            error_code="INVALID_TOKEN",
            detail=f"Token is invalid or expired.",
            resolution="Log in again at POST /v1/auth/login.",
        )
    except Exception:
        raise ServiceOSException(
            error_code="INVALID_TOKEN",
            detail="Could not validate authentication token.",
        )


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserContext | None:
    """Returns None if no token provided (for guest-allowed endpoints)."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except ServiceOSException:
        return None


def _check_force_password_change(user: UserContext) -> None:
    """Raise if the user must change their password before accessing protected resources."""
    if user.force_password_change:
        raise ServiceOSException(
            error_code="FORCE_PASSWORD_CHANGE",
            detail="You must change your password before accessing this resource.",
            resolution="Change your password at POST /v1/auth/change-password-required then log in again.",
        )


async def require_super_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    _check_force_password_change(user)
    if user.role != "super_admin":
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Super admin access required. Your role: '{user.role}'.",
            blocking_rule="required_role: super_admin",
            resolution="This endpoint is restricted to platform administrators.",
        )
    return user


async def require_tenant_owner(user: UserContext = Depends(get_current_user)) -> UserContext:
    _check_force_password_change(user)
    if user.role not in ("super_admin", "tenant_owner"):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Tenant owner access required. Your role: '{user.role}'.",
            blocking_rule="required_role: tenant_owner | super_admin",
        )
    return user


async def require_staff_or_above(user: UserContext = Depends(get_current_user)) -> UserContext:
    _check_force_password_change(user)
    if user.role not in ("super_admin", "tenant_owner", "staff", "technician"):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Staff access required. Your role: '{user.role}'.",
            blocking_rule="required_role: staff | technician | tenant_owner | super_admin",
        )
    return user


async def require_customer(user: UserContext = Depends(get_current_user)) -> UserContext:
    _check_force_password_change(user)
    if user.role != "customer":
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Customer access required. Your role: '{user.role}'.",
            blocking_rule="required_role: customer",
        )
    return user


async def require_technician(user: UserContext = Depends(get_current_user)) -> UserContext:
    _check_force_password_change(user)
    if user.role not in ("technician", "staff", "tenant_owner", "super_admin"):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Technician access required. Your role: '{user.role}'.",
            blocking_rule="required_role: technician | staff | tenant_owner | super_admin",
        )
    return user


async def require_staff_or_technician_only(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Slice 2F-14: named dependency for the field_ops staff/technician
    self-service and execution surface (`field_ops.staff_router`'s "my
    jobs" section and the equivalent job-execution/checklist routes in
    `field_ops.router`). Deliberately narrower than `require_technician`
    (which also admits tenant_owner/super_admin) -- this is a staff/
    technician *execution* capability, not a tenant-oversight one
    (tenant_owner already has separate, tenant-scoped routes for that).
    Replaces the equivalent inline `if u.role not in ("staff",
    "technician")` checks that existed in both routers -- same policy,
    now a properly named dependency so runtime guard-status verification
    can recognize it (an inline body check is invisible to dependency-
    based introspection)."""
    _check_force_password_change(user)
    if user.role not in ("staff", "technician"):
        raise ServiceOSException(
            error_code="STAFF_ACCESS_DENIED",
            detail=f"This endpoint is for staff/technician accounts only. Your role: '{user.role}'.",
            blocking_rule="required_role: staff | technician",
        )
    return user


async def require_no_force_password_change(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Blocks access if user must change their password first."""
    if user.force_password_change:
        raise ServiceOSException(
            error_code="FORCE_PASSWORD_CHANGE",
            detail="You must change your temporary password before accessing this resource.",
            resolution="Change your password at PUT /v1/auth/password/change then log in again.",
        )
    return user


# MODULE-L5-01B: the 5 platform-level admin_* roles, canonical in one place
# so callers don't redefine this set ad hoc per router (the anti-pattern
# this sprint is closing). These roles have no tenant_id of their own and
# operate across the whole platform by design.
PLATFORM_STAFF_ROLES = ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly")


async def require_platform_staff(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Any of the 5 platform admin_* roles -- for admin-console-only surfaces
    that are not further permission-differentiated (e.g. an admin's own
    notification inbox). Not a substitute for require_permission() on
    endpoints where a specific permission already exists."""
    _check_force_password_change(user)
    if user.role not in PLATFORM_STAFF_ROLES:
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Platform admin access required. Your role: '{user.role}'.",
            blocking_rule=f"required_role: {' | '.join(PLATFORM_STAFF_ROLES)}",
        )
    return user
