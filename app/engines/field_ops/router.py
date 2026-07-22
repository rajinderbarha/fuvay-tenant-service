"""Field Ops Engine — Router (23 endpoints). 23-status lifecycle."""
import uuid
from decimal import Decimal
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission, require_staff_or_above_mutation
from app.dependencies.auth import get_current_user, UserContext, require_super_admin, require_staff_or_technician_only, require_customer
from app.dependencies.db import get_db
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.billing_service import BillingService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, Links, Link, ok

logger = structlog.get_logger("fieldops.router")
router = APIRouter(prefix="/v1/jobs", tags=["Field Ops Engine", "Job Status Lifecycle"])
ENGINE_ID = "field_ops"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> FieldOpsService:
    return FieldOpsService(db=db, request_id=getattr(r.state,"request_id","—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
                            actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)

def _billing_svc(r: Request, db: AsyncSession = Depends(get_db),
                  u: UserContext = Depends(get_current_user)) -> BillingService:
    return BillingService(db=db, request_id=getattr(r.state,"request_id","—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
                           actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)

def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    from app.engines.field_ops.constants import ALLOWED_TRANSITIONS, JS
    return {"engine_id": ENGINE_ID, "name": "Field Ops Engine", "version": "8.0.0",
            "endpoint_count": 23, "status": "active", "status_count": 23,
            "statuses": list(ALLOWED_TRANSITIONS.keys()),
            "capabilities": ["23_status_lifecycle","transition_validation","atomic_close",
                             "commission_integration","sla_monitoring","customer_token",
                             "media_attachments","job_timeline","immutable_history"]}

@router.post("", summary="Create job from booking", status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_job(r: Request,
                      u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.create_job(uuid.UUID(body["tenant_id"]), body)
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[
                  Link(href=f"/v1/jobs/{data['job_id']}/status", method="PUT", rel="update_status"),
                  Link(href=f"/v1/dispatch/jobs/{data['job_id']}/dispatch", method="POST", rel="dispatch")]))

@router.get("/sla-alerts", summary="SLA breach alerts, tenant-scoped or platform-wide",
             response_model=ApiResponse[list[dict]])
async def sla_alerts(r: Request,
                      tenant_id: uuid.UUID | None = Query(None),
                      u: UserContext = Depends(get_current_user),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[list[dict]]:
    return ok(await s.get_sla_alerts(tenant_id), _rid(r), ENGINE_ID)

@router.get("/{job_id}", summary="Get job with status and allowed_transitions",
            response_model=ApiResponse[dict])
async def get_job(job_id: uuid.UUID, r: Request,
                   u: UserContext = Depends(get_current_user),
                   s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_job(job_id)
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[
                  Link(href=f"/v1/jobs/{job_id}/status", method="PUT", rel="update_status"),
                  Link(href=f"/v1/jobs/{job_id}/timeline", method="GET", rel="timeline")]))

@router.get("", summary="List jobs — tenant_owner (own tenant), staff (own assigned), "
                          "customer (own), super_admin (any) with filters",
            response_model=ApiResponse[dict])
async def list_jobs(r: Request,
                     tenant_id: uuid.UUID | None = Query(None),
                     job_status: str | None = Query(None, alias="status"),
                     staff_id: uuid.UUID | None = Query(None),
                     job_type: str | None = Query(None),
                     service_id: uuid.UUID | None = Query(None),
                     city: str | None = Query(None),
                     zipcode: str | None = Query(None),
                     scheduled_from: str | None = Query(None),
                     scheduled_to: str | None = Query(None),
                     search: str | None = Query(None),
                     limit: int = Query(50,ge=1,le=200),
                     cursor: str | None = Query(None),
                     u: UserContext = Depends(get_current_user),
                     s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # super_admin may omit tenant_id to see all jobs (routes to admin list)
    if tenant_id is None and u.role == "super_admin":
        return ok(await s.list_jobs_admin(None, job_status, limit, cursor), _rid(r), ENGINE_ID)
    if tenant_id is None:
        raise ServiceOSException("TENANT_REQUIRED", "tenant_id is required for this role.", status_code=422)
    return ok(await s.list_jobs(tenant_id, job_status, staff_id, limit, cursor,
                                 job_type, service_id, city, zipcode,
                                 scheduled_from, scheduled_to, search), _rid(r), ENGINE_ID)

@router.get("/admin/summary", summary="Platform-wide ops board summary counts",
             response_model=ApiResponse[dict])
async def ops_summary(r: Request,
                       tenant_id: uuid.UUID | None = Query(None),
                       u: UserContext = Depends(require_super_admin),
                       s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_ops_summary(tenant_id), _rid(r), ENGINE_ID)

@router.get("/admin/all", summary="Cross-tenant job queue (Super Admin) — platform-wide or filtered to one tenant",
             response_model=ApiResponse[dict])
async def list_jobs_admin(r: Request,
                           tenant_id: uuid.UUID | None = Query(None),
                           job_status: str | None = Query(None, alias="status"),
                           limit: int = Query(50, ge=1, le=200),
                           cursor: str | None = Query(None),
                           q: str | None = Query(None),
                           job_type: str | None = Query(None),
                           sla_status: str | None = Query(None),
                           unassigned: bool = Query(False),
                           date_from: str | None = Query(None),
                           date_to: str | None = Query(None),
                           sort_by: str = Query("created_at"),
                           sort_dir: str = Query("desc"),
                           page: int = Query(1, ge=1),
                           page_size: int = Query(50, ge=1, le=200),
                           u: UserContext = Depends(require_super_admin),
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_jobs_admin(
        tenant_id, job_status, limit, cursor,
        q=q, job_type=job_type, sla_status=sla_status, unassigned=unassigned,
        date_from=date_from, date_to=date_to, sort_by=sort_by, sort_dir=sort_dir,
        page=page, page_size=page_size,
    ), _rid(r), ENGINE_ID)

@router.get("/staff/{staff_id}/earnings",
             summary="Technician's own completed-job earnings summary",
             response_model=ApiResponse[dict])
async def staff_earnings(staff_id: uuid.UUID, r: Request,
                          tenant_id: uuid.UUID = Query(...),
                          u: UserContext = Depends(get_current_user),
                          s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_staff_earnings(staff_id, tenant_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/assign", tags=["Job Assignment"],
             summary="Step 6: Tenant owner assigns job to an active staff member of their own tenant",
             response_model=ApiResponse[dict])
async def assign_job(job_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_ASSIGN)),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.assign_staff(job_id, uuid.UUID(body["staff_id"]), body.get("notes"))
    return ok(data, _rid(r), ENGINE_ID)

@router.post("/{job_id}/accept", tags=["Staff Jobs"],
             summary="Step 6: Staff accepts an assigned job",
             response_model=ApiResponse[dict])
async def accept_job(job_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_staff_or_technician_only),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.accept_job(job_id, body.get("notes")), _rid(r), ENGINE_ID)

@router.post("/{job_id}/reject-assignment", tags=["Staff Jobs"],
             summary="Step 6: Staff rejects an assigned job — reason required",
             response_model=ApiResponse[dict])
async def reject_assignment(job_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_staff_or_technician_only),
                             s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_assignment(job_id, body.get("reason")), _rid(r), ENGINE_ID)

@router.put("/{job_id}/status",
            summary="Transition job status — validated against TRANSITIONS_BY_JOB_TYPE",
            response_model=ApiResponse[dict])
async def update_status(job_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_UPDATE)),
                         s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.update_status(job_id, body["to_status"], body.get("reason"),
                                  body.get("latitude"), body.get("longitude"),
                                  body.get("emergency_assessment", False))
    return ok(data, _rid(r), ENGINE_ID)

