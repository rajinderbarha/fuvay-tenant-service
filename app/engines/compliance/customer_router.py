"""Compliance Customer Self-Service Router — DPDP Act 2023.

Endpoints under /v1/me/compliance allow authenticated customers to:
  - Create and track compliance requests
  - View consent records and withdraw allowed consents
  - Download their own data exports

Security invariants:
  - All endpoints require require_customer (role=customer).
  - Customers can only access their own records (subject_id == user.id).
  - Internal admin notes, risk flags, and exemption details are stripped
    before returning customer-visible data.
  - Rate limits: 5 request creations / day, 10 downloads / day,
    10 consent withdrawals / day (enforced in-process via simple audit count).
"""
import uuid
import structlog
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.security import get_client_ip
from app.dependencies.auth import UserContext, require_customer
from app.dependencies.db import get_db
from app.engines.compliance.enterprise_service import ComplianceEnterpriseService
from app.engines.compliance.models import (
    ComplianceRequest, ComplianceAuditLog, ComplianceExport,
)
from app.models.base import utcnow
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException

logger = structlog.get_logger("compliance.customer_router")
router = APIRouter(prefix="/v1/me/compliance", tags=["Compliance Customer Self-Service"])

# Consent types customers may withdraw (not required-for-account)
WITHDRAWABLE_CONSENT_TYPES = {
    "marketing", "location_access", "notification",
    "profiling", "ai_assistant_processing", "media_processing",
}

# Request types customers may create
CUSTOMER_ALLOWED_REQUEST_TYPES = {
    "right_to_erasure", "data_export", "consent_withdrawal",
    "consent_update", "data_correction", "processing_objection", "grievance",
}

# Statuses considered "open" for duplicate-check
OPEN_STATUSES = {
    "submitted", "identity_verification_pending",
    "under_review", "approved", "processing",
}

# Customer-friendly status labels (never expose technical names raw)
STATUS_LABELS = {
    "submitted": "Submitted",
    "identity_verification_pending": "Identity Verification Required",
    "under_review": "Under Review",
    "approved": "Approved",
    "partially_approved": "Partially Approved",
    "rejected": "Rejected",
    "processing": "Processing",
    "completed": "Completed",
    "failed": "Needs Attention",
    "cancelled": "Cancelled",
    "sla_breached": "Delayed",
}
SLA_LABELS = {
    "on_track": "On Track",
    "at_risk": "Due Soon",
    "breached": "Delayed",
    "completed": "Completed",
}

