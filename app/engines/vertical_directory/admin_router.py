"""VERTICAL-DIRECTORY-FRAMEWORK: one reusable router serving Providers,
Staff, Customers and Complaints for EVERY Business Vertical -- the vertical
is resolved from the URL path segment server-side (never a client-supplied
query param), gated by VerticalScope (enabled + permission + membership)
before any query executes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.vertical_directory_scope import require_vertical_domain_scope, VerticalScope
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException
from app.engines.vertical_directory.service import (
    VerticalProviderDirectoryService, VerticalStaffDirectoryService,
    VerticalCustomerDirectoryService, VerticalComplaintWorkspaceService,
)

router = APIRouter(prefix="/v1/admin/verticals/{vertical}", tags=["Vertical Directory"])

_providers = VerticalProviderDirectoryService()
_staff = VerticalStaffDirectoryService()
_customers = VerticalCustomerDirectoryService()
_complaints = VerticalComplaintWorkspaceService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Providers ─────────────────────────────────────────────────────────────────

@router.get("/providers", response_model=ApiResponse)
async def list_providers(
    r: Request, search: str | None = Query(None), status: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("providers", "view")),
):
    return ok(await _providers.list_providers(db, scope, search=search, status=status,
                                              page=page, page_size=page_size), _rid(r))


@router.get("/providers/summary", response_model=ApiResponse)
async def providers_summary(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("providers", "view")),
):
    return ok(await _providers.get_summary(db, scope), _rid(r))


@router.get("/providers/{tenant_id}", response_model=ApiResponse)
async def get_provider(
    tenant_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("providers", "view")),
):
    return ok(await _providers.get_provider(db, scope, tenant_id), _rid(r))


# ── Staff ─────────────────────────────────────────────────────────────────────

@router.get("/staff", response_model=ApiResponse)
async def list_staff(
    r: Request, search: str | None = Query(None),
    verification_status: str | None = Query(None), assignment_status: str | None = Query(None),
    availability: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.list_staff(
        db, scope, search=search, verification_status=verification_status,
        assignment_status=assignment_status, availability=availability, page=page, page_size=page_size,
    ), _rid(r))


@router.get("/staff/summary", response_model=ApiResponse)
async def staff_summary(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_summary(db, scope), _rid(r))


# Must be registered BEFORE /staff/{staff_id} -- otherwise FastAPI tries to
# parse "export" as a uuid.UUID path param and 422s before this ever runs.
@router.get("/staff/export", response_model=ApiResponse)
async def staff_export(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "export")),
):
    data = await _staff.list_staff(db, scope, page=1, page_size=1000)
    return ok(data, _rid(r))


@router.get("/staff/{staff_id}", response_model=ApiResponse)
async def get_staff(
    staff_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_staff_detail(db, scope, staff_id), _rid(r))


@router.get("/staff/{staff_id}/capabilities", response_model=ApiResponse)
async def staff_capabilities(
    staff_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_capabilities(db, scope, staff_id), _rid(r))


@router.get("/staff/{staff_id}/workload", response_model=ApiResponse)
async def staff_workload(
    staff_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_workload(db, scope, staff_id), _rid(r))


@router.get("/staff/{staff_id}/performance", response_model=ApiResponse)
async def staff_performance(
    staff_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_performance(db, scope, staff_id), _rid(r))


@router.get("/staff/{staff_id}/activity", response_model=ApiResponse)
async def staff_activity(
    staff_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "audit")),
):
    return ok(await _staff.get_activity(db, scope, staff_id), _rid(r))


class StaffActionRequest(BaseModel):
    reason: str = ""


@router.post("/staff/{staff_id}/request-changes", response_model=ApiResponse)
async def staff_request_changes(
    staff_id: uuid.UUID, body: StaffActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "request_changes")),
):
    return ok(await _staff.request_changes(db, scope, staff_id, reason=body.reason, actor=scope.actor), _rid(r))


@router.post("/staff/{staff_id}/verify", response_model=ApiResponse)
async def staff_verify(
    staff_id: uuid.UUID, body: StaffActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "verify")),
):
    return ok(await _staff.verify(db, scope, staff_id, reason=body.reason, actor=scope.actor), _rid(r))


@router.post("/staff/{staff_id}/reject", response_model=ApiResponse)
async def staff_reject(
    staff_id: uuid.UUID, body: StaffActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "verify")),
):
    return ok(await _staff.reject(db, scope, staff_id, reason=body.reason, actor=scope.actor), _rid(r))


@router.post("/staff/{staff_id}/restrict", response_model=ApiResponse)
async def staff_restrict(
    staff_id: uuid.UUID, body: StaffActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "restrict")),
):
    return ok(await _staff.restrict(db, scope, staff_id, reason=body.reason, actor=scope.actor), _rid(r))


@router.post("/staff/{staff_id}/suspend", response_model=ApiResponse)
async def staff_suspend(
    staff_id: uuid.UUID, body: StaffActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "suspend")),
):
    return ok(await _staff.suspend(db, scope, staff_id, reason=body.reason, actor=scope.actor), _rid(r))


@router.post("/staff/{staff_id}/reactivate", response_model=ApiResponse)
async def staff_reactivate(
    staff_id: uuid.UUID, body: StaffActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "reactivate")),
):
    return ok(await _staff.reactivate(db, scope, staff_id, reason=body.reason, actor=scope.actor), _rid(r))


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/customers", response_model=ApiResponse)
async def list_customers(
    r: Request, search: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("customers", "view")),
):
    return ok(await _customers.list_customers(db, scope, search=search, page=page, page_size=page_size), _rid(r))


@router.get("/customers/summary", response_model=ApiResponse)
async def customers_summary(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("customers", "view")),
):
    return ok(await _customers.get_summary(db, scope), _rid(r))


@router.get("/customers/{customer_id}", response_model=ApiResponse)
async def get_customer(
    customer_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("customers", "view")),
):
    return ok(await _customers.get_customer(db, scope, customer_id), _rid(r))


# ── Complaints ────────────────────────────────────────────────────────────────

@router.get("/complaints", response_model=ApiResponse)
async def list_complaints(
    r: Request, search: str | None = Query(None), status: str | None = Query(None),
    severity: str | None = Query(None), complaint_type: str | None = Query(None),
    sla_status: str | None = Query(None), assigned_admin_id: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.list_complaints(
        db, scope, search=search, status=status, severity=severity, complaint_type=complaint_type,
        sla_status=sla_status, assigned_admin_id=assigned_admin_id, page=page, page_size=page_size,
    ), _rid(r))


@router.get("/complaints/summary", response_model=ApiResponse)
async def complaints_summary(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.get_summary(db, scope), _rid(r))


# Must be registered BEFORE /complaints/{complaint_id} -- otherwise FastAPI
# tries to parse "export" as a uuid.UUID path param and 422s before this runs.
@router.get("/complaints/export", response_model=ApiResponse)
async def export_complaints(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "export")),
):
    return ok(await _complaints.list_complaints(db, scope, page=1, page_size=1000), _rid(r))


@router.get("/complaints/{complaint_id}", response_model=ApiResponse)
async def get_complaint(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.get_complaint(db, scope, complaint_id), _rid(r))


@router.get("/complaints/{complaint_id}/job-context", response_model=ApiResponse)
async def get_complaint_job_context(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.get_job_context(db, scope, complaint_id), _rid(r))


@router.get("/complaints/{complaint_id}/evidence", response_model=ApiResponse)
async def get_complaint_evidence(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.list_evidence(db, scope, complaint_id), _rid(r))


@router.get("/complaints/{complaint_id}/conversation", response_model=ApiResponse)
async def get_complaint_conversation(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.list_conversation(db, scope, complaint_id), _rid(r))


@router.get("/complaints/{complaint_id}/timeline", response_model=ApiResponse)
async def get_complaint_timeline(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.list_timeline(db, scope, complaint_id), _rid(r))


@router.get("/complaints/{complaint_id}/resolution", response_model=ApiResponse)
async def get_complaint_resolution(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "view")),
):
    return ok(await _complaints.get_resolution(db, scope, complaint_id), _rid(r))


class ComplaintAssignRequest(BaseModel):
    assignee_id: str


class ComplaintActionRequest(BaseModel):
    reason: str = ""


class ComplaintMessageRequest(BaseModel):
    message_text: str
    internal_only: bool = True


class ComplaintResolutionRequest(BaseModel):
    resolution_type: str
    description: str
    customer_visible_notes: str | None = None
    internal_notes: str | None = None


class CustomerCreditRequest(BaseModel):
    amount: str
    reason: str


class TenantCreditAdjustmentRequest(BaseModel):
    direction: str
    credit_units: str
    reason_code: str
    detailed_reason: str


def _actor(scope: VerticalScope) -> uuid.UUID:
    if not scope.actor.user_id:
        raise ServiceOSException("VALIDATION_ERROR", "Actor identity required for this action.", status_code=422)
    return uuid.UUID(scope.actor.user_id)


@router.post("/complaints/{complaint_id}/assign", response_model=ApiResponse)
async def assign_complaint(
    complaint_id: uuid.UUID, body: ComplaintAssignRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "assign")),
):
    return ok(await _complaints.assign(db, scope, complaint_id, uuid.UUID(body.assignee_id), _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/request-response", response_model=ApiResponse)
async def request_complaint_response(
    complaint_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "message")),
):
    return ok(await _complaints.request_provider_response(db, scope, complaint_id, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/message", response_model=ApiResponse)
async def add_complaint_message(
    complaint_id: uuid.UUID, body: ComplaintMessageRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "message")),
):
    return ok(await _complaints.add_message(db, scope, complaint_id, body.message_text, body.internal_only, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/escalate", response_model=ApiResponse)
async def escalate_complaint(
    complaint_id: uuid.UUID, body: ComplaintActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "escalate")),
):
    return ok(await _complaints.escalate(db, scope, complaint_id, body.reason, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/propose-resolution", response_model=ApiResponse)
async def propose_complaint_resolution(
    complaint_id: uuid.UUID, body: ComplaintResolutionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "resolve")),
):
    return ok(await _complaints.propose_resolution(
        db, scope, complaint_id, resolution_type=body.resolution_type, description=body.description,
        customer_visible_notes=body.customer_visible_notes, internal_notes=body.internal_notes,
        actor_id=_actor(scope),
    ), _rid(r))


@router.post("/complaints/{complaint_id}/resolve", response_model=ApiResponse)
async def resolve_complaint(
    complaint_id: uuid.UUID, body: ComplaintActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "resolve")),
):
    return ok(await _complaints.resolve(db, scope, complaint_id, body.reason, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/close", response_model=ApiResponse)
async def close_complaint_route(
    complaint_id: uuid.UUID, body: ComplaintActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "resolve")),
):
    return ok(await _complaints.close(db, scope, complaint_id, body.reason, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/reject", response_model=ApiResponse)
async def reject_complaint_route(
    complaint_id: uuid.UUID, body: ComplaintActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "resolve")),
):
    return ok(await _complaints.reject(db, scope, complaint_id, body.reason, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/reopen", response_model=ApiResponse)
async def reopen_complaint_route(
    complaint_id: uuid.UUID, body: ComplaintActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "reopen")),
):
    return ok(await _complaints.reopen(db, scope, complaint_id, body.reason, _actor(scope)), _rid(r))


@router.post("/complaints/{complaint_id}/issue-customer-credit", response_model=ApiResponse)
async def issue_customer_credit_route(
    complaint_id: uuid.UUID, body: CustomerCreditRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "credit_issue")),
):
    return ok(await _complaints.issue_customer_credit(
        db, scope, complaint_id, amount=body.amount, reason=body.reason,
        actor_id=_actor(scope), actor_role=scope.actor.role, request_id=_rid(r),
    ), _rid(r))


@router.post("/complaints/{complaint_id}/apply-tenant-credit-adjustment", response_model=ApiResponse)
async def apply_tenant_credit_adjustment_route(
    complaint_id: uuid.UUID, body: TenantCreditAdjustmentRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("complaints", "credit_adjust")),
):
    return ok(await _complaints.apply_tenant_credit_adjustment(
        db, scope, complaint_id, direction=body.direction, credit_units=body.credit_units,
        reason_code=body.reason_code, detailed_reason=body.detailed_reason, actor_id=_actor(scope),
    ), _rid(r))