# ── Step 7: Assessment workflow (repair / consultation) ──────────────────────
@router.post("/{job_id}/assessment/start", tags=["Job Assessment"],
             summary="Step 7: Assigned staff starts assessment (job must be 'arrived')",
             response_model=ApiResponse[dict])
async def start_assessment(job_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_staff_or_technician_only),
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-14A: this is the same assigned-technician job-execution
    # capability class as accept_job/complete_checklist (fixed in 2F-14) --
    # _get_job_for_staff_action already made this safe via ID-equality (no
    # other role's actor_id can equal a staff assignment), but it had no named
    # role dependency, unlike its siblings. Added for consistency and runtime
    # tool visibility, not because a live bypass existed.
    return ok(await s.start_assessment(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/assessment/complete", tags=["Job Assessment"],
             summary="Step 7: Assigned staff completes assessment with findings/recommendation",
             response_model=ApiResponse[dict])
async def complete_assessment(job_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_staff_or_technician_only),
                               s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-14A: same reasoning as start_assessment above.
    body = await r.json()
    labour = body.get("labour_estimate")
    parts = body.get("parts_estimate")
    data = await s.complete_assessment(
        job_id, body.get("findings"), body.get("recommended_work"),
        body.get("estimated_parts", []),
        Decimal(str(labour)) if labour is not None else None,
        Decimal(str(parts)) if parts is not None else None,
        body.get("quote_required", False))
    return ok(data, _rid(r), ENGINE_ID)

# ── Step 7: Job Quotes (richer line-item quotes) ──────────────────────────────
@router.post("/{job_id}/quotes", tags=["Job Quotes"],
             summary="Step 7: Create a line-item quote after assessment is complete",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_job_quote(job_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_staff_or_above_mutation),
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-14B: quote administration is a provider-only, tenant-scoped
    # capability; require_staff_or_above_mutation (excludes customer, denies
    # read-only tenant access-scope) makes that persona/scope check tool-visible
    # at the router level, in front of the newly-hardened
    # _get_job_for_quote_management object-ownership check.
    body = await r.json()
    return ok(await s.create_job_quote(job_id, body), _rid(r), ENGINE_ID)

@router.get("/{job_id}/quotes", tags=["Job Quotes"],
            summary="Step 7: List quotes for a job (newest first)",
            response_model=ApiResponse[dict])
async def list_job_quotes(job_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_job_quotes(job_id), _rid(r), ENGINE_ID)

@router.get("/{job_id}/quotes/{quote_id}", tags=["Job Quotes"],
            summary="Step 7: Get a single job quote",
            response_model=ApiResponse[dict])
async def get_job_quote(job_id: uuid.UUID, quote_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job_quote(job_id, quote_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/quotes/{quote_id}/send", tags=["Job Quotes"],
             summary="Step 7: Staff/tenant sends the quote to the customer",
             response_model=ApiResponse[dict])
async def send_job_quote(job_id: uuid.UUID, quote_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_staff_or_above_mutation),
                          s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.send_job_quote(job_id, quote_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/quotes/{quote_id}/approve", tags=["Job Quotes"],
             summary="Step 7: Customer approves their own quote",
             response_model=ApiResponse[dict])
async def approve_job_quote(job_id: uuid.UUID, quote_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_customer),
                             s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.approve_job_quote(job_id, quote_id, uuid.UUID(u.user_id)), _rid(r), ENGINE_ID)

@router.post("/{job_id}/quotes/{quote_id}/reject", tags=["Job Quotes"],
             summary="Step 7: Customer rejects their own quote",
             response_model=ApiResponse[dict])
async def reject_job_quote(job_id: uuid.UUID, quote_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_customer),
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_job_quote(job_id, quote_id, uuid.UUID(u.user_id), body.get("reason")),
              _rid(r), ENGINE_ID)

# ── Step 7: Consultation -> Repair conversion ─────────────────────────────────
@router.post("/{job_id}/convert-to-repair", tags=["Consultation Conversion"],
             summary="Step 7: Tenant owner converts an approved consultation into a repair job",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def convert_to_repair(job_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_ASSIGN)),
                             s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.convert_to_repair(
        job_id, body.get("repair_service_id"), body.get("scheduled_at"),
        body.get("assignment_mode", "manual"), body.get("assigned_staff_id"), body.get("notes"))
    return ok(data, _rid(r), ENGINE_ID)

# ── Step 8: Service checklist execution (normalized job_checklist_items) ─────
@router.get("/{job_id}/checklist", tags=["Job Checklist"],
            summary="Step 8: Get a service job's checklist progress and items",
            response_model=ApiResponse[dict])
async def get_checklist(job_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job_checklist_items(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/checklist/start", tags=["Job Checklist"],
             summary="Step 8: Staff starts the service job's checklist "
                     "(lazily provisions items from the tenant's template)",
             response_model=ApiResponse[dict])
async def start_checklist(job_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_staff_or_technician_only),
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.start_job_checklist(job_id), _rid(r), ENGINE_ID)

@router.put("/{job_id}/checklist/items/{item_id}", tags=["Job Checklist"],
            summary="Step 8: Mark a single checklist item complete/incomplete "
                    "(validates requires_note / requires_photo)",
            response_model=ApiResponse[dict])
async def update_checklist_item(job_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_staff_or_technician_only),
                                 s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.update_job_checklist_item(
        job_id, item_id, body.get("is_completed", True),
        body.get("notes"), body.get("photo_urls"))
    return ok(data, _rid(r), ENGINE_ID)

@router.post("/{job_id}/checklist/complete", tags=["Job Checklist"],
             summary="Step 8: Complete the service job's checklist (all required items must be done)",
             response_model=ApiResponse[dict])
async def complete_checklist(job_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_staff_or_technician_only),
                              s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.complete_job_checklist(job_id), _rid(r), ENGINE_ID)