RATE_LIMIT_CREATE_PER_DAY = 5
RATE_LIMIT_DOWNLOAD_PER_DAY = 10
RATE_LIMIT_CONSENT_WITHDRAW_PER_DAY = 10


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_customer)) -> ComplianceEnterpriseService:
    return ComplianceEnterpriseService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, actor_ip=get_client_ip(r))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _customer_safe_request(d: dict) -> dict:
    """Strip internal fields before sending to customer."""
    return {
        "id": d.get("id"),
        "request_number": d.get("request_number"),
        "request_type": d.get("request_type"),
        "status": d.get("status"),
        "status_label": STATUS_LABELS.get(d.get("status", ""), d.get("status", "")),
        "sla_status": d.get("sla_status"),
        "sla_label": SLA_LABELS.get(d.get("sla_status", ""), d.get("sla_status", "")),
        "verification_status": d.get("verification_status"),
        "submitted_at": d.get("submitted_at"),
        "due_at": d.get("due_at"),
        "completed_at": d.get("completed_at"),
        "reason": d.get("reason"),
        # Admin notes / internal risk flags are intentionally omitted
        "rejection_reason": d.get("rejection_reason"),
        "request_source": d.get("request_source"),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


async def _check_rate_limit(db: AsyncSession, actor_id: uuid.UUID,
                             action: str, limit: int) -> None:
    """Raise if actor has hit rate limit for this action today."""
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    count = await db.scalar(
        select(func.count()).select_from(ComplianceAuditLog).where(
            ComplianceAuditLog.actor_id == actor_id,
            ComplianceAuditLog.action == action,
            ComplianceAuditLog.created_at >= start_of_day,
        ))
    if (count or 0) >= limit:
        raise ServiceOSException(
            "RATE_LIMIT_EXCEEDED",
            f"Limit of {limit} '{action}' actions per day reached. Try again tomorrow.")


# ── Customer Request Endpoints ────────────────────────────────────────────────

@router.get("/requests",
            summary="List own compliance requests",
            response_model=ApiResponse[dict])
async def list_my_requests(
        r: Request,
        request_type: str | None = Query(None),
        req_status: str | None = Query(None, alias="status"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    stmt = (
        select(ComplianceRequest)
        .where(ComplianceRequest.subject_id == user_id)
        .where(ComplianceRequest.subject_type == "customer")
    )
    if request_type:
        stmt = stmt.where(ComplianceRequest.request_type == request_type)
    if req_status:
        stmt = stmt.where(ComplianceRequest.status == req_status)

    total = await db.scalar(select(func.count()).select_from(
        stmt.subquery()))

    stmt = stmt.order_by(ComplianceRequest.created_at.desc())
    stmt = stmt.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    # Audit view
    for req in rows:
        db.add(ComplianceAuditLog(
            user_id=user_id, actor_id=user_id, actor_role="customer",
            actor_ip=get_client_ip(r), action="compliance.customer_request_viewed",
            reference_id=str(req.id), legal_basis="dpdp_act_2023",
            meta={"request_number": req.request_number}))
    await db.commit()

    return ok({
        "requests": [_customer_safe_request(req.to_dict()) for req in rows],
        "meta": {"total": total or 0, "page": page, "limit": limit,
                 "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
    }, _rid(r), "compliance_customer")


@router.post("/requests",
             summary="Create a new compliance request (erasure / export / consent withdrawal / etc.)",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_my_request(
        r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    await _check_rate_limit(db, user_id, "compliance.customer_request_created",
                            RATE_LIMIT_CREATE_PER_DAY)

    body = await r.json()
    request_type = body.get("request_type", "")
    reason = body.get("reason", "")

    if request_type not in CUSTOMER_ALLOWED_REQUEST_TYPES:
        raise ServiceOSException(
            "VALIDATION_ERROR",
            f"request_type must be one of: {sorted(CUSTOMER_ALLOWED_REQUEST_TYPES)}")

    if not body.get("confirm_understanding"):
        raise ServiceOSException(
            "VALIDATION_ERROR",
            "confirm_understanding is required and must be true.")

    if request_type in ("right_to_erasure", "data_correction", "grievance") and not reason:
        raise ServiceOSException(
            "VALIDATION_ERROR",
            f"reason is required for request_type '{request_type}'.")

    # Duplicate open-request check
    existing = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.subject_id == user_id,
            ComplianceRequest.request_type == request_type,
            ComplianceRequest.status.in_(OPEN_STATUSES),
        ))
    if existing:
        raise ServiceOSException(
            "DUPLICATE_OPEN_REQUEST",
            f"You already have an open request of type '{request_type}'.",
            context={"existing_request_id": str(existing.id)})

    result = await s.create_request({
        "subject_type": "customer",
        "subject_id": str(user_id),
        "subject_email": u.email,
        "subject_name": getattr(u, "full_name", None) or u.email,
        "request_type": request_type,
        "reason": reason,
        "request_source": "customer_app",
        "verification_status": "not_required",
    })

    # Rate-limit audit
    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.customer_request_created",
        reference_id=result["id"], legal_basis="dpdp_act_2023",
        meta={"request_type": request_type, "request_number": result["request_number"]}))
    await db.commit()

    return ok({
        "request_id": result["id"],
        "request_number": result["request_number"],
        "request_type": result["request_type"],
        "status": result["status"],
        "status_label": STATUS_LABELS.get(result["status"], result["status"]),
        "sla_status": result["sla_status"],
        "submitted_at": result["submitted_at"],
        "due_at": result["due_at"],
        "message": "Your request has been submitted. We will respond within 72 hours.",
    }, _rid(r), "compliance_customer")


@router.get("/requests/{request_id}",
            summary="View own request detail",
            response_model=ApiResponse[dict])
async def get_my_request(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.subject_id == user_id,
        ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")

    detail = await s.get_request(request_id)

    # Audit
    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.customer_request_viewed",
        reference_id=str(request_id), legal_basis="dpdp_act_2023",
        meta={"request_number": req.request_number}))
    await db.commit()

    # Strip admin-only fields; only expose safe audit trail entries
    safe = _customer_safe_request(detail)
    # Expose only customer-visible audit actions (exclude admin-internal actions)
    customer_visible_actions = {
        "request.created", "request.identity_verified", "request.approved",
        "request.partially_approved", "request.rejected", "request.processed",
        "request.completed", "sla.at_risk", "sla.breached", "sla.on_track",
        "compliance.customer_request_viewed",
    }
    safe["audit_trail"] = [
        {"action": e["action"], "created_at": e["created_at"]}
        for e in detail.get("audit_trail", [])
        if e["action"] in customer_visible_actions
    ]
    # Export info if available
    export_row = await db.scalar(
        select(ComplianceExport).where(
            ComplianceExport.request_id == request_id,
            ComplianceExport.status.in_(["ready", "downloaded"]),
        ))
    if export_row and req.request_type == "data_export":
        safe["export"] = {
            "export_id": str(export_row.id),
            "status": export_row.status,
            "expires_at": export_row.expires_at.isoformat() if export_row.expires_at else None,
            "is_expired": export_row.expires_at < utcnow() if export_row.expires_at else False,
        }

    return ok(safe, _rid(r), "compliance_customer")


@router.post("/requests/{request_id}/cancel",
             summary="Cancel own pending request",
             response_model=ApiResponse[dict])
async def cancel_my_request(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.subject_id == user_id,
        ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")
    if req.status not in ("submitted", "identity_verification_pending"):
        raise ServiceOSException(
            "INVALID_STATE",
            f"Cannot cancel a request with status '{req.status}'. "
            "Only submitted requests may be cancelled.")

    req.status = "cancelled"
    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.customer_request_cancelled",
        reference_id=str(request_id), legal_basis="dpdp_act_2023",
        meta={"request_number": req.request_number}))
    await db.commit()
    return ok({"cancelled": True, "request_id": str(request_id)}, _rid(r), "compliance_customer")


