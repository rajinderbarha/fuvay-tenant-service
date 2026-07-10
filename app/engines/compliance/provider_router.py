"""Compliance Provider/Tenant Router — DPDP Act 2023.

Endpoints under /v1/provider/compliance allow authenticated tenant users to:
  - Create and track their own business/owner compliance requests
  - View staff requests within their tenant scope
  - See limited, scoped customer request context
  - Manage consent records for the tenant
  - Download own tenant-scoped exports

Tenant isolation invariants:
  - All requests scoped by metadata_json->>'tenant_id'
  - Tenant cannot access platform-wide compliance queue
  - Tenant cannot approve erasure; admin remains final authority
  - Customer request data is limited (no private data, no admin notes)
  - Financial/statutory records are never erasable by tenant
  - Export download verified: export.request.tenant_id == current tenant
"""
import uuid
import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.security import get_client_ip
from app.dependencies.auth import UserContext, require_tenant_owner, require_technician, get_current_user
from app.dependencies.db import get_db
from app.engines.compliance.enterprise_service import ComplianceEnterpriseService
from app.engines.compliance.models import (
    ComplianceRequest, ComplianceAuditLog, ComplianceExport,
)
from app.models.base import utcnow
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException

logger = structlog.get_logger("compliance.provider_router")
router = APIRouter(prefix="/v1/provider/compliance", tags=["Compliance Tenant Portal"])

# Request types tenants may create
TENANT_ALLOWED_REQUEST_TYPES = {
    "business_data_export", "business_profile_erasure",
    "owner_data_export", "owner_data_erasure",
    "staff_data_export", "staff_data_erasure",
    "consent_withdrawal", "data_correction",
    "processing_objection", "grievance",
}

ERASURE_TYPES = {"business_profile_erasure", "owner_data_erasure", "staff_data_erasure"}

# Erasure blockers (inform tenant; admin does final check)
ERASURE_BLOCKERS_MESSAGE = (
    "Your erasure/deactivation request will be reviewed by our team. "
    "Records required by law (GST Act 7 years: payments, invoices, commissions, wallet) "
    "and records related to active bookings, open disputes, pending payouts, "
    "or security investigations cannot be removed. "
    "You will be notified of the outcome within 72 hours."
)

# Subject types considered "staff" for staff-request scoping
TENANT_STAFF_SUBJECT_TYPES = {"tenant_staff", "technician", "staff", "provider_manager"}

# Consent types that can be withdrawn (not required for account)
TENANT_WITHDRAWABLE_CONSENT_TYPES = {
    "marketing", "notification", "location_processing",
    "document_processing", "media_processing",
    "ai_assistant_processing", "staff_management_processing",
}

# Open statuses for duplicate-check
OPEN_STATUSES = {
    "submitted", "identity_verification_pending",
    "under_review", "approved", "processing",
}

# Rate limits
RATE_LIMIT_CREATE_PER_DAY = 10
RATE_LIMIT_DOWNLOAD_PER_DAY = 20
RATE_LIMIT_CONSENT_WITHDRAW_PER_DAY = 10

# Customer-safe SLA / status labels
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_technician)) -> ComplianceEnterpriseService:
    return ComplianceEnterpriseService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, actor_ip=get_client_ip(r))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(u: UserContext) -> str:
    """Return tenant_id string, raise if user has no tenant."""
    if not u.tenant_id:
        raise ServiceOSException("FORBIDDEN", "No tenant associated with your account.")
    return u.tenant_id


def _tenant_safe_request(d: dict) -> dict:
    """Strip platform-internal fields before sending to tenant."""
    return {
        "id": d.get("id"),
        "request_number": d.get("request_number"),
        "subject_type": d.get("subject_type"),
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
        "rejection_reason": d.get("rejection_reason"),
        "request_source": d.get("request_source"),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
        # admin_notes, risk flags intentionally omitted
    }


def _customer_limited_view(req: ComplianceRequest) -> dict:
    """Return only tenant-visible fields for a customer request."""
    return {
        "id": str(req.id),
        "request_number": req.request_number,
        "request_type": req.request_type,
        "status": STATUS_LABELS.get(req.status, req.status),
        "sla_status": SLA_LABELS.get(req.sla_status, req.sla_status),
        "due_at": req.due_at.isoformat() if req.due_at else None,
        "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
        "tenant_action_required": req.metadata_json.get("tenant_action_required", False)
            if req.metadata_json else False,
        # Never expose: customer name/email, admin notes, export data, private details
    }


