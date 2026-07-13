"""Security Engine — Admin Router (SOC).
All endpoints under /v1/admin/security/*. All write endpoints are permission-guarded
via P.SECURITY_*; super_admin holds P.ALL so this is additive, not a regression.
The pre-existing /v1/security/* router (internal API-key verification, etc.) is untouched.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.security.admin_service import SecurityAdminService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/security", tags=["Security SOC"])
ENGINE_ID = "security"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.SECURITY_READ))) -> SecurityAdminService:
    return SecurityAdminService(db=db, request_id=getattr(r.state, "request_id", "—"),
                                 actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                                 actor_role=u.role, actor_ip=r.client.host if r.client else None)


def _rid(r): return getattr(r.state, "request_id", "—")


# ═══════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════

@router.get("/overview", response_model=ApiResponse[dict], summary="SOC overview")
async def overview(r: Request, s: SecurityAdminService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await s.get_security_overview(), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# THREATS
# ═══════════════════════════════════════════════════════════════

@router.get("/threats", response_model=ApiResponse[dict], summary="List threats")
async def list_threats(r: Request,
                        status: str | None = Query(None), threat_level: str | None = Query(None),
                        activity_type: str | None = Query(None), q: str | None = Query(None),
                        limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None),
                        u: UserContext = Depends(require_permission(P.SECURITY_THREATS_READ)),
                        s: SecurityAdminService = Depends(_svc)):
    return ok(await s.list_threats(status, threat_level, activity_type, q, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/threats/{threat_id}", response_model=ApiResponse[dict], summary="Get threat detail")
async def threat_detail(r: Request, threat_id: uuid.UUID,
                         u: UserContext = Depends(require_permission(P.SECURITY_THREATS_READ)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_threat_detail(threat_id), _rid(r), ENGINE_ID)


class AssignThreatBody(BaseModel):
    admin_id: uuid.UUID


@router.post("/threats/{threat_id}/assign", response_model=ApiResponse[dict], summary="Assign threat")
async def assign_threat(r: Request, threat_id: uuid.UUID, body: AssignThreatBody,
                         u: UserContext = Depends(require_permission(P.SECURITY_THREATS_UPDATE)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.assign_threat(threat_id, body.admin_id), _rid(r), ENGINE_ID)


class ThreatStatusBody(BaseModel):
    status: str
    notes: str | None = None


@router.post("/threats/{threat_id}/status", response_model=ApiResponse[dict], summary="Update threat status")
async def update_threat_status(r: Request, threat_id: uuid.UUID, body: ThreatStatusBody,
                                u: UserContext = Depends(require_permission(P.SECURITY_THREATS_RESOLVE)),
                                s: SecurityAdminService = Depends(_svc)):
    return ok(await s.update_threat_status(threat_id, body.status, body.notes), _rid(r), ENGINE_ID)


class BlockIpFromThreatBody(BaseModel):
    reason: str
    expires_hours: int | None = 720


@router.post("/threats/{threat_id}/block-ip", response_model=ApiResponse[dict], summary="Block IP from threat")
async def block_ip_from_threat(r: Request, threat_id: uuid.UUID, body: BlockIpFromThreatBody,
                                u: UserContext = Depends(require_permission(P.SECURITY_THREATS_BLOCK_IP)),
                                s: SecurityAdminService = Depends(_svc)):
    return ok(await s.block_ip_from_threat(threat_id, body.reason, body.expires_hours), _rid(r), ENGINE_ID)


class RevokeSessionsBody(BaseModel):
    reason: str


@router.post("/threats/{threat_id}/revoke-sessions", response_model=ApiResponse[dict],
             summary="Revoke sessions from threat")
async def revoke_sessions_from_threat(r: Request, threat_id: uuid.UUID, body: RevokeSessionsBody,
                                       u: UserContext = Depends(require_permission(P.SECURITY_THREATS_UPDATE)),
                                       s: SecurityAdminService = Depends(_svc)):
    return ok(await s.revoke_sessions_from_threat(threat_id, body.reason), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# ACTIVE SESSIONS
# ═══════════════════════════════════════════════════════════════

@router.get("/sessions", response_model=ApiResponse[dict], summary="List active sessions")
async def list_sessions(r: Request,
                         tenant_id: uuid.UUID | None = Query(None), role: str | None = Query(None),
                         active_only: bool = Query(True), q: str | None = Query(None),
                         limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None),
                         u: UserContext = Depends(require_permission(P.SECURITY_SESSIONS_READ)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.list_sessions(tenant_id, role, active_only, q, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/sessions/{session_id}", response_model=ApiResponse[dict], summary="Get session detail")
async def session_detail(r: Request, session_id: uuid.UUID,
                          u: UserContext = Depends(require_permission(P.SECURITY_SESSIONS_READ)),
                          s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_session_detail(session_id), _rid(r), ENGINE_ID)


class RevokeSessionBody(BaseModel):
    reason: str


@router.post("/sessions/{session_id}/revoke", response_model=ApiResponse[dict], summary="Revoke session")
async def revoke_session(r: Request, session_id: uuid.UUID, body: RevokeSessionBody,
                          u: UserContext = Depends(require_permission(P.SECURITY_SESSIONS_REVOKE)),
                          s: SecurityAdminService = Depends(_svc)):
    return ok(await s.revoke_session(session_id, body.reason), _rid(r), ENGINE_ID)


class RevokeAllSessionsBody(BaseModel):
    reason: str


@router.post("/sessions/user/{user_id}/revoke-all", response_model=ApiResponse[dict],
             summary="Revoke all sessions for a user")
async def revoke_all_sessions(r: Request, user_id: uuid.UUID, body: RevokeAllSessionsBody,
                               u: UserContext = Depends(require_permission(P.SECURITY_SESSIONS_REVOKE)),
                               s: SecurityAdminService = Depends(_svc)):
    return ok(await s.revoke_all_user_sessions(user_id, body.reason), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# IP BLOCKLIST
# ═══════════════════════════════════════════════════════════════

@router.get("/ip-blocklist", response_model=ApiResponse[dict], summary="List IP blocklist")
async def list_ip_blocklist(r: Request,
                             status: str | None = Query(None), scope: str | None = Query(None),
                             q: str | None = Query(None),
                             limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None),
                             u: UserContext = Depends(require_permission(P.SECURITY_IP_BLOCKLIST_READ)),
                             s: SecurityAdminService = Depends(_svc)):
    return ok(await s.list_ip_blocklist(status, scope, q, limit, cursor), _rid(r), ENGINE_ID)


class CreateIpBlockBody(BaseModel):
    ip_or_cidr: str
    entry_type: str = "ip"
    reason: str
    threat_level: str = "medium"
    scope: str = "all"
    tenant_id: uuid.UUID | None = None
    expires_hours: int | None = None
    override_self_block: bool = False


@router.post("/ip-blocklist", response_model=ApiResponse[dict], summary="Create IP block")
async def create_ip_block(r: Request, body: CreateIpBlockBody,
                           u: UserContext = Depends(require_permission(P.SECURITY_IP_BLOCKLIST_CREATE)),
                           s: SecurityAdminService = Depends(_svc)):
    return ok(await s.create_ip_block(body.ip_or_cidr, body.entry_type, body.reason, body.threat_level,
                                       body.scope, body.tenant_id, body.expires_hours,
                                       body.override_self_block), _rid(r), ENGINE_ID)


class UpdateIpBlockBody(BaseModel):
    scope: str | None = None
    threat_level: str | None = None
    reason: str | None = None


@router.patch("/ip-blocklist/{entry_id}", response_model=ApiResponse[dict], summary="Update IP block")
async def update_ip_block(r: Request, entry_id: uuid.UUID, body: UpdateIpBlockBody,
                           u: UserContext = Depends(require_permission(P.SECURITY_IP_BLOCKLIST_UPDATE)),
                           s: SecurityAdminService = Depends(_svc)):
    return ok(await s.update_ip_block(entry_id, **body.model_dump()), _rid(r), ENGINE_ID)


class RevokeIpBlockBody(BaseModel):
    reason: str


@router.post("/ip-blocklist/{entry_id}/revoke", response_model=ApiResponse[dict], summary="Revoke IP block")
async def revoke_ip_block(r: Request, entry_id: uuid.UUID, body: RevokeIpBlockBody,
                           u: UserContext = Depends(require_permission(P.SECURITY_IP_BLOCKLIST_REVOKE)),
                           s: SecurityAdminService = Depends(_svc)):
    return ok(await s.revoke_ip_block(entry_id, body.reason), _rid(r), ENGINE_ID)


@router.get("/ip-blocklist/{entry_id}/hits", response_model=ApiResponse[dict], summary="Get IP block hits")
async def ip_block_hits(r: Request, entry_id: uuid.UUID,
                         u: UserContext = Depends(require_permission(P.SECURITY_IP_BLOCKLIST_READ)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_ip_block_hits(entry_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════════

@router.get("/api-keys", response_model=ApiResponse[dict], summary="List API keys")
async def list_api_keys(r: Request,
                         tenant_id: uuid.UUID | None = Query(None), status: str | None = Query(None),
                         q: str | None = Query(None),
                         limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None),
                         u: UserContext = Depends(require_permission(P.SECURITY_API_KEYS_READ)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.list_api_keys(tenant_id, status, q, limit, cursor), _rid(r), ENGINE_ID)


class CreateApiKeyBody(BaseModel):
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    scopes: list[str]
    environment: str = "live"
    expires_days: int | None = None
    owner_type: str = "tenant"
    allowed_ips: list[str] | None = None
    rate_limit_per_minute: int | None = None
    permissions: list[str] | None = None


@router.post("/api-keys", response_model=ApiResponse[dict], summary="Create API key")
async def create_api_key(r: Request, body: CreateApiKeyBody,
                          u: UserContext = Depends(require_permission(P.SECURITY_API_KEYS_CREATE)),
                          s: SecurityAdminService = Depends(_svc)):
    return ok(await s.create_api_key(body.tenant_id, body.name, body.description, body.scopes,
                                      body.environment, body.expires_days, body.owner_type,
                                      body.allowed_ips, body.rate_limit_per_minute,
                                      body.permissions), _rid(r), ENGINE_ID)


@router.get("/api-keys/{key_id}", response_model=ApiResponse[dict], summary="Get API key detail")
async def api_key_detail(r: Request, key_id: uuid.UUID,
                          u: UserContext = Depends(require_permission(P.SECURITY_API_KEYS_READ)),
                          s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_api_key_detail(key_id), _rid(r), ENGINE_ID)


class RotateApiKeyBody(BaseModel):
    tenant_id: uuid.UUID


@router.post("/api-keys/{key_id}/rotate", response_model=ApiResponse[dict], summary="Rotate API key")
async def rotate_api_key(r: Request, key_id: uuid.UUID, body: RotateApiKeyBody,
                          u: UserContext = Depends(require_permission(P.SECURITY_API_KEYS_ROTATE)),
                          s: SecurityAdminService = Depends(_svc)):
    return ok(await s.rotate_api_key(key_id, body.tenant_id), _rid(r), ENGINE_ID)


class RevokeApiKeyBody(BaseModel):
    tenant_id: uuid.UUID
    reason: str


@router.post("/api-keys/{key_id}/revoke", response_model=ApiResponse[dict], summary="Revoke API key")
async def revoke_api_key(r: Request, key_id: uuid.UUID, body: RevokeApiKeyBody,
                          u: UserContext = Depends(require_permission(P.SECURITY_API_KEYS_REVOKE)),
                          s: SecurityAdminService = Depends(_svc)):
    return ok(await s.revoke_api_key(key_id, body.tenant_id, body.reason), _rid(r), ENGINE_ID)


@router.get("/api-keys/{key_id}/usage", response_model=ApiResponse[dict], summary="Get API key usage")
async def api_key_usage(r: Request, key_id: uuid.UUID,
                         u: UserContext = Depends(require_permission(P.SECURITY_API_KEYS_READ)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_api_key_usage(key_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════════════════════

@router.get("/audit-logs", response_model=ApiResponse[dict], summary="List platform audit logs")
async def list_audit_logs(r: Request,
                           engine_id: str | None = Query(None), operation: str | None = Query(None),
                           actor_role: str | None = Query(None), tenant_id: uuid.UUID | None = Query(None),
                           is_high_risk: bool | None = Query(None), q: str | None = Query(None),
                           date_from: datetime | None = Query(None), date_to: datetime | None = Query(None),
                           limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None),
                           u: UserContext = Depends(require_permission(P.SECURITY_AUDIT_READ)),
                           s: SecurityAdminService = Depends(_svc)):
    return ok(await s.list_audit_logs(engine_id, operation, actor_role, tenant_id, is_high_risk, q,
                                       date_from, date_to, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/audit-logs/{log_id}", response_model=ApiResponse[dict], summary="Get audit log detail")
async def audit_log_detail(r: Request, log_id: uuid.UUID,
                            u: UserContext = Depends(require_permission(P.SECURITY_AUDIT_READ)),
                            s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_audit_log_detail(log_id), _rid(r), ENGINE_ID)


@router.get("/audit-logs-export", summary="Export audit logs as CSV")
async def export_audit_logs(r: Request,
                             engine_id: str | None = Query(None), operation: str | None = Query(None),
                             date_from: datetime | None = Query(None), date_to: datetime | None = Query(None),
                             u: UserContext = Depends(require_permission(P.SECURITY_AUDIT_EXPORT)),
                             s: SecurityAdminService = Depends(_svc)):
    csv_data = await s.export_audit_logs(engine_id, operation, date_from, date_to)
    return Response(content=csv_data, media_type="text/csv",
                     headers={"Content-Disposition": "attachment; filename=security_audit_log.csv"})


# ═══════════════════════════════════════════════════════════════
# SECURITY POLICIES
# ═══════════════════════════════════════════════════════════════

@router.get("/policies", response_model=ApiResponse[dict], summary="Get security policies")
async def get_policies(r: Request,
                        u: UserContext = Depends(require_permission(P.SECURITY_POLICIES_READ)),
                        s: SecurityAdminService = Depends(_svc)):
    return ok(await s.get_policies(), _rid(r), ENGINE_ID)


class UpdatePolicyBody(BaseModel):
    value: object
    reason: str


@router.patch("/policies/{policy_key}", response_model=ApiResponse[dict], summary="Update a security policy")
async def update_policy(r: Request, policy_key: str, body: UpdatePolicyBody,
                         u: UserContext = Depends(require_permission(P.SECURITY_POLICIES_UPDATE)),
                         s: SecurityAdminService = Depends(_svc)):
    return ok(await s.update_policy(policy_key, body.value, body.reason), _rid(r), ENGINE_ID)
