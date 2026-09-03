"""TENANT-OPS-01 — Canonical Bookings & Jobs workspace projection.

GET /v1/tenant/home-services/bookings-jobs

Joins ServiceBooking + ServiceJob (1:1 via ServiceJob.booking_id) for the
authenticated tenant WITHOUT merging their identities: every row exposes
booking_id/booking_number AND service_job_id/job_number as distinct fields
(spec: "Do not merge IDs or copy one ID into another field"). Real
pagination, real tenant scoping, backend-computed display stage +
available_actions (see bookings_jobs_stage_mapping.py) reusing the actual
JOB_TRANSITIONS status machine already live in the execution engine — this
does not invent a parallel action or status system.

This projection is the provider command-center contract: accurate SQL-backed
stage/SLA/assignment/catalog/complaint filters, stable server pagination and
sorting, tenant-wide KPI aggregates, quick detail, audited address reveal,
workflow stages and direct-payment confirmation. Field execution remains in
the native staff app and assignment remains in the canonical Dispatch Board.
"""
from __future__ import annotations
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_staff_or_above, UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_owner_or_office_staff_mutation
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException
from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.engines.final_records.bookings_jobs_stage_mapping import (
    map_job_status, compute_available_actions, STAGE_STATUSES,
)
from app.engines.final_records.sla_summary import attach_sla, sla_filter_condition
from app.engines.final_records.bookings_jobs_kpis import compute_bookings_jobs_kpis
from app.engines.invoice_payment.models import ServiceInvoice
from app.engines.invoice_payment.payment_service import ServicePaymentService
from app.engines.complaints.models import CustomerComplaint
from app.engines.quote_checklist.models import ServiceJobQuote
from app.engines.admin_catalog.models import TenantService, MasterService, JobTypeDefinition
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.engines.tenant_engine.customer_operational_access_policy import (
    evaluate as _access_evaluate, customer_alias as _customer_alias,
    masked_locality as _masked_locality, sanitize_projection as _sanitize_projection,
)
from app.engines.tenant_engine.access_audit import record_address_access

_pay_svc = ServicePaymentService()


class ConfirmDirectPaymentRequest(BaseModel):
    payment_mode: Literal["onsite_cash", "onsite_upi", "onsite_card", "bank_transfer"] = "onsite_cash"
    collected_amount: float = Field(gt=0, le=100000000)
    proof_media_url: str | None = Field(default=None, max_length=1000)

