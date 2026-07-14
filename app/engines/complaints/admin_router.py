"""Sprint 25 + 75 — Admin Complaint APIs."""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
from typing import Optional
import uuid
from decimal import Decimal

from app.dependencies.auth import get_current_user, require_super_admin, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.constants import MONETARY_REMEDIES
from app.engines.complaints.rework_service import ServiceReworkService
from app.engines.complaints.refund_service import RefundRequestService

admin_complaint_router = APIRouter(prefix="/v1/admin/complaints",        tags=["admin-complaints"])
admin_rework_router    = APIRouter(prefix="/v1/admin/rework-requests",   tags=["admin-rework"])
admin_refund_router    = APIRouter(prefix="/v1/admin/refund-requests",   tags=["admin-refunds"])
admin_cpolicy_router   = APIRouter(prefix="/v1/admin/complaint-policies", tags=["admin-complaint-policies"])

_complaint = ComplaintService()
_rework    = ServiceReworkService()
_refund    = RefundRequestService()


def _rid(r):
    return getattr(r.state, "request_id", "—") if r else "—"


# ── Request bodies ────────────────────────────────────────────────────────────
class AssignIn(BaseModel):
    assignee_id: uuid.UUID


class PriorityIn(BaseModel):
    priority: str
    reason:   Optional[str] = None


class AdminMessageIn(BaseModel):
    message_text: str
    visibility:   Optional[str] = "admin_only"


class RejectComplaintIn(BaseModel):
    reason: str


class ProposeResolutionIn(BaseModel):
    resolution_type:        str
    description:            str
    customer_visible_notes: Optional[str] = None
    internal_notes:         Optional[str] = None


class ReasonIn(BaseModel):
    reason: Optional[str] = None


class ReworkApproveIn(BaseModel):
    admin_notes: Optional[str] = None


class ReworkAssignIn(BaseModel):
    staff_member_id: uuid.UUID


class RefundApproveIn(BaseModel):
    approved_amount: Optional[Decimal] = None


class RefundRejectIn(BaseModel):
    reason: str


class RefundRecordIn(BaseModel):
    recorded_amount: Decimal
    proof_media_url: Optional[str] = None


class PolicyIn(BaseModel):
    policy_key:                    Optional[str]  = None
    complaint_window_hours:        Optional[int]  = None
    allow_duplicate_open_complaints: Optional[bool] = None
    allow_rework_request:          Optional[bool] = None
    allow_refund_request:          Optional[bool] = None
    require_admin_review:          Optional[bool] = None
    is_active:                     Optional[bool] = None

    # ── The AI settlement rule — this is the ONLY thing the admin sets ─────────
    # Everything downstream is automatic: the AI takes over when the provider has
    # failed, offers at most `ai_settlement_max_pct` of the job value in credit
    # points, and hands anything bigger to a human.
    ai_settlement_enabled:             Optional[bool]    = None
    ai_auto_start_on_provider_failure: Optional[bool]    = None
    ai_settlement_max_pct:             Optional[Decimal] = None
    ai_settlement_allowed_remedies:    Optional[list[str]] = None
    settlement_payout_in_credits_only: Optional[bool]    = None

    @field_validator("ai_settlement_max_pct")
    @classmethod
    def _pct_range(cls, v):
        if v is not None and not (Decimal("0") <= v <= Decimal("100")):
            raise ValueError("ai_settlement_max_pct must be between 0 and 100")
        return v

    @field_validator("ai_settlement_allowed_remedies")
    @classmethod
    def _no_money(cls, v):
        """The platform never settles a dispute with real money — an admin cannot
        configure their way around that."""
        if v:
            bad = [r for r in v if r.lower() in MONETARY_REMEDIES]
            if bad:
                raise ValueError(
                    f"Settlements are paid in credit points, never money. "
                    f"Remedies not allowed: {', '.join(bad)}"
                )
        return v


class StartAISettlementIn(BaseModel):
    pass


class FinalizeSettlementIn(BaseModel):
    decision: str
    notes:    Optional[str] = None


class CreateSettlementProposalIn(BaseModel):
    proposal_type:   str
    description:     str
    proposal_amount: Optional[Decimal] = None
    conditions:      Optional[str]     = None


