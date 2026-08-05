"""Technician Mobile App Phase X — Privacy & Data.

Extends the SAME canonical global DPDP/compliance system used by
provider_router.py (tenant) and customer_router.py (customer) -- never a
second privacy engine. Confirmed by audit: `ComplianceRequest.subject_type`
already includes "tenant_staff" in `VALID_SUBJECT_TYPES`, and
`TENANT_STAFF_SUBJECT_TYPES` already lets a tenant owner view/respond to
staff-subject requests (provider_router.py's `/staff-requests/*`) -- but no
route ever let a technician CREATE a request about themselves. This file is
that missing self-service entry point, reusing `ComplianceEnterpriseService`,
`ComplianceRequest`/`ComplianceExport`/`ComplianceAuditLog`, and the base
service's `record_consent`/`withdraw_consent` exactly as-is.

Requests created here use subject_type="tenant_staff" (not "technician" --
confirmed by audit that literal value is NOT in VALID_SUBJECT_TYPES) with
subject_id=the technician's own user_id, and metadata_json.tenant_id set so
the EXISTING tenant staff-requests endpoints immediately see them -- no
parallel visibility system.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_client_ip
from app.dependencies.auth import UserContext, require_technician
from app.dependencies.db import get_db
from app.engines.compliance.enterprise_service import ComplianceEnterpriseService
from app.engines.compliance.models import ComplianceRequest, ComplianceAuditLog, ComplianceExport, ConsentRecord
from app.engines.compliance.constants import ConsentType, ConsentAction
from app.models.base import utcnow
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException

logger = structlog.get_logger("compliance.technician_router")
router = APIRouter(prefix="/v1/me/privacy", tags=["Technician Privacy & Data"])

SUBJECT_TYPE = "tenant_staff"

# Real, already-validated request types from enterprise_service.VALID_REQUEST_TYPES
# (staff_data_export/staff_data_erasure were added there specifically for this
# staff-subject use case, per that module's own Slice 2F-20 comment -- reused,
# not invented). "Account closure" in the UI maps to staff_data_erasure: closing
# a personal ServiceOS account IS an erasure request for this subject, and
# reuses the exact same erasure-safety pipeline (legal hold, active jobs,
# retention checks) rather than a separate destructive action.
TECHNICIAN_ALLOWED_REQUEST_TYPES = {
    "data_correction", "consent_withdrawal", "processing_objection",
    "grievance", "staff_data_export", "staff_data_erasure",
}
ACCOUNT_CLOSURE_REQUEST_TYPE = "staff_data_erasure"
EXPORT_REQUEST_TYPES = {"staff_data_export"}

OPEN_STATUSES = {"submitted", "identity_verification_pending", "under_review", "approved", "processing"}

STATUS_LABELS = {
    "submitted": "Submitted", "identity_verification_pending": "Identity Verification Required",
    "under_review": "Under Review", "approved": "Approved", "partially_approved": "Partially Approved",
    "rejected": "Rejected", "processing": "Processing", "completed": "Completed",
    "failed": "Needs Attention", "cancelled": "Cancelled", "sla_breached": "Delayed",
}

# Purpose -> real ConsentType. "service_communications" has no consent_type at
# all -- it is required processing (auth, job assignment, security alerts),
# never a withdrawable row, shown locked rather than as a fake toggle.
CONSENT_PURPOSES = [
    {"purpose_code": "service_communications", "label": "Service communications",
     "description": "Required for assigned jobs and account updates", "consent_type": None,
     "required": True, "configurable": False, "default_enabled": True},
    {"purpose_code": "product_improvement", "label": "Product improvement",
     "description": "Share anonymous app diagnostics", "consent_type": ConsentType.ANALYTICS,
     "required": False, "configurable": True, "default_enabled": True},
    {"purpose_code": "optional_updates", "label": "Optional updates",
     "description": "Tips and non-essential announcements", "consent_type": ConsentType.MARKETING,
     "required": False, "configurable": True, "default_enabled": False},
]
# Single, hardcoded policy version -- matches the real backend's own
# `withdraw_consent`/`record_consent` callers elsewhere in this codebase,
# which also pass a fixed "1.0" (confirmed by audit: no live
# DPDPPolicyVersion-driven version-conflict check exists on this path today).
# Disclosed as a genuine PARTIAL for full policy-version-conflict handling.
POLICY_VERSION = "1.0"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_technician)) -> ComplianceEnterpriseService:
    return ComplianceEnterpriseService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, actor_ip=get_client_ip(r))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _safe_request(d: dict) -> dict:
    return {
        "id": d.get("id"), "request_number": d.get("request_number"),
        "request_type": d.get("request_type"), "status": d.get("status"),
        "status_label": STATUS_LABELS.get(d.get("status", ""), d.get("status", "")),
        "sla_status": d.get("sla_status"), "verification_status": d.get("verification_status"),
        "submitted_at": d.get("submitted_at"), "due_at": d.get("due_at"),
        "completed_at": d.get("completed_at"), "reason": d.get("reason"),
        "rejection_reason": d.get("rejection_reason"),
        "created_at": d.get("created_at"), "updated_at": d.get("updated_at"),
    }


def _audit(db: AsyncSession, tenant_id: uuid.UUID | None, actor_id: uuid.UUID,
           actor_role: str, actor_ip: str, action: str,
           reference_id: str | None = None, meta: dict | None = None) -> None:
    db.add(ComplianceAuditLog(
        tenant_id=tenant_id, user_id=actor_id, actor_id=actor_id, actor_role=actor_role,
        actor_ip=actor_ip, action=action, reference_id=reference_id,
        legal_basis="dpdp_act_2023", meta=meta or {},
    ))


@router.get("/summary", summary="Technician personal privacy summary", response_model=ApiResponse[dict])
async def get_summary(r: Request, db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician)) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)

    open_count = await db.scalar(select(func.count()).select_from(ComplianceRequest).where(
        ComplianceRequest.subject_type == SUBJECT_TYPE, ComplianceRequest.subject_id == actor_id,
        ComplianceRequest.status.in_(OPEN_STATUSES)))
    completed_count = await db.scalar(select(func.count()).select_from(ComplianceRequest).where(
        ComplianceRequest.subject_type == SUBJECT_TYPE, ComplianceRequest.subject_id == actor_id,
        ComplianceRequest.status == "completed"))

    recent = await db.scalar(select(ComplianceRequest).where(
        ComplianceRequest.subject_type == SUBJECT_TYPE, ComplianceRequest.subject_id == actor_id,
    ).order_by(ComplianceRequest.created_at.desc()).limit(1))

    if (open_count or 0) > 0:
        status_level, status_label = "request_in_progress", "Request in progress"
    else:
        # "Up to date" is never shown just because nothing is open -- it
        # reflects that no open request needs attention, which IS the real
        # backend fact being checked (spec section 4).
        status_level, status_label = "up_to_date", "Up to date"

    return ok({
        "privacy_status": {"code": status_level, "label": status_label},
        "policy": {"version": POLICY_VERSION, "effective_from": None},
        "request_counts": {"open": open_count or 0, "completed": completed_count or 0},
        "recent_request": _safe_request(recent.to_dict()) if recent else None,
    }, _rid(r), "compliance_technician")


@router.get("/consents", summary="Technician consent choices", response_model=ApiResponse[dict])
async def list_consents(r: Request, db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician)) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    purposes = []
    for p in CONSENT_PURPOSES:
        enabled = p["default_enabled"]
        last_changed_at = None
        if p["consent_type"]:
            latest = await db.scalar(select(ConsentRecord).where(
                ConsentRecord.user_id == actor_id, ConsentRecord.consent_type == p["consent_type"],
            ).order_by(ConsentRecord.created_at.desc()).limit(1))
            if latest:
                enabled = latest.action == ConsentAction.GRANTED
                last_changed_at = latest.created_at.isoformat()
        purposes.append({
            "purpose_code": p["purpose_code"], "label": p["label"], "description": p["description"],
            "legal_or_policy_basis": "contract_or_security" if p["required"] else "consent",
            "required": p["required"], "enabled": enabled, "configurable": p["configurable"],
            "policy_version": POLICY_VERSION, "last_changed_at": last_changed_at,
        })
    return ok({"consents": purposes}, _rid(r), "compliance_technician")


@router.patch("/consents/{purpose_code}", summary="Update an optional consent choice", response_model=ApiResponse[dict])
async def update_consent(
        purpose_code: str, r: Request,
        db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
) -> ApiResponse[dict]:
    purpose = next((p for p in CONSENT_PURPOSES if p["purpose_code"] == purpose_code), None)
    if not purpose:
        raise ServiceOSException("VALIDATION_ERROR", f"Unknown privacy purpose: {purpose_code}")
    if not purpose["configurable"]:
        raise ServiceOSException("MANDATORY_PROCESSING", "This processing is required and cannot be disabled.", status_code=422)

    body = await r.json()
    enabled = bool(body.get("enabled"))
    actor_id = uuid.UUID(u.user_id)
    tenant_id = uuid.UUID(u.tenant_id) if u.tenant_id else None

    action = ConsentAction.GRANTED if enabled else ConsentAction.WITHDRAWN
    svc = ComplianceEnterpriseService(db=db, request_id=_rid(r), actor_id=actor_id, actor_role=u.role, actor_ip=get_client_ip(r))
    # record_consent is an append-only ledger (never UPDATE/DELETE) -- prior
    # consent history is always preserved (spec section 6).
    await svc._base.record_consent(actor_id, tenant_id, purpose["consent_type"], action, POLICY_VERSION, "staff_app")

    _audit(db, tenant_id, actor_id, u.role, get_client_ip(r), "compliance.staff_consent_changed",
           meta={"purpose_code": purpose_code, "enabled": enabled})
    await db.commit()

    return ok({"purpose_code": purpose_code, "enabled": enabled}, _rid(r), "compliance_technician")


@router.get("/consent-history", summary="Full consent change ledger (never destructive, append-only)", response_model=ApiResponse[dict])
async def consent_history(
        r: Request, page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100),
        db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
        s: ComplianceEnterpriseService = Depends(_svc),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    result = await s.list_consent_records(subject_id=actor_id, page=page, limit=limit)
    return ok(result, _rid(r), "compliance_technician")


@router.get("/requests", summary="List own privacy requests", response_model=ApiResponse[dict])
async def list_requests(
        r: Request, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    stmt = select(ComplianceRequest).where(
        ComplianceRequest.subject_type == SUBJECT_TYPE, ComplianceRequest.subject_id == actor_id,
    ).order_by(ComplianceRequest.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.execute(stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
    return ok({
        "requests": [_safe_request(req.to_dict()) for req in rows],
        "meta": {"total": total or 0, "page": page, "limit": limit},
    }, _rid(r), "compliance_technician")


@router.post("/requests", status_code=status.HTTP_201_CREATED, summary="Submit a privacy request", response_model=ApiResponse[dict])
async def create_request(
        r: Request, db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
        s: ComplianceEnterpriseService = Depends(_svc),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    body = await r.json()
    request_type = body.get("request_type", "")
    reason = (body.get("reason") or "").strip()

    if request_type not in TECHNICIAN_ALLOWED_REQUEST_TYPES:
        raise ServiceOSException("VALIDATION_ERROR", f"request_type must be one of: {sorted(TECHNICIAN_ALLOWED_REQUEST_TYPES)}")
    if not reason:
        raise ServiceOSException("VALIDATION_ERROR", "reason is required.")
    if not body.get("confirm_understanding"):
        raise ServiceOSException("VALIDATION_ERROR", "confirm_understanding is required.")

    # Duplicate-open-request detection (spec section 9), scoped to this subject only.
    existing = await db.scalar(select(ComplianceRequest).where(
        ComplianceRequest.subject_type == SUBJECT_TYPE, ComplianceRequest.subject_id == actor_id,
        ComplianceRequest.request_type == request_type, ComplianceRequest.status.in_(OPEN_STATUSES),
    ))
    if existing:
        raise ServiceOSException("DUPLICATE_OPEN_REQUEST", f"An open request of type '{request_type}' already exists.",
                                 context={"existing_request_id": str(existing.id)})

    result = await s.create_request({
        "subject_type": SUBJECT_TYPE, "subject_id": str(actor_id),
        "subject_email": u.email, "subject_name": u.full_name or u.email,
        "request_type": request_type, "reason": reason,
        "request_source": "staff_app", "verification_status": "not_required",
        "metadata_json": {
            "tenant_id": u.tenant_id, "actor_user_id": u.user_id,
            "details": body.get("details", ""),
            "is_account_closure": request_type == ACCOUNT_CLOSURE_REQUEST_TYPE and bool(body.get("is_account_closure")),
        },
    })

    _audit(db, uuid.UUID(u.tenant_id) if u.tenant_id else None, actor_id, u.role, get_client_ip(r),
           "compliance.staff_request_created", reference_id=result["id"],
           meta={"request_type": request_type, "request_number": result["request_number"]})
    await db.commit()

    return ok({
        "request_id": result["id"], "request_number": result["request_number"],
        "request_type": result["request_type"], "status": result["status"],
        "status_label": STATUS_LABELS.get(result["status"], result["status"]),
        "submitted_at": result["submitted_at"], "due_at": result["due_at"],
        "message": "Your request has been submitted and will be reviewed across every ServiceOS category linked to your account.",
    }, _rid(r), "compliance_technician")


@router.get("/requests/{request_id}", summary="View own request detail", response_model=ApiResponse[dict])
async def get_request_detail(
        request_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician), s: ComplianceEnterpriseService = Depends(_svc),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    req = await db.scalar(select(ComplianceRequest).where(
        ComplianceRequest.id == request_id, ComplianceRequest.subject_type == SUBJECT_TYPE,
        ComplianceRequest.subject_id == actor_id,
    ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")

    detail = await s.get_request(request_id)
    safe = _safe_request(detail)
    visible_actions = {
        "request.created", "request.identity_verified", "request.approved",
        "request.partially_approved", "request.rejected", "request.processed",
        "request.completed", "compliance.staff_request_created",
    }
    safe["audit_trail"] = [
        {"action": e["action"], "created_at": e["created_at"]}
        for e in detail.get("audit_trail", []) if e["action"] in visible_actions
    ]

    export_row = await db.scalar(select(ComplianceExport).where(
        ComplianceExport.request_id == request_id, ComplianceExport.status.in_(["processing", "ready", "downloaded"]),
    ))
    if export_row:
        safe["export"] = {
            "export_id": str(export_row.id), "status": export_row.status,
            "expires_at": export_row.expires_at.isoformat() if export_row.expires_at else None,
            "is_expired": bool(export_row.expires_at and export_row.expires_at < utcnow()),
        }
    return ok(safe, _rid(r), "compliance_technician")


@router.post("/requests/{request_id}/withdraw", summary="Withdraw own pending request", response_model=ApiResponse[dict])
async def withdraw_request(
        request_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    req = await db.scalar(select(ComplianceRequest).where(
        ComplianceRequest.id == request_id, ComplianceRequest.subject_type == SUBJECT_TYPE,
        ComplianceRequest.subject_id == actor_id,
    ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")
    if req.status not in ("submitted", "identity_verification_pending"):
        raise ServiceOSException("INVALID_STATE", f"Cannot withdraw a request with status '{req.status}'.")

    req.status = "cancelled"
    _audit(db, uuid.UUID(u.tenant_id) if u.tenant_id else None, actor_id, u.role, get_client_ip(r),
           "compliance.staff_request_withdrawn", reference_id=str(request_id), meta={"request_number": req.request_number})
    await db.commit()
    return ok({"withdrawn": True, "request_id": str(request_id)}, _rid(r), "compliance_technician")


@router.post("/requests/{request_id}/generate-export", summary="Queue a voluntary data export", response_model=ApiResponse[dict])
async def generate_export(
        request_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    req = await db.scalar(select(ComplianceRequest).where(
        ComplianceRequest.id == request_id, ComplianceRequest.subject_type == SUBJECT_TYPE,
        ComplianceRequest.subject_id == actor_id,
    ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")
    if req.request_type not in EXPORT_REQUEST_TYPES:
        raise ServiceOSException("INVALID_REQUEST_TYPE", "generate-export is only available for export-type requests.")
    if req.status not in ("approved", "completed"):
        raise ServiceOSException("INVALID_STATE", f"Request must be approved before generating an export (current: {req.status}).")

    expires_at = utcnow() + timedelta(days=7)
    export = ComplianceExport(request_id=request_id, subject_type=req.subject_type, subject_id=req.subject_id,
                              status="processing", expires_at=expires_at, generated_at=utcnow())
    db.add(export)
    _audit(db, uuid.UUID(u.tenant_id) if u.tenant_id else None, actor_id, u.role, get_client_ip(r),
           "compliance.staff_export_generated", reference_id=str(request_id), meta={"export_id": str(export.id)})
    await db.commit()

    return ok({
        "export_id": str(export.id), "status": "processing", "expires_at": expires_at.isoformat(),
        "message": "Your export is being generated. Check back shortly.",
    }, _rid(r), "compliance_technician")


@router.get("/exports/{export_id}", summary="Get export status/download", response_model=ApiResponse[dict])
async def get_export(
        export_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db), u: UserContext = Depends(require_technician),
) -> ApiResponse[dict]:
    actor_id = uuid.UUID(u.user_id)
    export = await db.scalar(select(ComplianceExport).where(ComplianceExport.id == export_id))
    if not export:
        raise ServiceOSException("NOT_FOUND", "Export not found.")
    req = await db.scalar(select(ComplianceRequest).where(
        ComplianceRequest.id == export.request_id, ComplianceRequest.subject_type == SUBJECT_TYPE,
        ComplianceRequest.subject_id == actor_id,
    ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    if export.status == "ready" and export.expires_at and export.expires_at < utcnow():
        export.status = "expired"
        export.download_url = None
        await db.commit()

    return ok({
        "export_id": str(export.id), "status": export.status,
        "expires_at": export.expires_at.isoformat() if export.expires_at else None,
        "downloaded_at": export.downloaded_at.isoformat() if export.downloaded_at else None,
        "download_url": export.download_url if export.status in ("ready", "downloaded") else None,
    }, _rid(r), "compliance_technician")
