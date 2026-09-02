"""Compliance Admin Router — Enterprise DPDP Act 2023 governance.

All endpoints require super_admin authentication.
Prefix: /v1/admin/compliance
"""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_client_ip
from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.compliance.enterprise_service import ComplianceEnterpriseService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("compliance.admin_router")
router = APIRouter(prefix="/v1/admin/compliance", tags=["Compliance Admin"])


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_super_admin)) -> ComplianceEnterpriseService:
    return ComplianceEnterpriseService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, actor_ip=get_client_ip(r))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Summary / Overview ────────────────────────────────────────────────────────

@router.get("/summary",
            summary="Enterprise compliance summary — 10 dashboard cards",
            response_model=ApiResponse[dict])
async def get_summary(r: Request,
    u: UserContext = Depends(require_super_admin),
                      s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_enterprise_summary(), _rid(r), "compliance_admin")


@router.get("/overview",
            summary="Alias for summary — compliance overview",
            response_model=ApiResponse[dict])
async def get_overview(r: Request,
    u: UserContext = Depends(require_super_admin),
                       s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_enterprise_summary(), _rid(r), "compliance_admin")


# ── SLA Monitor ───────────────────────────────────────────────────────────────

@router.post("/sla/refresh",
             summary="Refresh SLA statuses on all open requests",
             response_model=ApiResponse[dict])
async def refresh_sla(r: Request,
    u: UserContext = Depends(require_super_admin),
                      s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.refresh_sla_statuses(), _rid(r), "compliance_admin")


# ── Request Management ────────────────────────────────────────────────────────

@router.get("/requests",
            summary="List enterprise compliance requests with filters",
            response_model=ApiResponse[dict])
async def list_requests(
        r: Request,
        request_type: str | None = Query(None),
        req_status: str | None = Query(None, alias="status"),
        sla_status: str | None = Query(None),
        subject_type: str | None = Query(None),
        verification_status: str | None = Query(None),
        search: str | None = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_requests(
        request_type=request_type, status=req_status, sla_status=sla_status,
        subject_type=subject_type, verification_status=verification_status,
        search=search, page=page, limit=limit), _rid(r), "compliance_admin")