@router.get("/{job_id}/history", tags=["Job Status Lifecycle"],
            summary="Step 6: Job status history (tenant_owner/staff/customer scoped)",
            response_model=ApiResponse[dict])
async def get_history(job_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job_history(job_id), _rid(r), ENGINE_ID)

@router.get("/{job_id}/valid-next-statuses", tags=["Job Status Lifecycle"],
            summary="Step 6: Valid next statuses for the current job status",
            response_model=ApiResponse[dict])
async def valid_next_statuses(job_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(get_current_user),
                               s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_valid_next_statuses(job_id), _rid(r), ENGINE_ID)

@router.get("/{job_id}/transitions",
            summary="Get allowed transitions for current job status",
            response_model=ApiResponse[dict])
async def get_transitions(job_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_allowed_transitions(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/findings",
             summary="Technician submits assessment findings (repair/consultation)",
             response_model=ApiResponse[dict])
async def submit_findings(job_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_staff_or_technician_only),
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.submit_findings(job_id, body["findings"], body.get("recommendation")),
              _rid(r), ENGINE_ID)

@router.put("/{job_id}/checklist",
            summary="Update a service/maintenance job's checklist",
            response_model=ApiResponse[dict])
async def update_checklist(job_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_staff_or_technician_only),
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_checklist(job_id, body["items"]), _rid(r), ENGINE_ID)