router = APIRouter(
    prefix="/v1/tenant/home-services",
    tags=["Tenant Home Services — Bookings & Jobs"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


def _parse_date(value: str, field: str):
    from datetime import date as _date
    try:
        return _date.fromisoformat(value)
    except ValueError:
        raise ServiceOSException(error_code="INVALID_DATE", detail=f"{field} must be YYYY-MM-DD.", status_code=422)


def _tenant_id(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException(
            error_code="TENANT_CONTEXT_REQUIRED",
            detail="This workspace requires a tenant-scoped session.",
            status_code=403,
        )
    return uuid.UUID(str(user.tenant_id))


@router.get("/bookings-jobs", response_model=ApiResponse,
            summary="Canonical Bookings & Jobs workspace list (booking+job joined, not merged)")
async def list_bookings_jobs(
    r:        Request,
    search:   str | None = Query(None, description="job number / booking number / customer alias / technician"),
    stage:    str | None = Query(None, description="display stage — see bookings_jobs_stage_mapping.STAGE_LABELS"),
    status:   str | None = Query(None, description="raw ServiceJob.status"),
    assignment_status: str | None = Query(None),
    assigned_staff_id: uuid.UUID | None = Query(None),
    job_type_id: uuid.UUID | None = Query(None),
    offering_id: uuid.UUID | None = Query(None, description="Master Service filter"),
    sla:      str | None = Query(None, description="on_track | at_risk | breached (database-filtered before pagination)"),
    date_from: str | None = Query(None, description="scheduled_date >= (YYYY-MM-DD)"),
    date_to:   str | None = Query(None, description="scheduled_date <= (YYYY-MM-DD)"),
    has_complaint: bool | None = Query(None),
    sort_by: Literal["created_at", "scheduled_date", "updated_at", "job_number"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    limit:    int = Query(20, ge=1, le=100),
    offset:   int = Query(0, ge=0),
    user:     UserContext  = Depends(require_staff_or_above),
    db:       AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(user)

    # 1:1 join — ServiceJob.booking_id -> ServiceBooking.id. Both tables are
    # queried by tenant_id independently (both columns exist and are
    # populated identically at creation, final_creation_service.py) rather
    # than trusting only one side, matching the pattern already used by
    # final_records/provider_router.py.
    q = (
        select(ServiceJob, ServiceBooking)
        .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
        .where(ServiceJob.tenant_id == tenant_id, ServiceBooking.tenant_id == tenant_id)
    )
    count_q = (
        select(func.count())
        .select_from(ServiceJob)
        .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
        .where(ServiceJob.tenant_id == tenant_id, ServiceBooking.tenant_id == tenant_id)
    )

    if stage:
        stage_statuses = STAGE_STATUSES.get(stage)
        if not stage_statuses:
            raise ServiceOSException(error_code="INVALID_STAGE", detail="Unknown booking/job stage.", status_code=422)
        q = q.where(ServiceJob.status.in_(stage_statuses))
        count_q = count_q.where(ServiceJob.status.in_(stage_statuses))

    if status:
        q = q.where(ServiceJob.status == status)
        count_q = count_q.where(ServiceJob.status == status)
    if assignment_status:
        q = q.where(ServiceJob.assignment_status == assignment_status)
        count_q = count_q.where(ServiceJob.assignment_status == assignment_status)
    if assigned_staff_id:
        q = q.where(ServiceJob.assigned_staff_id == assigned_staff_id)
        count_q = count_q.where(ServiceJob.assigned_staff_id == assigned_staff_id)
    if job_type_id:
        q = q.where(ServiceJob.job_type_id == job_type_id)
        count_q = count_q.where(ServiceJob.job_type_id == job_type_id)
    if offering_id:
        q = q.where(ServiceJob.offering_id == offering_id)
        count_q = count_q.where(ServiceJob.offering_id == offering_id)
    if date_from:
        parsed_from = _parse_date(date_from, "date_from")
        q = q.where(ServiceJob.scheduled_date >= parsed_from)
        count_q = count_q.where(ServiceJob.scheduled_date >= parsed_from)
    if date_to:
        parsed_to = _parse_date(date_to, "date_to")
        q = q.where(ServiceJob.scheduled_date <= parsed_to)
        count_q = count_q.where(ServiceJob.scheduled_date <= parsed_to)
    if search:
        escaped = search.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        s = f"%{escaped}%"
        q = q.outerjoin(ProviderTeamMember, ProviderTeamMember.id == ServiceJob.assigned_staff_id)
        count_q = count_q.outerjoin(ProviderTeamMember, ProviderTeamMember.id == ServiceJob.assigned_staff_id)
        cond = or_(
            func.lower(ServiceJob.job_number).like(s, escape="\\"),
            func.lower(ServiceBooking.booking_number).like(s, escape="\\"),
            func.lower(ServiceBooking.customer_name).like(s, escape="\\"),
            func.lower(ServiceBooking.customer_phone).like(s, escape="\\"),
            func.lower(ProviderTeamMember.full_name).like(s, escape="\\"),
        )
        q = q.where(cond)
        count_q = count_q.where(cond)

    if sla:
        try:
            sla_condition = sla_filter_condition(ServiceJob, sla)
        except ValueError:
            raise ServiceOSException(error_code="INVALID_SLA_STATUS", detail="Unknown SLA status.", status_code=422)
        q = q.where(sla_condition)
        count_q = count_q.where(sla_condition)

    if has_complaint is not None:
        open_complaint = select(CustomerComplaint.id).where(
            CustomerComplaint.tenant_id == tenant_id,
            CustomerComplaint.job_id == ServiceJob.id,
            CustomerComplaint.status.notin_(("resolved", "closed", "withdrawn")),
        ).exists()
        q = q.where(open_complaint if has_complaint else ~open_complaint)
        count_q = count_q.where(open_complaint if has_complaint else ~open_complaint)

    total = await db.scalar(count_q) or 0

    sort_column = {
        "created_at": ServiceJob.created_at,
        "scheduled_date": ServiceJob.scheduled_date,
        "updated_at": ServiceJob.updated_at,
        "job_number": ServiceJob.job_number,
    }[sort_by]
    order = asc(sort_column) if sort_dir == "asc" else desc(sort_column)
    q = q.order_by(order.nulls_last(), ServiceJob.id.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).all()

    staff_uuid = uuid.UUID(user.user_id) if user.user_id else None
    is_dispatcher = str(user.role) in ("tenant_owner", "staff")

    # Batch SLA (2 queries total, not per-row) + batch open-complaint count --
    # same real projections used by the KPI strip and the detail panel, so
    # the row indicator, the summary tile and the panel can never disagree.
    page_jobs = [job for job, _booking in rows]
    sla_map = await attach_sla(db, page_jobs)
    job_ids = [job.id for job in page_jobs]
    complaint_counts: dict[str, int] = {}
    if job_ids:
        complaint_rows = (await db.execute(
            select(CustomerComplaint.job_id, func.count())
            .where(CustomerComplaint.tenant_id == tenant_id,
                   CustomerComplaint.job_id.in_(job_ids),
                   CustomerComplaint.status.notin_(("resolved", "closed", "withdrawn")))
            .group_by(CustomerComplaint.job_id)
        )).all()
        complaint_counts = {str(jid): cnt for jid, cnt in complaint_rows}

    # Batch-resolve real catalog names (Master Service + Job Type) rather
    # than showing the generic "Service" placeholder the old page used --
    # 2 more bounded queries, not per-row.
    offering_ids = {job.offering_id for job in page_jobs if job.offering_id}
    service_names: dict[str, str] = {}
    if offering_ids:
        svc_rows = (await db.execute(
            select(MasterService.id, MasterService.service_name).where(MasterService.id.in_(offering_ids))
        )).all()
        service_names = {str(sid): name for sid, name in svc_rows}
    job_type_ids = {job.job_type_id for job in page_jobs if job.job_type_id}
    job_type_labels: dict[str, str] = {}
    if job_type_ids:
        jt_rows = (await db.execute(
            select(JobTypeDefinition.id, JobTypeDefinition.label).where(JobTypeDefinition.id.in_(job_type_ids))
        )).all()
        job_type_labels = {str(jid): label for jid, label in jt_rows}

    staff_ids = {job.assigned_staff_id for job in page_jobs if job.assigned_staff_id}
    staff_names: dict[str, str] = {}
    if staff_ids:
        staff_rows = (await db.execute(
            select(ProviderTeamMember.id, ProviderTeamMember.full_name).where(
                ProviderTeamMember.tenant_id == tenant_id,
                ProviderTeamMember.id.in_(staff_ids),
            )
        )).all()
        staff_names = {str(sid): name for sid, name in staff_rows}

    items = []
    for job, booking in rows:
        stage_info = map_job_status(job.status, job.assignment_status)
        available_actions = compute_available_actions(job.status, job.assignment_status)

        # ── Field-level authorization: CustomerOperationalAccessPolicy is the
        # single source of truth for whether raw contact/exact-address may be
        # projected in this bulk list. A bulk exportable list is the highest-
        # value leak (marketplace poaching risk) — see
        # customer_operational_access_policy.py. Raw customer_name/phone are
        # NEVER included here regardless of decision; only the alias +
        # masked locality are ever shown in a list projection (spec: exact
        # address/contact is job-scoped only, never in directory/list rows).
        decision = _access_evaluate(
            tenant_id=tenant_id, job_tenant_id=job.tenant_id,
            staff_id=staff_uuid, assigned_staff_id=job.assigned_staff_id,
            customer_id=job.customer_id, job_status=job.status,
            job_updated_at=job.updated_at, is_dispatcher=is_dispatcher,
        )

        items.append({
            # ── canonical identity — booking and job kept distinct, never merged ──
            "booking_id":        str(booking.id),
            "booking_number":    booking.booking_number,
            "service_job_id":    str(job.id),
            "job_number":        job.job_number,
            "tenant_id":         str(tenant_id),
            "category_id":       str(job.category_id),
            "offering_id":       str(job.offering_id),
            "service_name":      service_names.get(str(job.offering_id)),
            "job_type_id":       str(job.job_type_id) if job.job_type_id else None,
            "job_type_label":    job_type_labels.get(str(job.job_type_id)) if job.job_type_id else None,
            "customer_id":       str(job.customer_id) if job.customer_id else None,
            "customer_alias":    _customer_alias(tenant_id, job.customer_id) if job.customer_id else None,
            "locality":          _masked_locality(job.city, job.zipcode),
            "access_reason_code": decision.reason_code.value,
            "city":              job.city,
            "zipcode":           job.zipcode,
            "scheduled_date":        job.scheduled_date.isoformat() if job.scheduled_date else None,
            "scheduled_time_window": job.scheduled_time_window,
            "assigned_staff_id": str(job.assigned_staff_id) if job.assigned_staff_id else None,
            "assigned_staff_name": staff_names.get(str(job.assigned_staff_id)) if job.assigned_staff_id else None,
            "assignment_status": job.assignment_status,
            "status":            job.status,
            "stage":             stage_info["stage"],
            "stage_label":       stage_info["stage_label"],
            "is_active":         stage_info["is_active"],
            "is_terminal":       stage_info["is_terminal"],
            "next_action":       stage_info["next_action"],
            "available_actions": available_actions,
            "sla":               sla_map.get(str(job.id)),
            "open_complaint_count": complaint_counts.get(str(job.id), 0),
            "created_at":        job.created_at.isoformat() if job.created_at else None,
            "updated_at":        job.updated_at.isoformat() if job.updated_at else None,
        })

    summary = await compute_bookings_jobs_kpis(db, tenant_id)

    # Real, tenant-wide catalog options for the Service filter dropdown --
    # not just the services present on the current page.
    available_service_rows = (await db.execute(
        select(TenantService.master_service_id, MasterService.service_name)
        .join(MasterService, MasterService.id == TenantService.master_service_id)
        .where(TenantService.tenant_id == tenant_id, TenantService.is_enabled == True)  # noqa: E712
        .distinct()
    )).all()

    available_staff_rows = (await db.execute(
        select(ProviderTeamMember.id, ProviderTeamMember.full_name)
        .where(
            ProviderTeamMember.tenant_id == tenant_id,
            ProviderTeamMember.deleted_at.is_(None),
            ProviderTeamMember.status == "active",
        )
        .order_by(ProviderTeamMember.full_name.asc())
    )).all()
    available_job_type_rows = (await db.execute(
        select(ServiceJob.job_type_id, JobTypeDefinition.label)
        .join(JobTypeDefinition, JobTypeDefinition.id == ServiceJob.job_type_id)
        .where(ServiceJob.tenant_id == tenant_id, ServiceJob.job_type_id.is_not(None))
        .distinct()
        .order_by(JobTypeDefinition.label.asc())
    )).all()

    return ok({
        "items":  items,
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "summary": summary,
        "available_filters": {
            "services": [{"offering_id": str(mid), "name": name} for mid, name in available_service_rows],
            "technicians": [{"staff_member_id": str(sid), "name": name} for sid, name in available_staff_rows],
            "job_types": [{"job_type_id": str(jid), "label": label} for jid, label in available_job_type_rows],
        },
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }, _RID(r), "final_records")


@router.get("/bookings-jobs/{job_id}", response_model=ApiResponse,
            summary="Quick-view detail for one job+booking pair")
async def get_bookings_jobs_detail(
    job_id: uuid.UUID,
    r:      Request,
    user:   UserContext  = Depends(require_staff_or_above),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(user)
    row = (await db.execute(
        select(ServiceJob, ServiceBooking)
        .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
        .where(ServiceJob.id == job_id, ServiceJob.tenant_id == tenant_id)
    )).first()
    if not row:
        raise ServiceOSException(error_code="JOB_NOT_FOUND",
                                  detail="Service job not found for this tenant.", status_code=404)
    job, booking = row
    stage_info = map_job_status(job.status, job.assignment_status)

    service_name = await db.scalar(
        select(MasterService.service_name).where(MasterService.id == job.offering_id)
    )
    job_type_label = None
    if job.job_type_id:
        job_type_label = await db.scalar(
            select(JobTypeDefinition.label).where(JobTypeDefinition.id == job.job_type_id)
        )

    invoice = (await db.execute(
        select(ServiceInvoice).where(
            ServiceInvoice.job_id == job_id, ServiceInvoice.tenant_id == tenant_id,
        ).order_by(ServiceInvoice.created_at.desc())
    )).scalars().first()

    # Current (is_current=True) quote/estimate for the Repair inspection
    # workflow -- the panel needs this to show estimate state + amount
    # without a second round-trip; version lineage (superseded quotes) is
    # already enforced at write time by quote_service.py, this only reads
    # the one row that's authoritative right now.
    quote = (await db.execute(
        select(ServiceJobQuote).where(
            ServiceJobQuote.job_id == job_id, ServiceJobQuote.tenant_id == tenant_id,
            ServiceJobQuote.is_current == True,  # noqa: E712
        )
    )).scalars().first()

    visit_fee = (await db.execute(
        select(TenantService.tenant_visit_fee).where(
            TenantService.tenant_id == tenant_id, TenantService.master_service_id == job.offering_id,
        )
    )).scalar()

    open_complaint_count = await db.scalar(
        select(func.count()).select_from(CustomerComplaint).where(
            CustomerComplaint.tenant_id == tenant_id, CustomerComplaint.job_id == job_id,
            CustomerComplaint.status.notin_(("resolved", "closed", "withdrawn")),
        )
    ) or 0

    sla = (await attach_sla(db, [job]))[str(job.id)]

    staff_uuid = uuid.UUID(user.user_id) if user.user_id else None
    is_dispatcher = str(user.role) in ("tenant_owner", "staff")
    decision = _access_evaluate(
        tenant_id=tenant_id, job_tenant_id=job.tenant_id,
        staff_id=staff_uuid, assigned_staff_id=job.assigned_staff_id,
        customer_id=job.customer_id, job_status=job.status,
        job_updated_at=job.updated_at, is_dispatcher=is_dispatcher,
    )
    booking_dict = _sanitize_projection(
        decision, booking.to_dict(), tenant_id=tenant_id, customer_id=job.customer_id,
        city=job.city, zipcode=job.zipcode,
    )
    job_dict = _sanitize_projection(
        decision, job.to_dict(), tenant_id=tenant_id, customer_id=job.customer_id,
        city=job.city, zipcode=job.zipcode,
    )

    from app.engines.admin_catalog.workflow_steps import (
        resolve_job_workflow_stages, to_client_stages,
    )
    _stages = await resolve_job_workflow_stages(db, job, "tenant")
    _tenant_stages = to_client_stages(_stages) if _stages else []

    return ok({
        "booking": booking_dict,
        "job":     job_dict,
        "service_name": service_name,
        "job_type_label": job_type_label,
        "stage":   stage_info,
        "available_actions": compute_available_actions(job.status, job.assignment_status),
        "invoice": invoice.to_dict() if invoice else None,
        "quote": quote.to_dict() if quote else None,
        "visit_fee": str(visit_fee) if visit_fee is not None else None,
        "open_complaint_count": open_complaint_count,
        "sla": sla,
        # The journey as the PROVIDER should see it — steps flagged
        # tenant_visible on this job's own snapshotted workflow. Empty when the
        # workflow defines no steps, so pre-migration-274 workflows are unaffected.
        "workflow_stages": _tenant_stages,
        "direct_payment_notice": "Customer pays the provider directly. Fuvay records confirmation only.",
    }, _RID(r), "final_records")


@router.get("/bookings-jobs/{job_id}/address", response_model=ApiResponse,
            summary="Separately-authorized exact service address (job-scoped, audited)")
async def get_job_exact_address(
    job_id: uuid.UUID,
    r:      Request,
    user:   UserContext  = Depends(require_staff_or_above),
    db:     AsyncSession = Depends(get_db),
):
    """Spec section 5 — exact address is NEVER in list/detail projections.
    It is fetched here only, gated by CustomerOperationalAccessPolicy, and
    every grant (or denial) writes a real audit row via
    app.engines.tenant_engine.access_audit.record_address_access."""
    tenant_id = _tenant_id(user)
    row = (await db.execute(
        select(ServiceJob, ServiceBooking)
        .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
        .where(ServiceJob.id == job_id, ServiceJob.tenant_id == tenant_id)
    )).first()
    if not row:
        raise ServiceOSException(error_code="JOB_NOT_FOUND",
                                  detail="Service job not found for this tenant.", status_code=404)
    job, booking = row

    staff_uuid = uuid.UUID(user.user_id) if user.user_id else None
    is_dispatcher = str(user.role) in ("tenant_owner", "staff")
    decision = _access_evaluate(
        tenant_id=tenant_id, job_tenant_id=job.tenant_id,
        staff_id=staff_uuid, assigned_staff_id=job.assigned_staff_id,
        customer_id=job.customer_id, job_status=job.status,
        job_updated_at=job.updated_at, is_dispatcher=is_dispatcher,
    )
    granted = "exact_address" in decision.allowed_fields

    await record_address_access(
        db, tenant_id=tenant_id, staff_id=staff_uuid, job_id=job_id,
        customer_id=job.customer_id, granted=granted,
        reason_code=decision.reason_code.value,
    )
    await db.commit()

    if not granted:
        return ok({
            "granted": False,
            "reason_code": decision.reason_code.value,
            "locality": _masked_locality(job.city, job.zipcode),
        }, _RID(r), "final_records")

    return ok({
        "granted": True,
        "reason_code": decision.reason_code.value,
        "access_expiry": decision.access_expiry.isoformat() if decision.access_expiry else None,
        "address_snapshot": booking.address_snapshot,
        "city": job.city,
        "zipcode": job.zipcode,
    }, _RID(r), "final_records")


@router.post("/bookings-jobs/{job_id}/confirm-payment", response_model=ApiResponse,
             summary="Provider confirms a direct customer payment for this job's invoice")
async def confirm_job_payment(
    job_id: uuid.UUID,
    body: ConfirmDirectPaymentRequest,
    r:    Request,
    user: UserContext  = Depends(require_owner_or_office_staff_mutation),
    db:   AsyncSession = Depends(get_db),
):
    """Thin adapter over the real, existing payment-confirmation service
    (ServicePaymentService.record_onsite_payment, also used by
    /v1/provider/service-invoices/{invoice_id}/record-payment) so the
    Bookings & Jobs quick view can confirm payment by job_id -- the identity
    it already has -- without the frontend needing to separately resolve an
    invoice_id first. Does not duplicate the payment logic itself: customer
    pays the tenant directly, this only records that confirmation and lets
    the existing commission/wallet debit run exactly as it already does for
    every other caller of record_onsite_payment. Never creates a Fuvay
    payout or gateway settlement record."""
    tenant_id = _tenant_id(user)
    job = (await db.execute(
        select(ServiceJob).where(ServiceJob.id == job_id, ServiceJob.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not job:
        raise ServiceOSException(error_code="JOB_NOT_FOUND",
                                  detail="Service job not found for this tenant.", status_code=404)

    invoice = (await db.execute(
        select(ServiceInvoice).where(
            ServiceInvoice.job_id == job_id, ServiceInvoice.tenant_id == tenant_id,
        ).order_by(ServiceInvoice.created_at.desc())
    )).scalars().first()
    if not invoice:
        raise ServiceOSException(error_code="PAYMENT_CONFIRMATION_REQUIRED",
                                  detail="No invoice exists yet for this job.", status_code=422)

    try:
        data = await _pay_svc.record_onsite_payment(
            db, str(invoice.id), str(tenant_id),
            payment_mode=body.payment_mode,
            collected_amount=body.collected_amount,
            proof_media_url=body.proof_media_url,
            user_id=str(user.user_id),
            staff_member_id=str(getattr(user, "staff_member_id", None) or user.user_id),
            request_id=_RID(r),
        )
    except ValueError as exc:
        code = str(exc)
        status = 404 if code in ("INVOICE_NOT_FOUND",) else (
            403 if code in ("INVOICE_ACCESS_DENIED",) else 422)
        raise ServiceOSException(error_code=code, detail=code.replace("_", " ").title(), status_code=status)

    return ok(data, _RID(r), "final_records")
