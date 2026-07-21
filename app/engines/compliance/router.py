"""Compliance Engine — Router (18 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_mutation_access_scope
from app.core.security import get_client_ip
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.compliance.service import ComplianceService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("compliance.router")
router = APIRouter(prefix="/v1/compliance", tags=["Compliance Engine"])
ENGINE_ID = "compliance"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> ComplianceService:
    return ComplianceService(db=db, request_id=getattr(r.state,"request_id","—"),
                              actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                              actor_role=u.role, actor_ip=get_client_ip(r))
def _rid(r): return getattr(r.state,"request_id","—")


@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Compliance Engine",
            "version": "13.0.0", "endpoint_count": 18, "status": "active",
            "capabilities": [
                "immutable_consent_ledger",
                "72h_sla_erasure_dpdp_2023",
                "per_row_exemption_reasons",
                "financial_records_never_erased",
                "idempotent_portability_export",
                "append_only_audit_log",
                "redis_consent_cache",
                "right_to_access_data",
            ]}


# ── Consent Management (4 endpoints) ─────────────────────────────────────────
@router.post("/consent",
             summary="Record consent — INSERT only, immutable ledger",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def record_consent(r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    # Slice 2F-39A3 fix: same self-service ownership gap Slice 2F-37 fixed
    # for request_deletion/request_export in this same file -- user_id was
    # fully client-supplied with no comparison to the caller's own
    # identity, letting any authenticated user record consent on another
    # user's behalf. Self-service only, except super_admin.
    requested_user_id = uuid.UUID(body["user_id"])
    if u.role != "super_admin" and str(requested_user_id) != str(u.user_id):
        raise ServiceOSException("PERMISSION_DENIED",
            "You can only record consent for your own account.",
            blocking_rule="compliance_consent_self_only")
    return ok(await s.record_consent(
        requested_user_id,
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body["consent_type"], body["action"],
        body.get("policy_version", "1.0"),
        body.get("source", "api")), _rid(r), ENGINE_ID)


@router.get("/consent/users/{user_id}/check",
            summary="Check consent status — Redis cache first, DB fallback",
            response_model=ApiResponse[dict])
async def check_consent(user_id: uuid.UUID, r: Request,
                         consent_type: str = Query(...),
                         u: UserContext = Depends(get_current_user),
                         s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.check_consent(user_id, consent_type), _rid(r), ENGINE_ID)


@router.get("/consent/users/{user_id}",
            summary="List full consent history — immutable ledger",
            response_model=ApiResponse[dict])
async def list_consents(user_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_user_consents(user_id), _rid(r), ENGINE_ID)


@router.post("/consent/withdraw",
             summary="Withdraw consent — records new WITHDRAWN event in ledger",
             response_model=ApiResponse[dict])
async def withdraw_consent(r: Request,
                            u: UserContext = Depends(get_current_user),
                            s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    # Slice 2F-39A3 fix: same self-service ownership gap as record_consent
    # above (already independently observed and recorded, unremediated,
    # since Slice 2F-26D/F/G/H's security-observations-not-remediated.md:
    # "withdraw another user's consent").
    requested_user_id = uuid.UUID(body["user_id"])
    if u.role != "super_admin" and str(requested_user_id) != str(u.user_id):
        raise ServiceOSException("PERMISSION_DENIED",
            "You can only withdraw consent for your own account.",
            blocking_rule="compliance_consent_withdraw_self_only")
    return ok(await s.withdraw_consent(
        requested_user_id,
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body["consent_type"],
        body.get("policy_version", "1.0")), _rid(r), ENGINE_ID)


# ── Right to Erasure (5 endpoints) ───────────────────────────────────────────
@router.post("/deletion-requests",
             summary="Request data erasure — 72h SLA stored at creation (DPDP Act 2023)",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def request_deletion(r: Request,
                            u: UserContext = Depends(require_mutation_access_scope),
                            s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    # Slice 2F-37: user_id was fully client-supplied with no comparison to
    # the caller's own identity, letting any authenticated user request
    # erasure of another user's data. Self-service only, except
    # super_admin (administrative/on-behalf-of processing).
    requested_user_id = uuid.UUID(body["user_id"])
    if u.role != "super_admin" and str(requested_user_id) != str(u.user_id):
        raise ServiceOSException("PERMISSION_DENIED",
            "You can only request erasure of your own data.",
            blocking_rule="compliance_deletion_self_only")
    return ok(await s.request_deletion(
        requested_user_id,
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body.get("request_reason")), _rid(r), ENGINE_ID)


@router.get("/deletion-requests/{request_id}",
            summary="Get deletion request status with SLA countdown",
            response_model=ApiResponse[dict])
async def get_deletion_request(request_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(get_current_user),
                                s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_deletion_request(request_id), _rid(r), ENGINE_ID)


@router.get("/deletion-requests",
            summary="List deletion requests with status filter",
            response_model=ApiResponse[dict])
async def list_deletion_requests(r: Request,
                                  user_id: uuid.UUID | None = Query(None),
                                  dlv_status: str | None = Query(None, alias="status"),
                                  limit: int = Query(50, ge=1, le=200),
                                  cursor: str | None = Query(None),
                                  u: UserContext = Depends(require_super_admin),
                                  s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_deletion_requests(user_id, dlv_status, limit, cursor),
              _rid(r), ENGINE_ID)


@router.post("/deletion-requests/{request_id}/process",
             summary="Process erasure — anonymises PII, exempts financial records with reason",
             response_model=ApiResponse[dict])
async def process_deletion(request_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.process_deletion(request_id), _rid(r), ENGINE_ID)


@router.get("/retention-policies",
            summary="Get data retention policies and exempt tables",
            response_model=ApiResponse[dict])
async def get_retention_policies(r: Request,
                                  tenant_id: uuid.UUID | None = Query(None),
                                  u: UserContext = Depends(require_super_admin),
                                  s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_retention_policies(tenant_id), _rid(r), ENGINE_ID)


# ── Data Portability (4 endpoints) ───────────────────────────────────────────
@router.post("/portability-requests",
             summary="Request data export — idempotent, 72h SLA, JSON or CSV",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def request_export(r: Request,
                          u: UserContext = Depends(require_mutation_access_scope),
                          s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    # Slice 2F-37: same self-service ownership fix as request_deletion.
    requested_user_id = uuid.UUID(body["user_id"])
    if u.role != "super_admin" and str(requested_user_id) != str(u.user_id):
        raise ServiceOSException("PERMISSION_DENIED",
            "You can only request an export of your own data.",
            blocking_rule="compliance_export_self_only")
    return ok(await s.request_export(
        requested_user_id,
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body.get("data_categories", []),
        body.get("export_format", "json")), _rid(r), ENGINE_ID)


@router.get("/portability-requests/{request_id}",
            summary="Get export status with download URL when ready",
            response_model=ApiResponse[dict])
async def get_export_status(request_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(get_current_user),
                             s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_export_status(request_id), _rid(r), ENGINE_ID)


@router.post("/portability-requests/{request_id}/process",
             summary="[Admin/Celery] Process export — collect data from all engines",
             response_model=ApiResponse[dict])
async def process_export(request_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.process_export(request_id), _rid(r), ENGINE_ID)


@router.put("/retention-policies",
            summary="Set data retention policy for a table",
            response_model=ApiResponse[dict])
async def set_retention_policy(r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_retention_policy(
        body["table_name"],
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body["retention_days"], body.get("legal_basis")), _rid(r), ENGINE_ID)


# ── Compliance Audit Log (2 endpoints) ───────────────────────────────────────
@router.get("/audit-log",
            summary="Compliance data-access audit log — append-only, immutable",
            response_model=ApiResponse[dict])
async def compliance_audit(r: Request,
                            user_id: uuid.UUID | None = Query(None),
                            action: str | None = Query(None),
                            limit: int = Query(50, ge=1, le=200),
                            cursor: str | None = Query(None),
                            u: UserContext = Depends(require_super_admin),
                            s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.search_compliance_audit(user_id, action, limit, cursor),
              _rid(r), ENGINE_ID)


# ── Compliance Summary (1 endpoint) ──────────────────────────────────────────
@router.get("/summary",
            summary="Compliance dashboard — SLA status, pending requests, consent counts",
            response_model=ApiResponse[dict])
async def compliance_summary(r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: ComplianceService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_compliance_summary(), _rid(r), ENGINE_ID)