@router.post("/{job_id}/quote",
             summary="Send a price quote to the customer (repair: if needed, consultation: always)",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_quote(job_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_staff_or_above_mutation),
                        s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    labour = body.get("labour_estimate")
    return ok(await s.create_quote(
        job_id, Decimal(str(body["amount"])), body.get("parts", []),
        Decimal(str(labour)) if labour is not None else None,
        body.get("notes"), body.get("expiry_days", 7),
    ), _rid(r), ENGINE_ID)

@router.post("/quotes/{quote_id}/respond",
             summary="Customer approves or rejects a quote — approving a consultation's "
                     "quote spawns a new follow-up repair job",
             response_model=ApiResponse[dict])
async def respond_to_quote(quote_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_customer),
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-14B: this previously let ANY non-customer authenticated caller
    # (staff, tenant_owner, technician) supply an arbitrary customer_id in the
    # request body and have the service record an "approved"/"rejected"
    # decision indistinguishable from a genuine customer decision -- a
    # customer-impersonation defect. No established offline-decision policy
    # (a distinct audit trail, a separate endpoint, product documentation)
    # exists for a provider to record a customer's decision on their behalf,
    # so this is closed as a straightforward customer-only self-service route:
    # customer_id is always derived from the authenticated principal.
    body = await r.json()
    customer_id = uuid.UUID(u.user_id)
    return ok(await s.respond_to_quote(quote_id, customer_id, body["approved"]), _rid(r), ENGINE_ID)

@router.post("/{job_id}/spawn-repair",
             summary="Manually spawn a repair job from a consultation (any time, not just on quote approval)",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def spawn_repair(job_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                        s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.spawn_repair_from_consultation(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/close", tags=["Job Financial Closure"],
             summary="Step 9: Close a paid job with commission deducted (closure_notes)",
             response_model=ApiResponse[dict])
async def close_job(job_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_CLOSE)),
                     s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.close_job_financial(job_id, body.get("closure_notes")), _rid(r), ENGINE_ID)

# ── Step 9: Payment / Invoice / Commission Closure Flow ──────────────────────
@router.post("/{job_id}/generate-invoice", tags=["Invoices"],
             summary="Step 9: Generate an invoice for a signed-off/completed job",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def generate_invoice(job_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_CLOSE)),
                            s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.generate_invoice(job_id, body), _rid(r), ENGINE_ID)

@router.post("/{job_id}/record-payment", tags=["Payments"],
             summary="Step 9: Record an on-site/manual payment against a job's invoice",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def record_payment(job_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_CLOSE)),
                          s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.record_payment(job_id, body), _rid(r), ENGINE_ID)

@router.post("/{job_id}/deduct-commission", tags=["Commission"],
             summary="Step 9: Deduct platform commission from the tenant wallet for this job",
             response_model=ApiResponse[dict])