@router.post("/requests/{request_id}/add-note",
             summary="Add a note to own request",
             response_model=ApiResponse[dict])
async def add_my_note(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.subject_id == user_id,
        ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")

    body = await r.json()
    note = (body.get("note") or "").strip()[:1000]
    if not note:
        raise ServiceOSException("VALIDATION_ERROR", "note must not be empty.")

    meta = req.metadata_json or {}
    customer_notes = meta.get("customer_notes", [])
    customer_notes.append({"note": note, "added_at": utcnow().isoformat()})
    req.metadata_json = {**meta, "customer_notes": customer_notes}
    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.customer_request_note_added",
        reference_id=str(request_id), legal_basis="dpdp_act_2023", meta={}))
    await db.commit()
    return ok({"note_added": True}, _rid(r), "compliance_customer")


# ── Consent Endpoints ─────────────────────────────────────────────────────────

@router.get("/consents",
            summary="View own consent records",
            response_model=ApiResponse[dict])
async def list_my_consents(
        r: Request,
        s: ComplianceEnterpriseService = Depends(_svc),
        u: UserContext = Depends(require_customer)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    result = await s.list_consent_records(subject_id=user_id, page=1, limit=100)
    return ok(result, _rid(r), "compliance_customer")


@router.post("/consents/{consent_type}/withdraw",
             summary="Withdraw an allowed consent type",
             response_model=ApiResponse[dict])
async def withdraw_my_consent(
        consent_type: str, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    if consent_type not in WITHDRAWABLE_CONSENT_TYPES:
        raise ServiceOSException(
            "VALIDATION_ERROR",
            f"consent_type '{consent_type}' cannot be withdrawn. "
            f"Withdrawable: {sorted(WITHDRAWABLE_CONSENT_TYPES)}")

    user_id = uuid.UUID(u.user_id)
    await _check_rate_limit(db, user_id, "compliance.customer_consent_withdrawn",
                            RATE_LIMIT_CONSENT_WITHDRAW_PER_DAY)

    body = await r.json()
    result = await s.revoke_consent(user_id, consent_type, body.get("reason"))

    # Override audit action with customer-specific one for rate-limiting
    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.customer_consent_withdrawn",
        legal_basis="dpdp_act_2023",
        meta={"consent_type": consent_type, "reason": body.get("reason", "")}))
    await db.commit()

    return ok({"withdrawn": True, "consent_type": consent_type}, _rid(r), "compliance_customer")


# ── Export Download ───────────────────────────────────────────────────────────

@router.get("/exports/{export_id}/download",
            summary="Download own data export",
            response_model=ApiResponse[dict])
async def download_my_export(
        export_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_customer)) -> ApiResponse[dict]:

    user_id = uuid.UUID(u.user_id)
    await _check_rate_limit(db, user_id, "compliance.customer_export_downloaded",
                            RATE_LIMIT_DOWNLOAD_PER_DAY)

    # Find export — verify it belongs to this customer via the linked request
    export = await db.scalar(
        select(ComplianceExport).where(ComplianceExport.id == export_id))
    if not export:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    # Ownership check: load the request and verify subject_id
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == export.request_id,
            ComplianceRequest.subject_id == user_id,
            ComplianceRequest.request_type == "data_export",
        ))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    if export.status == "expired":
        raise ServiceOSException(
            "EXPORT_EXPIRED",
            "This export link has expired. Please request a new export.")

    if export.status not in ("ready", "downloaded"):
        raise ServiceOSException(
            "EXPORT_NOT_READY",
            "This export is not ready for download yet.")

    if export.expires_at and export.expires_at < utcnow():
        export.status = "expired"
        export.download_url = None
        await db.commit()
        raise ServiceOSException(
            "EXPORT_EXPIRED",
            "This export link has expired. Please request a new export.")

    # Mark downloaded
    export.status = "downloaded"
    export.downloaded_at = utcnow()

    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.export_downloaded_by_customer",
        reference_id=str(export_id), legal_basis="dpdp_act_2023",
        meta={"request_number": req.request_number, "export_id": str(export_id)}))
    # Rate-limit audit
    db.add(ComplianceAuditLog(
        user_id=user_id, actor_id=user_id, actor_role="customer",
        actor_ip=get_client_ip(r), action="compliance.customer_export_downloaded",
        reference_id=str(export_id), legal_basis="dpdp_act_2023", meta={}))
    await db.commit()

    return ok({
        "download_url": export.download_url,
        "export_id": str(export.id),
        "status": "downloaded",
        "downloaded_at": export.downloaded_at.isoformat() if export.downloaded_at else None,
    }, _rid(r), "compliance_customer")