async def _check_rate_limit(db: AsyncSession, actor_id: uuid.UUID,
                             action: str, limit: int) -> None:
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


def _audit(db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID,
           actor_role: str, actor_ip: str, action: str,
           reference_id: str | None = None, meta: dict | None = None) -> None:
    db.add(ComplianceAuditLog(
        tenant_id=tenant_id,
        user_id=actor_id,
        actor_id=actor_id,
        actor_role=actor_role,
        actor_ip=actor_ip,
        action=action,
        reference_id=reference_id,
        legal_basis="dpdp_act_2023",
        meta=meta or {},
    ))


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary",
            summary="Tenant compliance dashboard — 8 summary cards",
            response_model=ApiResponse[dict])
async def get_summary(
        r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    tenant_id = uuid.UUID(tenant_id_str)

    # Count requests for this tenant (stored in metadata_json)
    def _count_where(**kwargs):
        stmt = select(func.count()).select_from(ComplianceRequest).where(
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str)
        for col, val in kwargs.items():
            stmt = stmt.where(getattr(ComplianceRequest, col) == val)
        return stmt

    open_count = await db.scalar(
        select(func.count()).select_from(ComplianceRequest).where(
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.status.in_(OPEN_STATUSES)))

    pending_admin = await db.scalar(
        select(func.count()).select_from(ComplianceRequest).where(
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.status.in_(["under_review", "approved", "processing"])))

    completed_count = await db.scalar(_count_where(status="completed"))
    rejected_count  = await db.scalar(_count_where(status="rejected"))

    sla_at_risk = await db.scalar(
        select(func.count()).select_from(ComplianceRequest).where(
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.sla_status.in_(["at_risk", "breached"])))

    # Export count
    export_count = await db.scalar(
        select(func.count()).select_from(ComplianceExport)
        .join(ComplianceRequest, ComplianceExport.request_id == ComplianceRequest.id)
        .where(ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str))

    # Staff requests
    staff_count = await db.scalar(
        select(func.count()).select_from(ComplianceRequest).where(
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.subject_type.in_(TENANT_STAFF_SUBJECT_TYPES)))

    return ok({
        "open_requests": open_count or 0,
        "pending_admin_review": pending_admin or 0,
        "data_exports": export_count or 0,
        "staff_requests": staff_count or 0,
        "sla_at_risk": sla_at_risk or 0,
        "completed_requests": completed_count or 0,
        "rejected_requests": rejected_count or 0,
        "tenant_id": tenant_id_str,
    }, _rid(r), "compliance_provider")


# ── My Requests ───────────────────────────────────────────────────────────────

@router.get("/requests",
            summary="List own tenant compliance requests",
            response_model=ApiResponse[dict])
async def list_my_requests(
        r: Request,
        request_type: str | None = Query(None),
        req_status: str | None = Query(None, alias="status"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    stmt = (
        select(ComplianceRequest)
        .where(ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str)
        .where(ComplianceRequest.subject_type.not_in(TENANT_STAFF_SUBJECT_TYPES))
    )
    if request_type:
        stmt = stmt.where(ComplianceRequest.request_type == request_type)
    if req_status:
        stmt = stmt.where(ComplianceRequest.status == req_status)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows  = (await db.execute(
        stmt.order_by(ComplianceRequest.created_at.desc())
            .offset((page - 1) * limit).limit(limit))).scalars().all()

    return ok({
        "requests": [_tenant_safe_request(req.to_dict()) for req in rows],
        "meta": {"total": total or 0, "page": page, "limit": limit,
                 "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
    }, _rid(r), "compliance_provider")


@router.post("/requests",
             summary="Create a tenant compliance request",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_my_request(
        r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    actor_id = uuid.UUID(u.user_id)
    await _check_rate_limit(db, actor_id, "compliance.tenant_request_created",
                            RATE_LIMIT_CREATE_PER_DAY)

    body = await r.json()
    request_type = body.get("request_type", "")
    reason = body.get("reason", "")

    if request_type not in TENANT_ALLOWED_REQUEST_TYPES:
        raise ServiceOSException(
            "VALIDATION_ERROR",
            f"request_type must be one of: {sorted(TENANT_ALLOWED_REQUEST_TYPES)}")

    if not body.get("confirm_understanding"):
        raise ServiceOSException("VALIDATION_ERROR", "confirm_understanding is required.")

    if not reason:
        raise ServiceOSException("VALIDATION_ERROR", "reason is required.")

    # Duplicate open request check
    existing = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.request_type == request_type,
            ComplianceRequest.status.in_(OPEN_STATUSES),
        ))
    if existing:
        raise ServiceOSException(
            "DUPLICATE_OPEN_REQUEST",
            f"An open request of type '{request_type}' already exists.",
            context={"existing_request_id": str(existing.id)})

    subject_type = "tenant_business" if "business" in request_type else "tenant_owner"
    subject_id   = tenant_id_str if subject_type == "tenant_business" else u.user_id

    result = await s.create_request({
        "subject_type": subject_type,
        "subject_id": subject_id,
        "subject_email": u.email,
        "subject_name": u.full_name or u.email,
        "request_type": request_type,
        "reason": reason,
        "request_source": "tenant_portal",
        "verification_status": "not_required",
        "metadata_json": {
            "tenant_id": tenant_id_str,
            "actor_user_id": u.user_id,
            "details": body.get("details", ""),
        },
    })

    # Store tenant_id in the metadata after creation
    created_req = await db.scalar(
        select(ComplianceRequest).where(ComplianceRequest.id == uuid.UUID(result["id"])))
    if created_req:
        created_req.metadata_json = {
            **(created_req.metadata_json or {}),
            "tenant_id": tenant_id_str,
        }

    _audit(db, uuid.UUID(tenant_id_str), actor_id, u.role, get_client_ip(r),
           "compliance.tenant_request_created",
           reference_id=result["id"],
           meta={"request_type": request_type, "request_number": result["request_number"]})
    await db.commit()

    extra_msg = ""
    if request_type in ERASURE_TYPES:
        extra_msg = f" {ERASURE_BLOCKERS_MESSAGE}"

    return ok({
        "request_id": result["id"],
        "request_number": result["request_number"],
        "request_type": result["request_type"],
        "status": result["status"],
        "status_label": STATUS_LABELS.get(result["status"], result["status"]),
        "sla_status": result["sla_status"],
        "submitted_at": result["submitted_at"],
        "due_at": result["due_at"],
        "message": f"Your request has been submitted.{extra_msg}",
    }, _rid(r), "compliance_provider")


@router.get("/requests/{request_id}",
            summary="View own request detail",
            response_model=ApiResponse[dict])
async def get_my_request(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")

    detail = await s.get_request(request_id)
    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.tenant_request_viewed",
           reference_id=str(request_id),
           meta={"request_number": req.request_number})
    await db.commit()

    safe = _tenant_safe_request(detail)
    # Filter audit trail to tenant-visible actions
    visible_actions = {
        "request.created", "request.identity_verified", "request.approved",
        "request.partially_approved", "request.rejected", "request.processed",
        "request.completed", "sla.at_risk", "sla.breached",
        "compliance.tenant_request_created", "compliance.tenant_request_viewed",
    }
    safe["audit_trail"] = [
        {"action": e["action"], "created_at": e["created_at"]}
        for e in detail.get("audit_trail", [])
        if e["action"] in visible_actions
    ]

    # Export info
    export_row = await db.scalar(
        select(ComplianceExport).where(
            ComplianceExport.request_id == request_id,
            ComplianceExport.status.in_(["ready", "downloaded"])))
    if export_row and "export" in req.request_type:
        safe["export"] = {
            "export_id": str(export_row.id),
            "status": export_row.status,
            "expires_at": export_row.expires_at.isoformat() if export_row.expires_at else None,
            "is_expired": bool(export_row.expires_at and export_row.expires_at < utcnow()),
        }

    return ok(safe, _rid(r), "compliance_provider")


@router.post("/requests/{request_id}/cancel",
             summary="Cancel own pending request",
             response_model=ApiResponse[dict])
async def cancel_my_request(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")
    if req.status not in ("submitted", "identity_verification_pending"):
        raise ServiceOSException(
            "INVALID_STATE",
            f"Cannot cancel a request with status '{req.status}'.")

    req.status = "cancelled"
    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.tenant_request_cancelled",
           reference_id=str(request_id),
           meta={"request_number": req.request_number})
    await db.commit()
    return ok({"cancelled": True, "request_id": str(request_id)}, _rid(r), "compliance_provider")


# ── Export Endpoints ──────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/generate-export",
             summary="Queue a data export for an approved request",
             response_model=ApiResponse[dict])
async def generate_export(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Request not found.")
    if "export" not in req.request_type:
        raise ServiceOSException(
            "INVALID_REQUEST_TYPE",
            "generate-export is only available for export-type requests.")
    if req.status not in ("approved", "completed"):
        raise ServiceOSException(
            "INVALID_STATE",
            f"Request must be approved before generating export (current: {req.status}).")

    from datetime import timedelta
    expires_at = utcnow() + timedelta(days=7)
    export = ComplianceExport(
        request_id=request_id,
        subject_type=req.subject_type,
        subject_id=req.subject_id,
        status="processing",
        expires_at=expires_at,
        generated_at=utcnow(),
    )
    db.add(export)
    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.tenant_export_generated",
           reference_id=str(request_id),
           meta={"export_id": str(export.id)})
    await db.commit()

    return ok({
        "export_id": str(export.id),
        "status": "processing",
        "expires_at": expires_at.isoformat(),
        "message": "Export is being generated. Check back shortly.",
    }, _rid(r), "compliance_provider")


@router.get("/exports",
            summary="List tenant data exports",
            response_model=ApiResponse[dict])
async def list_exports(
        r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    stmt = (
        select(ComplianceExport)
        .join(ComplianceRequest, ComplianceExport.request_id == ComplianceRequest.id)
        .where(ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str)
        .order_by(ComplianceExport.created_at.desc()))
    rows = (await db.execute(stmt)).scalars().all()

    return ok({
        "exports": [{
            "id": str(e.id),
            "request_id": str(e.request_id) if e.request_id else None,
            "status": e.status,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "downloaded_at": e.downloaded_at.isoformat() if e.downloaded_at else None,
            "generated_at": e.generated_at.isoformat() if e.generated_at else None,
        } for e in rows],
        "total": len(rows),
    }, _rid(r), "compliance_provider")


@router.get("/exports/{export_id}",
            summary="Get export detail",
            response_model=ApiResponse[dict])
async def get_export(
        export_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    export = await db.scalar(
        select(ComplianceExport).where(ComplianceExport.id == export_id))
    if not export:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    # Verify tenant scope
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == export.request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    return ok({
        "id": str(export.id),
        "request_id": str(export.request_id) if export.request_id else None,
        "status": export.status,
        "expires_at": export.expires_at.isoformat() if export.expires_at else None,
        "downloaded_at": export.downloaded_at.isoformat() if export.downloaded_at else None,
        "generated_at": export.generated_at.isoformat() if export.generated_at else None,
        "download_url": export.download_url if export.status in ("ready", "downloaded") else None,
    }, _rid(r), "compliance_provider")


@router.get("/exports/{export_id}/download",
            summary="Download tenant data export",
            response_model=ApiResponse[dict])
async def download_export(
        export_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    actor_id = uuid.UUID(u.user_id)
    await _check_rate_limit(db, actor_id, "compliance.tenant_export_downloaded",
                            RATE_LIMIT_DOWNLOAD_PER_DAY)

    export = await db.scalar(
        select(ComplianceExport).where(ComplianceExport.id == export_id))
    if not export:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == export.request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Export not found.")

    if export.status == "expired":
        raise ServiceOSException("EXPORT_EXPIRED",
            "This export has expired. Please request a new export.")
    if export.status not in ("ready", "downloaded"):
        raise ServiceOSException("EXPORT_NOT_READY",
            "This export is not ready for download yet.")
    if export.expires_at and export.expires_at < utcnow():
        export.status = "expired"
        export.download_url = None
        await db.commit()
        raise ServiceOSException("EXPORT_EXPIRED",
            "This export has expired. Please request a new export.")

    export.status = "downloaded"
    export.downloaded_at = utcnow()

    _audit(db, uuid.UUID(tenant_id_str), actor_id, u.role, get_client_ip(r),
           "compliance.tenant_export_downloaded",
           reference_id=str(export_id),
           meta={"request_number": req.request_number})
    _audit(db, uuid.UUID(tenant_id_str), actor_id, u.role, get_client_ip(r),
           "compliance.tenant_export_downloaded",
           reference_id=str(export_id), meta={})
    await db.commit()

    return ok({
        "download_url": export.download_url,
        "export_id": str(export.id),
        "status": "downloaded",
        "downloaded_at": export.downloaded_at.isoformat() if export.downloaded_at else None,
    }, _rid(r), "compliance_provider")


# ── Consent Endpoints ─────────────────────────────────────────────────────────

@router.get("/consents",
            summary="View tenant consent records",
            response_model=ApiResponse[dict])
async def list_consents(
        r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_technician),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    _require_tenant(u)
    result = await s.list_consent_records(
        subject_id=uuid.UUID(u.user_id), page=1, limit=100)
    return ok(result, _rid(r), "compliance_provider")


@router.post("/consents/{consent_type}/withdraw",
             summary="Withdraw an optional tenant consent",
             response_model=ApiResponse[dict])
async def withdraw_consent(
        consent_type: str, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    if consent_type not in TENANT_WITHDRAWABLE_CONSENT_TYPES:
        raise ServiceOSException(
            "VALIDATION_ERROR",
            f"consent_type '{consent_type}' cannot be withdrawn. "
            f"Withdrawable: {sorted(TENANT_WITHDRAWABLE_CONSENT_TYPES)}")

    tenant_id_str = _require_tenant(u)
    actor_id = uuid.UUID(u.user_id)
    await _check_rate_limit(db, actor_id, "compliance.tenant_consent_withdrawn",
                            RATE_LIMIT_CONSENT_WITHDRAW_PER_DAY)

    body = await r.json()
    result = await s.revoke_consent(actor_id, consent_type, body.get("reason"))

    _audit(db, uuid.UUID(tenant_id_str), actor_id, u.role, get_client_ip(r),
           "compliance.tenant_consent_withdrawn",
           meta={"consent_type": consent_type, "reason": body.get("reason", "")})
    await db.commit()

    return ok({"withdrawn": True, "consent_type": consent_type}, _rid(r), "compliance_provider")


# ── Staff Requests ────────────────────────────────────────────────────────────

@router.get("/staff-requests",
            summary="View staff compliance requests within this tenant",
            response_model=ApiResponse[dict])
async def list_staff_requests(
        r: Request,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    stmt = (
        select(ComplianceRequest)
        .where(ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str)
        .where(ComplianceRequest.subject_type.in_(TENANT_STAFF_SUBJECT_TYPES))
        .order_by(ComplianceRequest.created_at.desc())
        .offset((page - 1) * limit).limit(limit))

    total_stmt = (
        select(func.count()).select_from(ComplianceRequest)
        .where(ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str)
        .where(ComplianceRequest.subject_type.in_(TENANT_STAFF_SUBJECT_TYPES)))

    total = await db.scalar(total_stmt)
    rows  = (await db.execute(stmt)).scalars().all()

    for req in rows:
        _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
               "compliance.staff_request_viewed_by_tenant",
               reference_id=str(req.id), meta={"request_number": req.request_number})
    await db.commit()

    return ok({
        "requests": [_tenant_safe_request(req.to_dict()) for req in rows],
        "meta": {"total": total or 0, "page": page, "limit": limit,
                 "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
    }, _rid(r), "compliance_provider")


@router.get("/staff-requests/{request_id}",
            summary="View a staff request detail",
            response_model=ApiResponse[dict])
async def get_staff_request(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner),
        s: ComplianceEnterpriseService = Depends(_svc)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.subject_type.in_(TENANT_STAFF_SUBJECT_TYPES)))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Staff request not found.")

    detail = await s.get_request(request_id)
    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.staff_request_viewed_by_tenant",
           reference_id=str(request_id), meta={"request_number": req.request_number})
    await db.commit()

    return ok(_tenant_safe_request(detail), _rid(r), "compliance_provider")


@router.post("/staff-requests/{request_id}/tenant-response",
             summary="Add tenant-side response to a staff request",
             response_model=ApiResponse[dict])
async def staff_tenant_response(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.metadata_json["tenant_id"].astext == tenant_id_str,
            ComplianceRequest.subject_type.in_(TENANT_STAFF_SUBJECT_TYPES)))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Staff request not found.")

    body = await r.json()
    response_text = (body.get("response") or "").strip()[:2000]
    if not response_text:
        raise ServiceOSException("VALIDATION_ERROR", "response must not be empty.")

    meta = req.metadata_json or {}
    tenant_responses = meta.get("tenant_responses", [])
    tenant_responses.append({
        "response": response_text,
        "actor_id": u.user_id,
        "actor_role": u.role,
        "added_at": utcnow().isoformat(),
    })
    req.metadata_json = {**meta, "tenant_responses": tenant_responses,
                         "tenant_action_required": False}

    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.tenant_response_added",
           reference_id=str(request_id), meta={"response_preview": response_text[:100]})
    await db.commit()

    return ok({"response_added": True, "request_id": str(request_id)},
              _rid(r), "compliance_provider")


# ── Customer Request Limited Visibility ───────────────────────────────────────

@router.get("/customer-requests",
            summary="View customer compliance requests related to this tenant (limited fields)",
            response_model=ApiResponse[dict])
async def list_customer_requests(
        r: Request,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    # Customer requests linked to this tenant via metadata_json.related_tenant_id
    stmt = (
        select(ComplianceRequest)
        .where(ComplianceRequest.subject_type == "customer")
        .where(ComplianceRequest.metadata_json["related_tenant_id"].astext == tenant_id_str)
        .order_by(ComplianceRequest.created_at.desc())
        .offset((page - 1) * limit).limit(limit))

    total_stmt = (
        select(func.count()).select_from(ComplianceRequest)
        .where(ComplianceRequest.subject_type == "customer")
        .where(ComplianceRequest.metadata_json["related_tenant_id"].astext == tenant_id_str))

    total = await db.scalar(total_stmt)
    rows  = (await db.execute(stmt)).scalars().all()

    for req in rows:
        _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
               "compliance.customer_request_viewed_by_tenant",
               reference_id=str(req.id), meta={"request_number": req.request_number})
    if rows:
        await db.commit()

    return ok({
        "requests": [_customer_limited_view(req) for req in rows],
        "meta": {"total": total or 0, "page": page, "limit": limit,
                 "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
        "note": "Only requests related to bookings/jobs with your business are visible.",
    }, _rid(r), "compliance_provider")


@router.get("/customer-requests/{request_id}",
            summary="View limited detail for a related customer request",
            response_model=ApiResponse[dict])
async def get_customer_request(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.subject_type == "customer",
            ComplianceRequest.metadata_json["related_tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Customer request not found in your tenant scope.")

    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.customer_request_viewed_by_tenant",
           reference_id=str(request_id), meta={"request_number": req.request_number})
    await db.commit()

    return ok(_customer_limited_view(req), _rid(r), "compliance_provider")


@router.post("/customer-requests/{request_id}/tenant-response",
             summary="Add tenant-side context to a related customer request",
             response_model=ApiResponse[dict])
async def customer_tenant_response(
        request_id: uuid.UUID, r: Request,
        db: AsyncSession = Depends(get_db),
        u: UserContext = Depends(require_tenant_owner)) -> ApiResponse[dict]:

    tenant_id_str = _require_tenant(u)
    req = await db.scalar(
        select(ComplianceRequest).where(
            ComplianceRequest.id == request_id,
            ComplianceRequest.subject_type == "customer",
            ComplianceRequest.metadata_json["related_tenant_id"].astext == tenant_id_str))
    if not req:
        raise ServiceOSException("NOT_FOUND", "Customer request not found in your tenant scope.")

    body = await r.json()
    response_text = (body.get("response") or "").strip()[:2000]
    if not response_text:
        raise ServiceOSException("VALIDATION_ERROR", "response must not be empty.")

    meta = req.metadata_json or {}
    tenant_responses = meta.get("tenant_responses", [])
    tenant_responses.append({
        "response": response_text,
        "tenant_id": tenant_id_str,
        "actor_id": u.user_id,
        "added_at": utcnow().isoformat(),
    })
    req.metadata_json = {**meta, "tenant_responses": tenant_responses}

    _audit(db, uuid.UUID(tenant_id_str), uuid.UUID(u.user_id), u.role, get_client_ip(r),
           "compliance.tenant_response_added",
           reference_id=str(request_id), meta={})
    await db.commit()

    return ok({"response_added": True}, _rid(r), "compliance_provider")