async def deduct_commission(job_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_CLOSE)),
                             s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    return ok(await s.deduct_commission(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/financial-close", tags=["Job Financial Closure"],
             summary="Step 9: Atomic invoice -> payment -> commission -> close in one call",
             response_model=ApiResponse[dict])
async def financial_close(job_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_tenant_mutation_permission(P.FIELD_OPS_JOBS_CLOSE)),
                           s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.financial_close(job_id, body), _rid(r), ENGINE_ID)

@router.get("/{job_id}/invoice", tags=["Invoices"],
            summary="Step 9: Get the invoice generated for this job (tenant/staff view)",
            response_model=ApiResponse[dict])
async def get_job_invoice_for_tenant(job_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_permission(P.FIELD_OPS_JOBS_CLOSE)),
                                      s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    job = await s._get_job_for_billing(job_id)
    if not job.invoice_id:
        raise ServiceOSException("INVOICE_NOT_FOUND", "No invoice has been generated for this job yet.",
                                  status_code=404)
    from app.engines.payment.models import InvoiceRecord
    from sqlalchemy import select
    r2 = await s.db.execute(select(InvoiceRecord).where(InvoiceRecord.id == job.invoice_id))
    inv = r2.scalar_one_or_none()
    return ok(s._invoice_dict(inv), _rid(r), ENGINE_ID)

@router.post("/{job_id}/void", summary="Void job (cannot void while work in progress)",
             response_model=ApiResponse[dict])
async def void_job(job_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                    s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.void_job(job_id, body.get("reason","Voided by admin")), _rid(r), ENGINE_ID)

@router.get("/{job_id}/timeline", summary="Full immutable status history",
            response_model=ApiResponse[dict])
async def get_timeline(job_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job_timeline(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/notes", status_code=status.HTTP_201_CREATED,
             summary="Add note to job", response_model=ApiResponse[dict])
async def add_note(job_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(require_staff_or_above_mutation),
                    s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-14A: tenant_id is no longer accepted from the client -- it is
    # derived server-side from the job row (see FieldOpsService.add_note),
    # closing a tenant-spoofing/ownership gap.
    # Slice 2F-14C: router-level persona/mutation-scope enforcement added --
    # require_staff_or_above_mutation (excludes customer, denies read-only
    # tenant access-scope) makes canonical persona enforcement tool-visible,
    # in front of the pre-existing service-level _assert_can_access_job +
    # customer-denial (which remain unmodified object-ownership checks, not
    # replaced by this router-level guard).
    body = await r.json()
    return ok(await s.add_note(job_id, body["content"],
              body.get("note_type","staff_note"), body.get("is_internal",True)), _rid(r), ENGINE_ID)

@router.get("/{job_id}/notes", summary="List all notes for a job",
            response_model=ApiResponse[dict])
async def list_notes(job_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_notes(job_id), _rid(r), ENGINE_ID)

@router.post("/{job_id}/media", status_code=status.HTTP_201_CREATED,
             summary="Attach media to job at current status checkpoint",
             response_model=ApiResponse[dict])
async def add_media(job_id: uuid.UUID, r: Request,
                     u: UserContext = Depends(require_staff_or_above_mutation),
                     s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-14A: tenant_id is no longer accepted from the client -- see
    # FieldOpsService.add_media.
    # Slice 2F-14C: router-level persona/mutation-scope enforcement added --
    # same reasoning as add_note above.
    body = await r.json()
    return ok(await s.add_media(job_id,
              uuid.UUID(body["media_id"]) if body.get("media_id") else None,
              body.get("media_type","photo"), body.get("caption"),
              body.get("storage_key")), _rid(r), ENGINE_ID)

@router.get("/{job_id}/media", summary="List media attachments by status",
            response_model=ApiResponse[dict])
async def list_media(job_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_media(job_id), _rid(r), ENGINE_ID)

@router.get("/{job_id}/sla", summary="Get SLA status and breach flag",
            response_model=ApiResponse[dict])
async def sla_status(job_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_sla_status(job_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/counts",
            summary="Job counts by status for dashboard", response_model=ApiResponse[dict])
async def job_counts(tenant_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job_counts_by_status(tenant_id), _rid(r), ENGINE_ID)

@router.get("/track/{token}",
            summary="Public job tracking by customer token — no auth required",
            response_model=ApiResponse[dict])
async def track_by_token(token: str, r: Request, db=Depends(get_db)) -> ApiResponse[dict]:
    s = FieldOpsService(db=db)
    return ok(await s.get_job_by_token(token), _rid(r), ENGINE_ID)
