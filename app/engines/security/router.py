"""Security Engine — Router (21 endpoints). Zero inline imports. Zero business logic."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.core.security import get_client_ip
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.security.service import SecurityService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("security.router")
router = APIRouter(prefix="/v1/security", tags=["Security Engine"])
ENGINE_ID = "security"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> SecurityService:
    # Phase 2A Slice 2F-35: actor_tenant_id is now passed so SecurityService
    # can independently enforce tenant authority on rotate_api_key/
    # revoke_api_key, rather than trusting a client-supplied tenant_id.
    return SecurityService(db=db, request_id=getattr(r.state, "request_id", "—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                            actor_role=u.role, actor_ip=get_client_ip(r),
                            actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {
        "engine_id": ENGINE_ID, "name": "Security Engine", "version": "12.0.0",
        "endpoint_count": 21, "status": "active",
        "capabilities": [
            "api_key_hmac_hash_only",
            "ip_blocklist_redis_o1_lookup",
            "sliding_window_threat_detection",
            "append_only_audit_log",
            "atomic_session_force_logout",
            "api_key_rotation_atomic",
            "plaintext_never_stored",
        ],
    }


# ── API Key Management (6 endpoints) ─────────────────────────────────────────
@router.post("/api-keys",
             summary="Create API key — raw key returned ONCE, only hash stored in DB",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_api_key(r: Request,
                          u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                          s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_api_key(
        uuid.UUID(body["tenant_id"]), body["name"],
        body.get("description"), body.get("scopes", []),
        body.get("environment", "live"), body.get("expires_days")),
        _rid(r), ENGINE_ID)


@router.get("/api-keys/tenants/{tenant_id}",
            summary="List API keys — prefix shown, full key never retrievable",
            response_model=ApiResponse[dict])
async def list_api_keys(tenant_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                         s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_api_keys(tenant_id), _rid(r), ENGINE_ID)


@router.get("/api-keys/{key_id}",
            summary="Get API key metadata — full key cannot be retrieved",
            response_model=ApiResponse[dict])
async def get_api_key(key_id: uuid.UUID, r: Request,
                       tenant_id: uuid.UUID = Query(...),
                       u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                       s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_api_key(key_id, tenant_id), _rid(r), ENGINE_ID)


@router.post("/api-keys/verify",
             summary="Verify API key — HMAC hash comparison, Redis cache",
             response_model=ApiResponse[dict])
async def verify_api_key(r: Request,
                          db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    body = await r.json()
    svc = SecurityService(db=db, actor_ip=get_client_ip(r))
    return ok(await svc.verify_api_key(body["api_key"]), _rid(r), ENGINE_ID)


@router.post("/api-keys/{key_id}/rotate",
             summary="Rotate API key — old marked ROTATED, new issued atomically",
             response_model=ApiResponse[dict])
async def rotate_api_key(key_id: uuid.UUID, r: Request,
                          tenant_id: uuid.UUID = Query(...),
                          u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                          s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.rotate_api_key(key_id, tenant_id), _rid(r), ENGINE_ID)


@router.post("/api-keys/{key_id}/revoke",
             summary="Revoke API key — Redis cache invalidated immediately",
             response_model=ApiResponse[dict])
async def revoke_api_key(key_id: uuid.UUID, r: Request,
                          tenant_id: uuid.UUID = Query(...),
                          u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                          s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.revoke_api_key(key_id, tenant_id,
              body.get("reason", "Revoked by owner")), _rid(r), ENGINE_ID)


# ── IP Blocklist (4 endpoints) ────────────────────────────────────────────────
@router.post("/blocklist",
             summary="Block IP or CIDR — DB write first, then Redis SET sync",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def block_ip(r: Request,
                    u: UserContext = Depends(require_super_admin),
                    s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.block_ip(
        body["ip_or_cidr"], body.get("entry_type", "ip"),
        body["reason"], body.get("threat_level", "medium"),
        body.get("is_global", False),
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body.get("expires_hours")), _rid(r), ENGINE_ID)


@router.delete("/blocklist/{ip_or_cidr}",
               summary="Unblock IP — Redis SREM then DB deactivate",
               response_model=ApiResponse[dict])
async def unblock_ip(ip_or_cidr: str, r: Request,
                      u: UserContext = Depends(require_super_admin),
                      s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.unblock_ip(ip_or_cidr, None), _rid(r), ENGINE_ID)


@router.get("/blocklist/check",
            summary="Check if IP is blocked — Redis O(1) SISMEMBER, no DB query",
            response_model=ApiResponse[dict])
async def check_ip(r: Request, ip: str = Query(...),
                    u: UserContext = Depends(get_current_user),
                    s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.check_ip(ip), _rid(r), ENGINE_ID)


@router.get("/blocklist",
            summary="List all blocked IPs with cursor pagination",
            response_model=ApiResponse[dict])
async def list_blocklist(r: Request,
                          tenant_id: uuid.UUID | None = Query(None),
                          limit: int = Query(50, ge=1, le=200),
                          cursor: str | None = Query(None),
                          u: UserContext = Depends(require_super_admin),
                          s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_blocklist(tenant_id, limit, cursor), _rid(r), ENGINE_ID)


# ── Suspicious Activity (3 endpoints) ────────────────────────────────────────
@router.post("/activity/record",
             summary="Record activity event — Lua sliding window counter",
             response_model=ApiResponse[dict])
async def record_activity(r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.record_activity(
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body["entity_id"], body.get("entity_type", "user"),
        body["activity_type"], get_client_ip(r)), _rid(r), ENGINE_ID)


@router.get("/activity",
            summary="List suspicious activity with threat level filter",
            response_model=ApiResponse[dict])
async def list_activity(r: Request,
                         tenant_id: uuid.UUID | None = Query(None),
                         threat_level: str | None = Query(None),
                         act_status: str | None = Query(None, alias="status"),
                         limit: int = Query(50, ge=1, le=200),
                         cursor: str | None = Query(None),
                         u: UserContext = Depends(require_super_admin),
                         s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_suspicious_activity(tenant_id, threat_level,
              act_status, limit, cursor), _rid(r), ENGINE_ID)


@router.post("/activity/{log_id}/acknowledge",
             summary="Acknowledge threat — marks as reviewed by security team",
             response_model=ApiResponse[dict])
async def acknowledge_activity(log_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.acknowledge_activity(log_id, body.get("notes")), _rid(r), ENGINE_ID)


# ── Platform Audit Log (2 endpoints) ─────────────────────────────────────────
@router.post("/audit-log",
             summary="Write audit entry — append-only, called by other engines",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def write_audit(r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.write_audit_entry(
        body["operation"], body["engine_id"], body["entity_id"],
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body.get("entity_type"), body.get("before"), body.get("after")),
        _rid(r), ENGINE_ID)


@router.get("/audit-log",
            summary="Search audit log — append-only, immutable records",
            response_model=ApiResponse[dict])
async def search_audit(r: Request,
                        actor_id: uuid.UUID | None = Query(None),
                        tenant_id: uuid.UUID | None = Query(None),
                        operation: str | None = Query(None),
                        engine_id: str | None = Query(None),
                        high_risk_only: bool | None = Query(None),
                        limit: int = Query(50, ge=1, le=200),
                        cursor: str | None = Query(None),
                        u: UserContext = Depends(require_super_admin),
                        s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.search_audit_log(actor_id, tenant_id, operation, engine_id,
              high_risk_only, limit, cursor), _rid(r), ENGINE_ID)


# ── Session Management (4 endpoints) ─────────────────────────────────────────
@router.post("/sessions",
             summary="Register session — Redis primary, DB audit record",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_session(r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_session(
        uuid.UUID(body["user_id"]),
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body["session_id"], body.get("device_info", {}),
        get_client_ip(r), r.headers.get("User-Agent"),
        body.get("ttl_seconds", 3600)), _rid(r), ENGINE_ID)


@router.get("/sessions/users/{user_id}",
            summary="List active sessions for a user across all devices",
            response_model=ApiResponse[dict])
async def list_sessions(user_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_user_sessions(user_id), _rid(r), ENGINE_ID)


@router.post("/sessions/{session_id}/revoke",
             summary="Revoke session — Redis DELETE first, then DB update",
             response_model=ApiResponse[dict])
async def revoke_session(session_id: str, r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.revoke_session(session_id,
              body.get("reason", "User requested logout")), _rid(r), ENGINE_ID)


@router.post("/sessions/users/{user_id}/revoke-all",
             summary="Force logout all devices — Redis cleared atomically first",
             response_model=ApiResponse[dict])
async def revoke_all_sessions(user_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.revoke_all_sessions(user_id,
              body.get("reason", "Admin forced logout")), _rid(r), ENGINE_ID)


# ── Summary (1 endpoint) ──────────────────────────────────────────────────────
@router.get("/summary",
            summary="Security dashboard — API keys, blocked IPs, threats, sessions",
            response_model=ApiResponse[dict])
async def security_summary(r: Request,
                            tenant_id: uuid.UUID | None = Query(None),
                            u: UserContext = Depends(require_super_admin),
                            s: SecurityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_security_summary(tenant_id), _rid(r), ENGINE_ID)