# ── Enterprise summary endpoint ───────────────────────────────────────────────
@admin_complaint_router.get("/summary")
async def complaints_summary(
    tenant_id: Optional[uuid.UUID] = Query(None),
    u = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    params: dict = {}
    where = "1=1"
    if tenant_id:
        where += " AND c.tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    sql = f"""
        SELECT
            COUNT(*)                                                             AS total,
            COUNT(*) FILTER (WHERE c.status = 'open')                           AS open,
            COUNT(*) FILTER (WHERE c.status NOT IN ('closed','cancelled','rejected','resolved','settled')) AS active,
            COUNT(*) FILTER (WHERE c.priority IN ('high','urgent'))             AS high_priority,
            COUNT(*) FILTER (WHERE c.status = 'under_admin_review')             AS pending_admin,
            COUNT(*) FILTER (WHERE c.status LIKE 'ai_%%')                       AS in_ai_settlement,
            COUNT(*) FILTER (WHERE c.status = 'resolved')                       AS resolved,
            COUNT(*) FILTER (WHERE c.status = 'settled')                        AS settled,
            COUNT(*) FILTER (WHERE c.created_at >= NOW() - INTERVAL '24 hours') AS new_today,
            COUNT(*) FILTER (WHERE c.created_at >= NOW() - INTERVAL '7 days')   AS new_this_week
        FROM customer_complaints c
        WHERE {where}
    """
    row = (await db.execute(text(sql), params)).mappings().one()
    data = {k: int(row[k] or 0) for k in row.keys()}
    # sla_breached: approximate via tenant_first_response_due_at when column exists
    try:
        sla_sql = f"""
            SELECT COUNT(*) AS sla_breached
            FROM customer_complaints c
            WHERE {where}
              AND c.tenant_first_response_due_at < NOW()
              AND c.status NOT IN ('closed','cancelled','rejected','resolved','settled')
        """
        sla_row = (await db.execute(text(sla_sql), params)).mappings().one()
        data["sla_breached"] = int(sla_row["sla_breached"] or 0)
    except Exception:
        data["sla_breached"] = 0
    return {"data": data}


# ── Enhanced platform-wide list ───────────────────────────────────────────────
@admin_complaint_router.get("/list")
async def list_complaints_enterprise(
    q:           Optional[str]       = Query(None),
    tenant_id:   Optional[uuid.UUID] = Query(None),
    status:      Optional[str]       = Query(None),
    priority:    Optional[str]       = Query(None),
    severity:    Optional[str]       = Query(None),
    sla_status:  Optional[str]       = Query(None),
    record_type: Optional[str]       = Query(None),
    complaint_type: Optional[str]    = Query(None),
    date_from:   Optional[str]       = Query(None),
    date_to:     Optional[str]       = Query(None),
    sort_by:     str                 = Query("created_at"),
    sort_dir:    str                 = Query("desc"),
    page:        int                 = Query(1, ge=1),
    page_size:   int                 = Query(25, ge=1, le=200),
    u = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    params: dict = {}
    conditions = ["1=1"]

    if q:
        conditions.append(
            "(c.complaint_number ILIKE :q OR c.title ILIKE :q OR c.description ILIKE :q "
            "OR cu.full_name ILIKE :q OR t.tenant_name ILIKE :q)"
        )
        params["q"] = f"%{q}%"
    if tenant_id:
        conditions.append("c.tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id
    if status:
        conditions.append("c.status = :status")
        params["status"] = status
    if priority:
        conditions.append("c.priority = :priority")
        params["priority"] = priority
    if severity:
        conditions.append("c.severity = :severity")
        params["severity"] = severity
    if sla_status:
        conditions.append("c.sla_status = :sla_status")
        params["sla_status"] = sla_status
    if record_type:
        conditions.append("c.record_type = :record_type")
        params["record_type"] = record_type
    if complaint_type:
        conditions.append("c.complaint_type = :complaint_type")
        params["complaint_type"] = complaint_type
    if date_from:
        conditions.append("c.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("c.created_at <= :date_to")
        params["date_to"] = date_to

    where = " AND ".join(conditions)

    _SORT_MAP = {
        "created_at": "c.created_at",
        "priority": "c.priority",
        "status": "c.status",
        "sla_status": "c.sla_status",
        "tenant_name": "t.tenant_name",
    }
    sort_col = _SORT_MAP.get(sort_by, "c.created_at")
    sort_sql  = f"{sort_col} {sort_dir.upper()} NULLS LAST"

    count_sql = f"""
        SELECT COUNT(*)
        FROM   customer_complaints c
        LEFT   JOIN tenants t ON t.id = c.tenant_id
        LEFT   JOIN users   cu ON cu.id = c.customer_id
        WHERE  {where}
    """
    total = int((await db.execute(text(count_sql), params)).scalar() or 0)

    offset = (page - 1) * page_size
    params["limit"]  = page_size
    params["offset"] = offset

    data_sql = f"""
        SELECT
            c.id, c.complaint_number, c.status, c.priority,
            COALESCE(c.severity, 'medium')    AS severity,
            COALESCE(c.sla_status, 'on_time') AS sla_status,
            c.complaint_type, c.record_type, c.title, c.description,
            c.tenant_first_response_due_at,   c.settlement_status,
            c.created_at, c.resolved_at, c.closed_at,
            t.tenant_name,
            cu.full_name  AS customer_name, cu.email AS customer_email,
            (SELECT COUNT(*) FROM complaint_messages cm WHERE cm.complaint_id = c.id) AS message_count
        FROM   customer_complaints c
        LEFT   JOIN tenants t  ON t.id = c.tenant_id
        LEFT   JOIN users   cu ON cu.id = c.customer_id
        WHERE  {where}
        ORDER  BY {sort_sql}
        LIMIT  :limit OFFSET :offset
    """
    rows = (await db.execute(text(data_sql), params)).mappings().all()

    def _fmt(row) -> dict:
        return {
            "id":             str(row["id"]),
            "complaint_number": row["complaint_number"],
            "status":         row["status"],
            "priority":       row["priority"],
            "severity":       row["severity"],
            "sla_status":     row["sla_status"],
            "complaint_type": row["complaint_type"],
            "record_type":    row["record_type"],
            "title":          row["title"],
            "description":    (row["description"] or "")[:120],
            "tenant_name":    row["tenant_name"],
            "customer_name":  row["customer_name"],
            "customer_email": row["customer_email"],
            "message_count":  int(row["message_count"] or 0),
            "proposal_count": 0,
            "settlement_status": row.get("settlement_status") if hasattr(row, "get") else None,
            "tenant_first_response_due_at": row["tenant_first_response_due_at"].isoformat() if row["tenant_first_response_due_at"] else None,
            "created_at":     row["created_at"].isoformat() if row["created_at"] else None,
            "resolved_at":    row["resolved_at"].isoformat() if row["resolved_at"] else None,
        }

    return {"data": {
        "items": [_fmt(r) for r in rows],
        "meta": {
            "page":        page,
            "page_size":   page_size,
            "total":       total,
            "total_pages": max(1, -(-total // page_size)),
            "has_next":    (page * page_size) < total,
            "has_previous": page > 1,
        },
    }}


# ── Admin Complaints ──────────────────────────────────────────────────────────
@admin_complaint_router.get("")
async def list_complaints(
    tenant_id:   Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    status:      Optional[str]       = None,
    priority:    Optional[str]       = None,
    record_type: Optional[str]       = None,
    limit:       int                 = 100,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    complaints = await _complaint.admin_list_complaints(
        db, tenant_id=tenant_id, customer_id=customer_id,
        status=status, priority=priority, record_type=record_type, limit=limit,
    )
    return ok([c.to_dict() for c in complaints], _rid(r), "admin.complaints.list")


@admin_complaint_router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.get_complaint(db, complaint_id)
    return ok(c.to_dict(), _rid(r), "admin.complaints.get")


@admin_complaint_router.post("/{complaint_id}/assign")
async def assign_complaint(
    complaint_id: uuid.UUID,
    body: AssignIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.admin_assign_complaint(db, u.user_id, complaint_id, body.assignee_id, request_id=_rid(r))
    return ok({"id": str(c.id), "assigned_admin_user_id": str(c.assigned_admin_user_id)}, _rid(r), "admin.complaint.assigned")


@admin_complaint_router.post("/{complaint_id}/priority")
async def change_priority(
    complaint_id: uuid.UUID,
    body: PriorityIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.admin_change_priority(db, u.user_id, complaint_id, body.priority, body.reason, request_id=_rid(r))
    return ok({"id": str(c.id), "priority": c.priority}, _rid(r), "admin.complaint.priority_changed")


@admin_complaint_router.post("/{complaint_id}/request-provider-response")
async def request_provider_response(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.admin_request_provider_response(db, u.user_id, complaint_id, request_id=_rid(r))
    return ok({"id": str(c.id), "status": c.status}, _rid(r), "admin.complaint.provider_response_requested")


@admin_complaint_router.post("/{complaint_id}/messages")
async def admin_add_message(
    complaint_id: uuid.UUID,
    body: AdminMessageIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    msg = await _complaint.admin_add_message(
        db, u.user_id, complaint_id, body.message_text, visibility=body.visibility, request_id=_rid(r)
    )
    return ok({"id": str(msg.id), "visibility": msg.visibility}, _rid(r), "admin.complaint.message.added")


@admin_complaint_router.get("/{complaint_id}/messages")
async def list_messages(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    msgs = await _complaint.list_messages(db, complaint_id, viewer="admin")
    return ok([{"id": str(m.id), "sender_type": m.sender_type, "message_text": m.message_text,
                "visibility": m.visibility, "created_at": str(m.created_at)} for m in msgs],
              _rid(r), "admin.complaint.messages.list")


@admin_complaint_router.post("/{complaint_id}/propose-resolution")
async def propose_resolution(
    complaint_id: uuid.UUID,
    body: ProposeResolutionIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await _complaint.admin_propose_resolution(
        db, u.user_id, complaint_id,
        body.resolution_type, body.description,
        customer_visible_notes=body.customer_visible_notes,
        internal_notes=body.internal_notes,
        request_id=_rid(r),
    )
    return ok({"id": str(res.id), "status": res.status}, _rid(r), "admin.resolution.proposed")


@admin_complaint_router.get("/{complaint_id}/resolutions")
async def list_resolutions(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    resolutions = await _complaint.list_resolutions(db, complaint_id)
    return ok([{"id": str(res.id), "status": res.status, "resolution_type": res.resolution_type,
                "description": res.description, "internal_notes": res.internal_notes,
                "customer_visible_notes": res.customer_visible_notes, "proposed_by_type": res.proposed_by_type,
                "created_at": str(res.created_at)} for res in resolutions], _rid(r), "admin.resolutions.list")


@admin_complaint_router.post("/{complaint_id}/reject")
async def reject_complaint(
    complaint_id: uuid.UUID,
    body: RejectComplaintIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.admin_reject_complaint(db, u.user_id, complaint_id, body.reason, request_id=_rid(r))
    return ok({"id": str(c.id), "status": c.status}, _rid(r), "admin.complaint.rejected")


@admin_complaint_router.post("/{complaint_id}/resolve")
async def resolve_complaint(
    complaint_id: uuid.UUID,
    body: ReasonIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.admin_resolve_complaint(db, u.user_id, complaint_id, reason=body.reason, request_id=_rid(r))
    return ok({"id": str(c.id), "status": c.status}, _rid(r), "admin.complaint.resolved")


@admin_complaint_router.post("/{complaint_id}/close")
async def close_complaint(
    complaint_id: uuid.UUID,
    body: ReasonIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.complaints.constants import ACTOR_ADMIN
    c = await _complaint.close_complaint(db, u.user_id, ACTOR_ADMIN, complaint_id,
                                         reason=body.reason, request_id=_rid(r))
    return ok({"id": str(c.id), "status": c.status}, _rid(r), "admin.complaint.closed")


@admin_complaint_router.get("/{complaint_id}/events")
async def list_events(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    events = await _complaint.list_events(db, complaint_id)
    return ok([{"id": str(e.id), "event_type": e.event_type, "actor_type": e.actor_type,
                "old_status": e.old_status, "new_status": e.new_status,
                "reason": e.reason, "created_at": str(e.created_at)} for e in events],
              _rid(r), "admin.complaint.events.list")


# ── Admin Rework Requests ─────────────────────────────────────────────────────
@admin_rework_router.get("")
async def list_rework_requests(
    tenant_id: Optional[uuid.UUID] = None,
    status:    Optional[str]       = None,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    reworks = await _rework.list_rework_requests(db, tenant_id=tenant_id, status=status)
    return ok([{"id": str(rw.id), "status": rw.status, "complaint_id": str(rw.complaint_id),
                "rework_reason": rw.rework_reason,
                "scheduled_date": str(rw.scheduled_date) if rw.scheduled_date else None,
                "created_at": str(rw.created_at)} for rw in reworks], _rid(r), "admin.rework.list")


@admin_rework_router.post("/{rework_id}/approve")
async def approve_rework(
    rework_id: uuid.UUID,
    body: ReworkApproveIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.approve_rework(db, rework_id, u.user_id, admin_notes=body.admin_notes, request_id=_rid(r))
    return ok({"id": str(rw.id), "status": rw.status}, _rid(r), "admin.rework.approved")


@admin_rework_router.post("/{rework_id}/reject")
async def reject_rework(
    rework_id: uuid.UUID,
    body: RejectComplaintIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.reject_rework(db, rework_id, u.user_id, body.reason, request_id=_rid(r))
    return ok({"id": str(rw.id), "status": rw.status}, _rid(r), "admin.rework.rejected")


@admin_rework_router.post("/{rework_id}/assign")
async def assign_rework(
    rework_id: uuid.UUID,
    body: ReworkAssignIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.assign_rework(db, rework_id, body.staff_member_id, u.user_id, request_id=_rid(r))
    return ok({"id": str(rw.id), "status": rw.status}, _rid(r), "admin.rework.assigned")


# ── Admin Refund Requests ─────────────────────────────────────────────────────
@admin_refund_router.get("")
async def list_refund_requests(
    tenant_id:   Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    status:      Optional[str]       = None,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    refunds = await _refund.list_refund_requests(db, tenant_id=tenant_id, customer_id=customer_id, status=status)
    return ok([{"id": str(rf.id), "status": rf.status, "complaint_id": str(rf.complaint_id),
                "refund_type": rf.refund_type,
                "requested_amount": str(rf.requested_amount) if rf.requested_amount else None,
                "approved_amount": str(rf.approved_amount) if rf.approved_amount else None,
                "created_at": str(rf.created_at)} for rf in refunds], _rid(r), "admin.refund.list")


@admin_refund_router.post("/{refund_id}/approve")
async def approve_refund(
    refund_id: uuid.UUID,
    body: RefundApproveIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rf = await _refund.admin_approve_refund(
        db, refund_id, u.user_id, approved_amount=body.approved_amount, request_id=_rid(r)
    )
    return ok({"id": str(rf.id), "status": rf.status, "approved_amount": str(rf.approved_amount) if rf.approved_amount else None},
              _rid(r), "admin.refund.approved")


@admin_refund_router.post("/{refund_id}/reject")
async def reject_refund(
    refund_id: uuid.UUID,
    body: RefundRejectIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rf = await _refund.admin_reject_refund(db, refund_id, u.user_id, body.reason, request_id=_rid(r))
    return ok({"id": str(rf.id), "status": rf.status}, _rid(r), "admin.refund.rejected")


@admin_refund_router.post("/{refund_id}/record")
async def record_refund(
    refund_id: uuid.UUID,
    body: RefundRecordIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.complaints.constants import ACTOR_ADMIN
    rf = await _refund.record_refund(
        db, refund_id, u.user_id, ACTOR_ADMIN,
        body.recorded_amount, proof_media_url=body.proof_media_url, request_id=_rid(r)
    )
    return ok({"id": str(rf.id), "status": rf.status, "recorded_amount": str(rf.recorded_amount)},
              _rid(r), "admin.refund.recorded")


@admin_refund_router.post("/{refund_id}/verify")
async def verify_refund(
    refund_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rf = await _refund.verify_refund(db, refund_id, u.user_id, request_id=_rid(r))
    return ok({"id": str(rf.id), "status": rf.status, "verified_at": str(rf.verified_at)},
              _rid(r), "admin.refund.verified")


# ── Admin Complaint Policies ──────────────────────────────────────────────────
@admin_cpolicy_router.get("")
async def list_policies(
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    policies = await _complaint.list_policies(db)
    return ok([p.to_dict() for p in policies], _rid(r), "admin.cpolicies.list")


@admin_cpolicy_router.post("")
async def create_policy(
    body: PolicyIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    p = await _complaint.create_policy(db, body.model_dump(exclude_none=True))
    return ok(p.to_dict(), _rid(r), "admin.cpolicy.created")


@admin_cpolicy_router.put("/{policy_id}")
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyIn,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    p = await _complaint.update_policy(db, policy_id, body.model_dump(exclude_none=True))
    return ok(p.to_dict(), _rid(r), "admin.cpolicy.updated")


# ── Settlement actions (Sprint 75) ────────────────────────────────────────────
@admin_complaint_router.post("/{complaint_id}/start-ai-settlement")
async def start_ai_settlement(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    session = await _complaint.admin_start_ai_settlement(
        db, u.user_id, complaint_id, request_id=_rid(r)
    )
    return ok(session.to_dict(), _rid(r), "admin.complaint.ai_settlement.started")


@admin_complaint_router.post("/{complaint_id}/finalize-settlement")
async def finalize_settlement(
    complaint_id: uuid.UUID,
    body: FinalizeSettlementIn,
    r: Request       = None,
    u = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.admin_finalize_settlement(
        db, u.user_id, complaint_id, body.decision, notes=body.notes, request_id=_rid(r)
    )
    return ok({"id": str(c.id), "status": c.status, "settlement_status": c.settlement_status},
              _rid(r), "admin.complaint.settlement.finalized")


@admin_complaint_router.post("/{complaint_id}/settlement-proposals")
async def create_admin_settlement_proposal(
    complaint_id: uuid.UUID,
    body: CreateSettlementProposalIn,
    r: Request       = None,
    u = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.complaints.constants import ACTOR_ADMIN
    proposal = await _complaint.create_settlement_proposal(
        db, complaint_id,
        proposed_by=ACTOR_ADMIN,
        proposed_by_user_id=u.user_id,
        proposal_type=body.proposal_type,
        description=body.description,
        proposal_amount=body.proposal_amount,
        conditions=body.conditions,
        request_id=_rid(r),
    )
    return ok(proposal.to_dict(), _rid(r), "admin.complaint.settlement.proposal.created")


@admin_complaint_router.get("/{complaint_id}/settlement-proposals")
async def list_settlement_proposals(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    proposals = await _complaint.list_settlement_proposals(db, complaint_id)
    return ok([p.to_dict() for p in proposals], _rid(r), "admin.complaint.settlement.proposals.list")


@admin_complaint_router.get("/{complaint_id}/ai-session")
async def get_ai_session(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    session = await _complaint.get_ai_session(db, complaint_id)
    return ok(session.to_dict() if session else None, _rid(r), "admin.complaint.ai_session.get")


@admin_complaint_router.get("/{complaint_id}/timeline")
async def get_complaint_timeline(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unified timeline: messages + events + proposals in chronological order."""
    events   = await _complaint.list_events(db, complaint_id)
    messages = await _complaint.list_messages(db, complaint_id, viewer="admin")
    proposals = await _complaint.list_settlement_proposals(db, complaint_id)

    timeline = []
    for e in events:
        timeline.append({"type": "event", "at": str(e.created_at), "data": e.to_dict()})
    for m in messages:
        timeline.append({"type": "message", "at": str(m.created_at), "data": m.to_dict()})
    for p in proposals:
        timeline.append({"type": "proposal", "at": str(p.created_at), "data": p.to_dict()})

    timeline.sort(key=lambda x: x["at"])
    return ok(timeline, _rid(r), "admin.complaint.timeline.list")
