"""Sprint 25 — Customer Complaint API."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import uuid
from decimal import Decimal

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.complaints.eligibility_service import ComplaintEligibilityService
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.rework_service import ServiceReworkService
from app.engines.complaints.refund_service import RefundRequestService

customer_complaint_router = APIRouter(prefix="/v1/customer/complaints", tags=["customer-complaints"])

_eligibility = ComplaintEligibilityService()
_complaint   = ComplaintService()
_rework      = ServiceReworkService()
_refund      = RefundRequestService()


class CreateComplaintIn(BaseModel):
    record_type:          str
    record_id:            uuid.UUID
    complaint_type:       str
    description:          str
    category_id:          Optional[uuid.UUID] = None
    offering_id:          Optional[uuid.UUID] = None
    requested_resolution: Optional[str]        = None
    title:                Optional[str]        = None


class AddMessageIn(BaseModel):
    message_text: str


class CancelComplaintIn(BaseModel):
    reason: str


class ResolutionActionIn(BaseModel):
    reason: Optional[str] = None


class CreateRefundIn(BaseModel):
    refund_type:      str
    reason:           str
    requested_amount: Optional[Decimal] = None
    refund_method:    Optional[str]     = None


class CreateReworkIn(BaseModel):
    rework_reason:          str
    customer_visible_notes: Optional[str] = None


# ── Eligibility check ─────────────────────────────────────────────────────────
@customer_complaint_router.get("/check-eligible")
async def check_eligible(
    record_type:    str,
    record_id:      uuid.UUID,
    complaint_type: Optional[str] = None,
    category_id:    Optional[uuid.UUID] = None,
    r: Request     = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    result = await _eligibility.check_eligible(
        db, u.user_id, record_type, record_id,
        complaint_type=complaint_type, category_id=category_id,
    )
    return ok(result, rid, "complaint.eligible_check")


# ── Create complaint ──────────────────────────────────────────────────────────
@customer_complaint_router.post("")
async def create_complaint(
    body: CreateComplaintIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    c = await _complaint.create_complaint(
        db, u.user_id,
        category_id          = body.category_id or uuid.UUID(int=0),
        record_type          = body.record_type,
        record_id            = body.record_id,
        complaint_type       = body.complaint_type,
        description          = body.description,
        offering_id          = body.offering_id,
        requested_resolution = body.requested_resolution,
        title                = body.title,
        request_id           = rid,
    )
    return ok(c.to_customer_dict(), rid, "complaint.created")


# ── List complaints ───────────────────────────────────────────────────────────
@customer_complaint_router.get("")
async def list_complaints(
    status: Optional[str] = None,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    complaints = await _complaint.list_customer_complaints(db, u.user_id, status=status)
    return ok([c.to_customer_dict() for c in complaints], rid, "complaint.list")


# ── Get complaint ─────────────────────────────────────────────────────────────
@customer_complaint_router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    c = await _complaint.get_customer_complaint(db, u.user_id, complaint_id)
    return ok(c.to_customer_dict(), rid, "complaint.get")


# ── Add message ───────────────────────────────────────────────────────────────
@customer_complaint_router.post("/{complaint_id}/messages")
async def add_message(
    complaint_id: uuid.UUID,
    body: AddMessageIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    msg = await _complaint.add_customer_message(
        db, u.user_id, complaint_id, body.message_text, request_id=rid
    )
    return ok({"id": str(msg.id), "message_text": msg.message_text}, rid, "complaint.message.added")


# ── List messages ─────────────────────────────────────────────────────────────
@customer_complaint_router.get("/{complaint_id}/messages")
async def list_messages(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    await _complaint.get_customer_complaint(db, u.user_id, complaint_id)
    msgs = await _complaint.list_messages(db, complaint_id, viewer="customer")
    return ok([{"id": str(m.id), "sender_type": m.sender_type, "message_text": m.message_text,
                "created_at": str(m.created_at)} for m in msgs], rid, "complaint.messages.list")


# ── Cancel complaint ──────────────────────────────────────────────────────────
@customer_complaint_router.post("/{complaint_id}/cancel")
async def cancel_complaint(
    complaint_id: uuid.UUID,
    body: CancelComplaintIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    c = await _complaint.cancel_customer_complaint(db, u.user_id, complaint_id, body.reason, request_id=rid)
    return ok({"id": str(c.id), "status": c.status}, rid, "complaint.cancelled")


# ── Accept resolution ─────────────────────────────────────────────────────────
@customer_complaint_router.post("/{complaint_id}/resolutions/{resolution_id}/accept")
async def accept_resolution(
    complaint_id:  uuid.UUID,
    resolution_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    res = await _complaint.customer_accept_resolution(db, u.user_id, complaint_id, resolution_id, request_id=rid)
    return ok({"id": str(res.id), "status": res.status}, rid, "resolution.accepted")


# ── Reject resolution ─────────────────────────────────────────────────────────
@customer_complaint_router.post("/{complaint_id}/resolutions/{resolution_id}/reject")
async def reject_resolution(
    complaint_id:  uuid.UUID,
    resolution_id: uuid.UUID,
    body: ResolutionActionIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    res = await _complaint.customer_reject_resolution(
        db, u.user_id, complaint_id, resolution_id, body.reason or "", request_id=rid
    )
    return ok({"id": str(res.id), "status": res.status}, rid, "resolution.rejected")


# ── Request refund ────────────────────────────────────────────────────────────
@customer_complaint_router.post("/{complaint_id}/refund")
async def request_refund(
    complaint_id: uuid.UUID,
    body: CreateRefundIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    from app.engines.complaints.constants import ACTOR_CUSTOMER
    refund = await _refund.create_refund_request_from_complaint(
        db, complaint_id, u.user_id, ACTOR_CUSTOMER,
        body.refund_type, body.reason,
        requested_amount=body.requested_amount,
        refund_method=body.refund_method,
        request_id=rid,
    )
    return ok(refund.to_customer_dict(), rid, "refund.requested")


# ── Settlement proposals (Sprint 75) ──────────────────────────────────────────
class SettlementRespondIn(BaseModel):
    response:            str
    counter_description: Optional[str] = None


@customer_complaint_router.get("/{complaint_id}/settlement-proposals")
async def list_settlement_proposals(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    await _complaint.get_customer_complaint(db, u.user_id, complaint_id)
    proposals = await _complaint.list_settlement_proposals(db, complaint_id)
    return ok([p.to_dict() for p in proposals], rid, "customer.settlement.proposals.list")


@customer_complaint_router.post("/{complaint_id}/settlement-proposals/{proposal_id}/respond")
async def respond_to_settlement(
    complaint_id: uuid.UUID,
    proposal_id:  uuid.UUID,
    body: SettlementRespondIn,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    proposal = await _complaint.customer_respond_to_settlement(
        db, u.user_id, complaint_id, proposal_id,
        body.response, counter_description=body.counter_description, request_id=rid,
    )
    return ok(proposal.to_dict(), rid, "customer.settlement.responded")
