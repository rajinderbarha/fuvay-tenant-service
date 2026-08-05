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
from app.engines.complaints.constants import ALLOWED_TRANSITIONS_EXT, FINAL_STATUSES
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
    """Real next-transition keys for this status -- the frontend must never
    write an arbitrary status string, only pick from what the backend allows."""
    if status in FINAL_STATUSES:
        return []
    return sorted(ALLOWED_TRANSITIONS_EXT.get(status, set()))


async def _job_snapshot(db: AsyncSession, job_id: uuid.UUID | None) -> dict | None:
    if not job_id:
        return None
    from app.engines.final_records.models import ServiceJob
    from app.engines.admin_catalog.models import MasterService
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember

    job = (await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))).scalars().first()
    if not job:
        return None
    ms_name = None
    if job.offering_id:
        ms = (await db.execute(select(MasterService).where(MasterService.id == job.offering_id))).scalars().first()
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
    return ok({
        **c.to_provider_dict(),
        "customer_alias": customer_alias(tenant_id, c.customer_id),
        "job": job,
        "available_actions": _available_actions(c.status),
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
