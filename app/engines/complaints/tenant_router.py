"""Home Services Complaints & Resolution Center -- tenant-scoped read surface.

Phase 1: queue + case Overview/Job Context/Activity. Wraps the existing
canonical `app.engines.complaints` state machine/tables (CustomerComplaint,
ComplaintEvent, ...) -- no second complaint engine, no new status field.
Mutations (acknowledge/respond/propose-resolution/escalate/etc.) already
exist on `provider_router.py` and are reused there; this router adds the
read-side queue/case projections that page needs and that provider_router
didn't have (summary counts, filters, job-context join, masked customer
alias).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.constants import (
    ALLOWED_TRANSITIONS_EXT, FINAL_STATUSES, STATUS_RESOLUTION_PROPOSED,
    STATUS_AWAITING_CUSTOMER, STATUS_REWORK_APPROVED, STATUS_REFUND_REQUESTED,
    STATUS_REFUND_APPROVED, STATUS_RESOLVED, STATUS_SETTLED, STATUS_REFUND_RECORDED,
    RESOLVED_OR_FINAL_STATUSES, PROVIDER_RESOLUTION_OPTIONS,
    CUSTOMER_RESPONSE_EXPIRY_HOURS, RESOLVED_AUTO_CLOSE_HOURS,
)
from app.engines.tenant_engine.customer_operational_access_policy import customer_alias

router = APIRouter(prefix="/v1/tenant/home-services/complaints", tags=["tenant-complaints"])
_svc = ComplaintService()


def _rid(r: Request | None) -> str:
    return getattr(r.state, "request_id", "—") if r else "—"


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException(
            error_code="TENANT_SCOPE_VIOLATION",
            detail="No tenant context on this session.",
            status_code=403,
        )
    return user.tenant_id


def _available_actions(status: str) -> list[str]:
    """Actions THIS tenant can actually perform on a case in `status`.

    This reports only the real provider-side capabilities, gated on the state
    machine that enforces them:

      SEND_MESSAGE      -- POST /v1/provider/complaints/{id}/respond
      OFFER_RESOLUTION  -- POST /v1/provider/complaints/{id}/offer-resolution,
                           which transitions to resolution_proposed and is
                           therefore only legal from a status that permits it.
    """
    if status in FINAL_STATUSES:
        return []
    # A resolved or settled case stays open for follow-up messages until it
    # closes automatically; nothing else can happen to it.
    actions = ["SEND_MESSAGE"]
    if status in RESOLVED_OR_FINAL_STATUSES:
        return actions
    if STATUS_RESOLUTION_PROPOSED in ALLOWED_TRANSITIONS_EXT.get(status, set()):
        actions.append("OFFER_RESOLUTION")
    return actions


def _blocked_reason(status: str, actions: list[str]) -> str | None:
    """Why a case cannot be resolved yet, in the tenant's own terms.

    Without this the workspace can only show a missing button, which reads as
    a broken page rather than as "this case is waiting on someone else".
    """
    if status in FINAL_STATUSES:
        return None
    if "OFFER_RESOLUTION" in actions:
        return None
    if status in (STATUS_RESOLUTION_PROPOSED, STATUS_AWAITING_CUSTOMER):
        days = CUSTOMER_RESPONSE_EXPIRY_HOURS // 24
        return (
            "A resolution has been proposed and is with the customer. You can keep "
            f"replying while they decide. If they do not answer within {days} days "
            "the case resolves automatically."
        )
    # The remedy steps below are the provider's to finish, and the resolution
    # deadline keeps running until they are done -- the old copy said only that
    # the case had "moved into its remedy flow", which read as someone else's job.
    if status == STATUS_REWORK_APPROVED:
        return ("The customer accepted a free rework visit. Schedule it and mark it complete "
                "in Refunds & Warranty; completing it resolves this case.")
    if status == STATUS_REFUND_REQUESTED:
        return "The customer requested a refund. Approve or decline it in Refunds & Warranty."
    if status == STATUS_REFUND_APPROVED:
        return ("A refund is approved. Record the repayment in Refunds & Warranty; "
                "recording it resolves this case.")
    if status in (STATUS_RESOLVED, STATUS_SETTLED, STATUS_REFUND_RECORDED):
        return (f"This case is resolved. It closes automatically {RESOLVED_AUTO_CLOSE_HOURS} "
                "hours after resolution; you can still reply until then.")
    return None


async def _remedy(db: AsyncSession, complaint) -> dict | None:
    """The rework or refund this case is waiting on, and where to act on it.

    A case in a remedy status had no way to reach that remedy from the
    workspace, so finishing the job meant knowing to open a different page.
    """
    if complaint.status not in (STATUS_REWORK_APPROVED, STATUS_REFUND_REQUESTED, STATUS_REFUND_APPROVED):
        return None
    from app.engines.complaints.models import RefundRequest, ServiceReworkRequest
    if complaint.status == STATUS_REWORK_APPROVED:
        row = (await db.execute(
            select(ServiceReworkRequest).where(ServiceReworkRequest.complaint_id == complaint.id)
            .order_by(ServiceReworkRequest.created_at.desc()).limit(1)
        )).scalars().first()
        kind, mode = "rework", "rework"
    else:
        row = (await db.execute(
            select(RefundRequest).where(RefundRequest.complaint_id == complaint.id)
            .order_by(RefundRequest.created_at.desc()).limit(1)
        )).scalars().first()
        kind, mode = "refund", "refunds"
    if row is None:
        return None
    return {
        "kind": kind,
        "id": str(row.id),
        "status": row.status,
        "href": f"/provider/refund-requests?mode={mode}",
    }


async def _resolution_options(db: AsyncSession, complaint) -> list[dict]:
    """The remedies this provider can offer on this case, per policy."""
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService
    category_id = complaint.category_id if isinstance(complaint.category_id, uuid.UUID) else None
    policy = await ComplaintEligibilityService().get_complaint_policy(db, category_id, complaint.tenant_id)
    options = []
    for value, label in PROVIDER_RESOLUTION_OPTIONS:
        if value == "rework" and policy is not None and policy.allow_rework is False:
            continue
        if value == "refund" and policy is not None and policy.allow_refund_request is False:
            continue
        options.append({"value": value, "label": label, "requires_amount": value == "refund"})
    return options


async def _service_options(db: AsyncSession, tenant_id: str) -> list[dict]:
    """Services that actually appear in this tenant's complaints.

    Resolved through `tenant_services`, so the values line up exactly with the
    catalogue the Services & Pricing setup page manages, and a filter can never
    be set to something that returns nothing.
    """
    from sqlalchemy import text as _text
    # Facets come from the SAME column the filter matches on (cc.offering_id),
    # so every option offered is one that returns rows.
    rows = (await db.execute(_text(
        "SELECT DISTINCT cc.offering_id AS id, "
        "COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS name "
        "FROM customer_complaints cc "
        "LEFT JOIN tenant_services ts ON ts.id = cc.offering_id "
        "LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
        "WHERE cc.tenant_id = :tid AND cc.offering_id IS NOT NULL ORDER BY name"
    ), {"tid": str(tenant_id)})).fetchall()
    return [{"id": str(r.id), "name": r.name} for r in rows]


async def _complaint_type_options(db: AsyncSession, tenant_id: str) -> list[str]:
    from sqlalchemy import text as _text
    rows = (await db.execute(_text(
        "SELECT DISTINCT complaint_type FROM customer_complaints "
        "WHERE tenant_id = :tid AND complaint_type IS NOT NULL ORDER BY complaint_type"
    ), {"tid": str(tenant_id)})).fetchall()
    return [r.complaint_type for r in rows]


async def _job_snapshot(db: AsyncSession, job_id: uuid.UUID | None) -> dict | None:
    if not job_id:
        return None
    from app.engines.final_records.models import ServiceJob
    from app.engines.admin_catalog.models import MasterService
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember

    job = (await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))).scalars().first()
    if not job:
        return None
    # `service_jobs.offering_id` is a TENANT_SERVICES id, not a master_services
    # id -- looking MasterService up by it directly never matched a row, so the
    # service name was silently None on every complaint in the queue and in the
    # case header. Resolve it the same way the reviews workspace does: through
    # tenant_services, preferring the tenant's own display name (what the
    # Services & Pricing setup page configures) and falling back to the master
    # catalogue name.
    ms_name = None
    if job.offering_id:
        from app.engines.admin_catalog.models import TenantService
        ts = (await db.execute(
            select(TenantService).where(TenantService.id == job.offering_id)
        )).scalars().first()
        if ts:
            ms_name = ts.tenant_display_name
            if not ms_name and ts.master_service_id:
                ms = (await db.execute(
                    select(MasterService).where(MasterService.id == ts.master_service_id)
                )).scalars().first()
                ms_name = ms.service_name if ms else None
    staff_name = None
    if job.assigned_staff_id:
        staff = (await db.execute(
            select(ProviderTeamMember).where(ProviderTeamMember.id == job.assigned_staff_id)
        )).scalars().first()
        staff_name = staff.full_name if staff else None
    return {
        "job_id": str(job.id),
        "job_number": job.job_number,
        "master_service_name": ms_name,
        "technician_name": staff_name,
        "status": job.status,
        "assignment_status": job.assignment_status,
        "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
    }


# ── Queue ────────────────────────────────────────────────────────────────────
@router.get("")
async def list_complaints(
    search: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    sla_state: Optional[str] = None,
    service_id: Optional[uuid.UUID] = None,
    complaint_type: Optional[str] = None,
    cursor: int = 0,
    limit: int = 20,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    summary = await _svc.tenant_queue_summary(db, tenant_id)
    complaints, total = await _svc.tenant_list_complaints(
        db, tenant_id, search=search, status=status, severity=severity,
        sla_status=sla_state, service_offering_id=service_id,
        complaint_type=complaint_type,
        cursor=cursor, limit=limit,
    )

    items = []
    for c in complaints:
        job = await _job_snapshot(db, c.job_id)
        items.append({
            **c.to_provider_dict(),
            "customer_alias": customer_alias(tenant_id, c.customer_id),
            "job_number": job["job_number"] if job else None,
            "master_service_name": job["master_service_name"] if job else None,
            "available_actions": _available_actions(c.status),
        })

    return ok({
        "summary": summary,
        "complaints": items,
        "available_filters": {
            "status": sorted({s for grp in ALLOWED_TRANSITIONS_EXT.values() for s in grp} | {"open"}),
            "severity": ["low", "medium", "high", "critical"],
            "sla_state": ["on_time", "at_risk", "breached", "escalated"],
            "complaint_type": await _complaint_type_options(db, tenant_id),
            # The `service_id` query parameter was already supported but had no
            # facet to drive a picker, so the filter was unreachable from the UI.
            "services": await _service_options(db, tenant_id),
        },
        "pagination": {"cursor": cursor, "limit": limit, "total": total, "has_next": cursor + limit < total},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, _rid(r), "tenant.complaints.list")


# ── Case detail ──────────────────────────────────────────────────────────────
@router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: uuid.UUID,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    c = await _svc.provider_get_complaint(db, tenant_id, complaint_id)
    await _svc.check_and_update_sla(db, c)
    await db.commit()
    job = await _job_snapshot(db, c.job_id)
    actions = _available_actions(c.status)
    return ok({
        **c.to_provider_dict(),
        "customer_alias": customer_alias(tenant_id, c.customer_id),
        "job": job,
        "available_actions": actions,
        "action_blocked_reason": _blocked_reason(c.status, actions),
        "available_resolution_types": (
            await _resolution_options(db, c) if "OFFER_RESOLUTION" in actions else []
        ),
        "remedy": await _remedy(db, c),
    }, _rid(r), "tenant.complaints.get")


@router.get("/{complaint_id}/job-context")
async def get_job_context(
    complaint_id: uuid.UUID,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    c = await _svc.provider_get_complaint(db, tenant_id, complaint_id)
    if not c.job_id:
        return ok({"available": False, "reason": "No job is linked to this complaint."}, _rid(r), "tenant.complaints.job_context")

    from app.engines.final_records.models import ServiceJob
    from app.engines.invoice_payment.models import ServicePaymentRecord

    job = (await db.execute(select(ServiceJob).where(ServiceJob.id == c.job_id))).scalars().first()
    if not job:
        return ok({"available": False, "reason": "Linked job record could not be found."}, _rid(r), "tenant.complaints.job_context")

    snapshot = await _job_snapshot(db, c.job_id)
    payments = (await db.execute(
        select(ServicePaymentRecord).where(ServicePaymentRecord.job_id == c.job_id)
    )).scalars().all()

    return ok({
        "available": True,
        "job": {
            **snapshot,
            "category_id": str(job.category_id),
            "offering_id": str(job.offering_id),
            "city": job.city,
            "zipcode": job.zipcode,
            "completion_data": job.completion_data,
        },
        "direct_payments": [{
            "payment_id": str(p.id),
            "payment_mode": p.payment_mode,
            "payment_status": p.payment_status,
            "collected_amount": str(p.collected_amount),
            "customer_confirmed": p.customer_confirmed,
            "provider_confirmed_at": p.provider_confirmed_at.isoformat() if p.provider_confirmed_at else None,
        } for p in payments],
    }, _rid(r), "tenant.complaints.job_context")


@router.get("/{complaint_id}/activity")
async def get_activity(
    complaint_id: uuid.UUID,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    await _svc.provider_get_complaint(db, tenant_id, complaint_id)
    events = await _svc.list_events(db, complaint_id)
    return ok({
        "items": [e.to_dict() for e in events],
    }, _rid(r), "tenant.complaints.activity")


@router.get("/{complaint_id}/evidence")
async def get_evidence(
    complaint_id: uuid.UUID,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Photos and documents attached to the case.

    `ComplaintService.list_media` already existed, but no provider router
    exposed it -- so evidence a customer
    attached to their complaint was stored and then unreachable by the
    provider who needs it to judge the case. The Evidence tab on the case
    workspace was a placeholder purely because this endpoint was missing.

    Scoped as `viewer="provider"`, which filters to case-visible media rather
    than returning internal attachments.
    """
    tenant_id = _tid(u)
    await _svc.provider_get_complaint(db, tenant_id, complaint_id)
    media = await _svc.list_media(db, complaint_id, viewer="provider")
    return ok({"items": [m.to_dict() for m in media]}, _rid(r), "tenant.complaints.evidence")