@router.post("/requests",
             summary="Admin creates a compliance request on behalf of a data subject",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_request(r: Request,
    u: UserContext = Depends(require_super_admin),
                         s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_request(body), _rid(r), "compliance_admin")


@router.get("/requests/{request_id}",
            summary="Get enterprise request detail with items and audit trail",
            response_model=ApiResponse[dict])
async def get_request(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                      s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_request(request_id), _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/verify-identity",
             summary="Mark identity as verified for this request",
             response_model=ApiResponse[dict])
async def verify_identity(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                          s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.verify_identity(request_id, body.get("notes")), _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/scan-data",
             summary="Scan data modules and create request inventory items",
             response_model=ApiResponse[dict])
async def scan_data(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                    s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.scan_data(request_id), _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/approve",
             summary="Approve (or partially approve) a compliance request",
             response_model=ApiResponse[dict])
async def approve_request(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                          s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.approve_request(request_id, body.get("notes")), _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/reject",
             summary="Reject a compliance request — rejection reason required",
             response_model=ApiResponse[dict])
async def reject_request(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                         s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_request(request_id, body.get("reason", "")),
              _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/apply-exemption",
             summary="Apply a legal/statutory exemption to a specific request item",
             response_model=ApiResponse[dict])
async def apply_exemption(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                          s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.apply_exemption(
        request_id, uuid.UUID(str(body["item_id"])), body.get("exemption_reason", "")),
        _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/process",
             summary="Execute the approved compliance request",
             response_model=ApiResponse[dict])
async def process_request(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                          s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.process_request(request_id), _rid(r), "compliance_admin")


@router.get("/requests/{request_id}/audit",
            summary="Audit trail for a specific compliance request",
            response_model=ApiResponse[dict])
async def get_request_audit(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                            s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_request_audit(request_id), _rid(r), "compliance_admin")


# ── Consent Registry ──────────────────────────────────────────────────────────

@router.get("/consents",
            summary="List all consent records across all subjects",
            response_model=ApiResponse[dict])
async def list_consents(
        r: Request,
        subject_id: uuid.UUID | None = Query(None),
        consent_type: str | None = Query(None),
        action: str | None = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_consent_records(
        subject_id=subject_id, consent_type=consent_type,
        action=action, page=page, limit=limit), _rid(r), "compliance_admin")


@router.post("/consents/{user_id}/revoke",
             summary="Admin revoke / withdraw consent for a user + type",
             response_model=ApiResponse[dict])
async def revoke_consent(user_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                         s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.revoke_consent(
        user_id, body["consent_type"], body.get("notes")), _rid(r), "compliance_admin")


# ── Exports ───────────────────────────────────────────────────────────────────

@router.get("/exports",
            summary="List all compliance data exports",
            response_model=ApiResponse[dict])
async def list_exports(
        r: Request,
        req_status: str | None = Query(None, alias="status"),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_exports(status=req_status, page=page, limit=limit),
              _rid(r), "compliance_admin")


@router.get("/exports/{export_id}",
            summary="Get export detail",
            response_model=ApiResponse[dict])
async def get_export(export_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                     s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_export(export_id), _rid(r), "compliance_admin")


@router.post("/exports/{export_id}/expire",
             summary="Manually expire an export file",
             response_model=ApiResponse[dict])
async def expire_export(export_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.expire_export(export_id), _rid(r), "compliance_admin")


# ── Retention Policies ────────────────────────────────────────────────────────

@router.get("/retention-policies",
            summary="List all data retention policies",
            response_model=ApiResponse[dict])
async def list_retention(r: Request,
    u: UserContext = Depends(require_super_admin),
                         s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_retention_policies(), _rid(r), "compliance_admin")


@router.post("/retention-policies",
             summary="Create or update a retention policy",
             response_model=ApiResponse[dict])
async def create_retention(r: Request,
    u: UserContext = Depends(require_super_admin),
                           s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_retention_policy(body), _rid(r), "compliance_admin")


@router.put("/retention-policies/{table_name}",
            summary="Update retention policy for a specific table",
            response_model=ApiResponse[dict])
async def update_retention(table_name: str, r: Request,
    u: UserContext = Depends(require_super_admin),
                           s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_retention_policy(table_name, body), _rid(r), "compliance_admin")


# ── Audit Trail ───────────────────────────────────────────────────────────────

@router.get("/audit-trail",
            summary="Platform-wide compliance audit trail",
            response_model=ApiResponse[dict])
async def audit_trail(
        r: Request,
        user_id: uuid.UUID | None = Query(None),
        action: str | None = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(100, ge=1, le=500),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_audit_logs(
        user_id=user_id, action=action, page=page, limit=limit),
        _rid(r), "compliance_admin")


# ── SLA Job Triggers ──────────────────────────────────────────────────────────

@router.post("/jobs/run",
             summary="Manually trigger compliance SLA job (sla_check + expire_exports)",
             response_model=ApiResponse[dict])
async def run_compliance_jobs(r: Request,
                              u: UserContext = Depends(require_super_admin)) -> ApiResponse[dict]:
    """Triggers run_all() immediately. Safe to call repeatedly (idempotent)."""
    from app.jobs.compliance_sla import run_all
    result = await run_all(
        trigger="manual",
        triggered_by_user_id=uuid.UUID(u.user_id),
    )
    return ok(result, _rid(r), "compliance_admin")


@router.post("/jobs/run-sla",
             summary="Manually trigger SLA check only",
             response_model=ApiResponse[dict])
async def run_sla_check_only(r: Request,
                              u = Depends(require_super_admin)) -> ApiResponse[dict]:
    from app.jobs.compliance_sla import run_sla_check
    result = await run_sla_check()
    return ok(result, _rid(r), "compliance_admin")


@router.post("/jobs/run-expire-exports",
             summary="Manually trigger export expiry only",
             response_model=ApiResponse[dict])
async def run_expire_exports_only(r: Request,
                                   u = Depends(require_super_admin)) -> ApiResponse[dict]:
    from app.jobs.compliance_sla import run_expire_exports
    result = await run_expire_exports()
    return ok(result, _rid(r), "compliance_admin")


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/dpdp/policies",
            summary="List published DPDP policy versions",
            response_model=ApiResponse[dict])
