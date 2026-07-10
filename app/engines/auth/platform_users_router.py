"""P0 Enterprise Platform Users — /v1/admin/platform-users.

Extends the existing Phase 0D/0E account-security infrastructure (lock/unlock,
deactivate/reactivate, sessions, login history, password actions) with:
  - platform-scoped list/summary/detail (user_group separation)
  - role & access-scope governance
  - MFA enforcement / reset
  - suspend/unsuspend
  - computed risk signals
  - invite lifecycle
  - audit trail
  - bulk actions

All mutating routes additionally require the actor not be a "read_only_admin"
platform_role via `require_platform_mutate`, layered on top of require_super_admin.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_client_ip
from app.dependencies.auth import UserContext, require_super_admin, get_current_user
from app.dependencies.db import get_db
from app.engines.auth.service import AuthService
from app.engines.auth.schemas import (
    LockAccountRequest, UnlockAccountRequest, DeactivateUserRequest, ReactivateUserRequest,
    AdminRevokeAllSessionsRequest, AdminForcePasswordChangeRequest, AdminSendPasswordResetRequest,
    AdminGenerateTemporaryPasswordRequest, SuspendUserRequest, UnsuspendUserRequest,
    RequireMfaRequest, ResetMfaRequest, RevokeSessionRequest, ChangeRoleRequest,
    ChangeAccessScopeRequest, InvitePlatformUserRequest, RevokeInviteRequest,
    BulkPlatformActionRequest,
)
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException

router = APIRouter(prefix="/v1/admin/platform-users", tags=["Platform Users"])
ENGINE_ID = "auth"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db=db, request_id=_rid(r), ip_address=get_client_ip(r))


async def require_platform_mutate(
    admin: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """require_super_admin plus a block on the advisory 'read_only_admin' platform_role."""
    from sqlalchemy import select
    from app.engines.auth.models import User
    platform_role = await db.scalar(select(User.platform_role).where(User.id == uuid.UUID(admin.user_id)))
    if platform_role == "read_only_admin":
        raise ServiceOSException("PERMISSION_DENIED", "Read-only admins cannot perform this action.")
    return admin


# ── List / Summary / Detail ───────────────────────────────────────────────────

@router.get("/summary")
async def get_summary(
    r: Request, db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).get_platform_users_summary(), _rid(r), ENGINE_ID)


@router.get("")
async def list_users(
    r: Request,
    user_group: str = Query("platform"),
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    platform_role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    mfa_status: Optional[str] = Query(None),
    access_scope: Optional[str] = Query(None),
    inactive_days_min: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).list_platform_users(
        user_group=user_group, q=q, role=role, platform_role=platform_role,
        status=status, mfa_status=mfa_status, access_scope=access_scope,
        inactive_days_min=inactive_days_min, page=page, limit=limit,
    ), _rid(r), ENGINE_ID)


@router.get("/export")
async def export_users(
    r: Request, user_group: str = Query("platform"),
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    data = await _svc(r, db).list_platform_users(user_group=user_group, limit=10000)
    return ok({"rows": data["users"], "count": len(data["users"]), "format": "json"}, _rid(r), ENGINE_ID)


@router.get("/audit-logs")
async def list_audit_logs(
    r: Request, action_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).list_platform_audit_logs(action_type, page, limit), _rid(r), ENGINE_ID)


@router.get("/invites")
async def list_invites(
    r: Request, db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).list_platform_invites(), _rid(r), ENGINE_ID)


@router.post("/invite", status_code=201)
async def invite_user(
    r: Request, body: InvitePlatformUserRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).invite_platform_user(
        admin, body.email, body.full_name, body.phone, body.platform_role,
        body.access_scope, body.require_mfa, body.invite_expiry_days,
    ), _rid(r), ENGINE_ID)


@router.post("/invites/{invite_id}/resend")
async def resend_invite(
    r: Request, invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    data = await _svc(r, db).resend_invite(invite_id, uuid.UUID(admin.user_id))
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/invites/{invite_id}/revoke")
async def revoke_invite(
    r: Request, invite_id: uuid.UUID, body: RevokeInviteRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).revoke_platform_invite(admin, invite_id, body.reason), _rid(r), ENGINE_ID)


@router.post("/bulk/{action}")
async def bulk_action(
    r: Request, action: str, body: BulkPlatformActionRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).bulk_platform_action(admin, action, body.user_ids, body.reason),
              _rid(r), ENGINE_ID)


@router.get("/{user_id}")
async def get_detail(
    r: Request, user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).get_platform_user_detail(admin, user_id), _rid(r), ENGINE_ID)


# ── Role & Access Scope ───────────────────────────────────────────────────────

@router.put("/{user_id}/role")
async def change_role(
    r: Request, user_id: uuid.UUID, body: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).change_platform_role(admin, user_id, body.platform_role, body.reason),
              _rid(r), ENGINE_ID)


@router.put("/{user_id}/access-scope")
async def change_scope(
    r: Request, user_id: uuid.UUID, body: ChangeAccessScopeRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).change_access_scope(admin, user_id, body.access_scope, body.reason),
              _rid(r), ENGINE_ID)


# ── Lifecycle ──────────────────────────────────────────────────────────────────

@router.post("/{user_id}/suspend")
async def suspend(
    r: Request, user_id: uuid.UUID, body: SuspendUserRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).suspend_user(admin, user_id, body.reason, body.revoke_sessions),
              _rid(r), ENGINE_ID)


@router.post("/{user_id}/unsuspend")
async def unsuspend(
    r: Request, user_id: uuid.UUID, body: UnsuspendUserRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).unsuspend_user(admin, user_id, body.reason), _rid(r), ENGINE_ID)


@router.post("/{user_id}/deactivate")
async def deactivate(
    r: Request, user_id: uuid.UUID, body: DeactivateUserRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).deactivate_user(admin, user_id, body.reason, body.revoke_sessions),
              _rid(r), ENGINE_ID)


@router.post("/{user_id}/reactivate")
async def reactivate(
    r: Request, user_id: uuid.UUID, body: ReactivateUserRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).reactivate_user(admin, user_id, body.reason), _rid(r), ENGINE_ID)


@router.post("/{user_id}/lock")
async def lock(
    r: Request, user_id: uuid.UUID, body: LockAccountRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).lock_user(admin, user_id, body.reason, body.locked_until, body.revoke_sessions),
              _rid(r), ENGINE_ID)


@router.post("/{user_id}/unlock")
async def unlock(
    r: Request, user_id: uuid.UUID, body: UnlockAccountRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).unlock_user(admin, user_id, body.reason), _rid(r), ENGINE_ID)


# ── MFA & Password ────────────────────────────────────────────────────────────

@router.post("/{user_id}/require-mfa")
async def require_mfa(
    r: Request, user_id: uuid.UUID, body: RequireMfaRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).require_mfa_for_user(admin, user_id, body.reason), _rid(r), ENGINE_ID)


@router.post("/{user_id}/reset-mfa")
async def reset_mfa(
    r: Request, user_id: uuid.UUID, body: ResetMfaRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).reset_mfa_for_user(admin, user_id, body.reason), _rid(r), ENGINE_ID)


@router.post("/{user_id}/force-password-reset")
async def force_password_reset(
    r: Request, user_id: uuid.UUID, body: AdminForcePasswordChangeRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).admin_force_password_change(
        admin, user_id, body.reason, body.revoke_sessions), _rid(r), ENGINE_ID)


@router.post("/{user_id}/send-reset-link")
async def send_reset_link(
    r: Request, user_id: uuid.UUID, body: AdminSendPasswordResetRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).admin_send_password_reset(
        admin, user_id, body.reason, body.revoke_sessions), _rid(r), ENGINE_ID)


@router.post("/{user_id}/generate-temp-password")
async def generate_temp_password(
    r: Request, user_id: uuid.UUID, body: AdminGenerateTemporaryPasswordRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    # Restricted to Super Admin only (not just require_platform_mutate) per spec Part F.
    return ok(await _svc(r, db).admin_generate_temporary_password(
        admin, user_id, body.reason, body.revoke_sessions), _rid(r), ENGINE_ID)


# ── Sessions / Login History / Risk / Audit ───────────────────────────────────

@router.get("/{user_id}/sessions")
async def list_sessions(
    r: Request, user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    data = await _svc(r, db).admin_list_sessions(admin, user_id)
    return ok({"sessions": data, "total": len(data)}, _rid(r), ENGINE_ID)


@router.post("/{user_id}/sessions/{session_id}/revoke")
async def revoke_session(
    r: Request, user_id: uuid.UUID, session_id: uuid.UUID, body: RevokeSessionRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).admin_revoke_session(admin, user_id, session_id, body.reason),
              _rid(r), ENGINE_ID)


@router.post("/{user_id}/sessions/revoke-all")
async def revoke_all_sessions(
    r: Request, user_id: uuid.UUID, body: AdminRevokeAllSessionsRequest,
    db: AsyncSession = Depends(get_db), admin=Depends(require_platform_mutate),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).admin_revoke_all_sessions(admin, user_id, body.reason), _rid(r), ENGINE_ID)


@router.get("/{user_id}/login-history")
async def login_history(
    r: Request, user_id: uuid.UUID, limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    data = await _svc(r, db).get_login_history(
        requester_id=uuid.UUID(admin.user_id), requester_role=admin.role,
        target_user_id=user_id, limit=limit,
    )
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/{user_id}/risk-signals")
async def risk_signals(
    r: Request, user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).get_platform_user_risk_signals(admin, user_id), _rid(r), ENGINE_ID)


@router.get("/{user_id}/audit-logs")
async def user_audit_logs(
    r: Request, user_id: uuid.UUID,
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), admin=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(r, db).get_platform_user_audit_logs(admin, user_id, page, limit),
              _rid(r), ENGINE_ID)