async def list_dpdp_policies(
        r: Request,
        u: UserContext = Depends(require_super_admin),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_dpdp_policy_versions(), _rid(r), "compliance_admin")


@router.get("/dpdp/scheduler-status",
            summary="Authoritative status of the DPDP SLA evaluator",
            response_model=ApiResponse[dict])
async def dpdp_scheduler_status(
        r: Request,
        u: UserContext = Depends(require_super_admin),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_dpdp_scheduler_status(), _rid(r), "compliance_admin")


@router.get("/dpdp/health",
            summary="Compliance health score with top risks and recommendations",
            response_model=ApiResponse[dict])
async def get_health(r: Request, s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_health(), _rid(r), "compliance_admin")


# ── Action Queue ───────────────────────────────────────────────────────────────

@router.get("/dpdp/action-queue",
            summary="Pending compliance action queue, prioritized by SLA risk",
            response_model=ApiResponse[dict])
async def get_action_queue(r: Request, limit: int = Query(50, le=500),
    u: UserContext = Depends(require_super_admin),
                            s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_action_queue(limit), _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/assign",
             summary="Assign a compliance request to an admin owner",
             response_model=ApiResponse[dict])
async def assign_request(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                         s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.assign_action(request_id, uuid.UUID(str(body["assigned_to_user_id"]))),
              _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/escalate",
             summary="Escalate a compliance request to critical priority",
             response_model=ApiResponse[dict])
async def escalate_request(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                           s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.escalate_action(request_id, body.get("reason", "")), _rid(r), "compliance_admin")


# ── Affected Data Map ──────────────────────────────────────────────────────────

@router.get("/requests/{request_id}/data-map",
            summary="Affected data map for a compliance request",
            response_model=ApiResponse[dict])
async def get_data_map(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                       s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_data_map(request_id), _rid(r), "compliance_admin")


@router.post("/requests/{request_id}/refresh-data-map",
             summary="Re-scan and refresh the affected data map",
             response_model=ApiResponse[dict])
async def refresh_data_map(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                           s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    await s.scan_data(request_id)
    return ok(await s.get_data_map(request_id), _rid(r), "compliance_admin")


# ── Legal Holds / Exemptions ───────────────────────────────────────────────────

@router.get("/dpdp/legal-holds",
            summary="List legal holds",
            response_model=ApiResponse[dict])
async def list_legal_holds(r: Request, hold_status: str | None = Query(None, alias="status"),
                            page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
                            s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_legal_holds(status=hold_status, page=page, limit=limit),
              _rid(r), "compliance_admin")


@router.post("/dpdp/legal-holds",
             summary="Apply a legal hold to a data subject — blocks erasure",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def apply_legal_hold(r: Request,
    u: UserContext = Depends(require_super_admin),
                           s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.apply_legal_hold(body), _rid(r), "compliance_admin")


@router.post("/dpdp/legal-holds/{hold_id}/release",
             summary="Release a legal hold — reason required",
             response_model=ApiResponse[dict])
async def release_legal_hold(hold_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                             s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.release_legal_hold(hold_id, body.get("reason", "")),
              _rid(r), "compliance_admin")


# ── Evidence Packs ─────────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/generate-evidence-pack",
             summary="Generate a full evidence/audit package for a request",
             response_model=ApiResponse[dict])
async def generate_evidence_pack(request_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin),
                                 s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.generate_evidence_pack(request_id), _rid(r), "compliance_admin")


@router.get("/dpdp/evidence-packs",
            summary="List generated evidence packs",
            response_model=ApiResponse[dict])
async def list_evidence_packs(r: Request, request_id: uuid.UUID | None = Query(None),
                               page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
                               s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_evidence_packs(request_id=request_id, page=page, limit=limit),
              _rid(r), "compliance_admin")
