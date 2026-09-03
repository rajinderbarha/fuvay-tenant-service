"""Sprint 25 — Customer Complaint API."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
import uuid
from decimal import Decimal

from app.dependencies.auth import require_customer, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.complaints.eligibility_service import ComplaintEligibilityService
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.rework_service import ServiceReworkService
from app.engines.complaints.refund_service import RefundRequestService
from app.exceptions import ServiceOSException

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


class CreateJobRefundIn(BaseModel):
    job_id:           uuid.UUID
    reason:           str
    requested_amount: Decimal

# ── Eligibility check ─────────────────────────────────────────────────────────
@customer_complaint_router.get("/check-eligible")
async def check_eligible(
    record_type:    str,
    record_id:      uuid.UUID,
    complaint_type: Optional[str] = None,
    category_id:    Optional[uuid.UUID] = None,
    r: Request     = None,
    u: UserContext = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    msg = await _complaint.add_customer_message(
        db, u.user_id, complaint_id, body.message_text, request_id=rid
    )
    return ok({"id": str(msg.id), "message_text": msg.message_text}, rid, "complaint.message.added")


# ── List messages ─────────────────────────────────────────────────────────────
class AddComplaintMediaIn(BaseModel):
    """Evidence already stored by the media engine, referenced by URL.

    The bytes go through POST /v1/media/upload with
    media_context="complaint_evidence" (its CONTEXT_RULES entry already exists:
    documents/images, 10 MB) which validates type, size and signature; this
    endpoint records the resulting URL against the case.
    """
    model_config = ConfigDict(extra="forbid")
    file_url: str = Field(..., min_length=1, max_length=500)
    media_type: str = Field("photo", max_length=20)
    file_name: str | None = Field(None, max_length=300)
    caption: str | None = Field(None, max_length=1000)


@customer_complaint_router.post("/{complaint_id}/media", status_code=201)
async def add_complaint_media(
    complaint_id: uuid.UUID,
    body: AddComplaintMediaIn,
    r: Request = None,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Attach a photo or document to your own complaint.

    Real gap closed: `ComplaintService.upload_complaint_media` existed and the
    `complaint_media` table existed, but NO router anywhere called it -- so a
    customer could never attach evidence to a complaint, the table could only
    ever be empty in production, and the provider's Evidence tab had nothing
    to show no matter what the customer wanted to prove.
    """
    from app.engines.complaints.constants import ACTOR_CUSTOMER
    rid = getattr(r.state, "request_id", "-") if r else "-"
    media = await _complaint.upload_complaint_media(
        db, uuid.UUID(str(u.user_id)), ACTOR_CUSTOMER, complaint_id,
        file_url=body.file_url, media_type=body.media_type,
        file_name=body.file_name, caption=body.caption, request_id=rid,
    )
    return ok(media.to_dict(), rid, "complaint.media.added")


@customer_complaint_router.get("/{complaint_id}/media")
async def list_complaint_media(
    complaint_id: uuid.UUID,
    r: Request = None,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """The customer's own view of what is attached to their case."""
    rid = getattr(r.state, "request_id", "-") if r else "-"
    await _complaint.get_customer_complaint(db, uuid.UUID(str(u.user_id)), complaint_id)
    items = await _complaint.list_media(db, complaint_id, viewer="customer")
    return ok({"items": [m.to_dict() for m in items]}, rid, "complaint.media.list")


@customer_complaint_router.get("/{complaint_id}/messages")
async def list_messages(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    await _complaint.get_customer_complaint(db, u.user_id, complaint_id)
    msgs = await _complaint.list_messages(db, complaint_id, viewer="customer")
    return ok([{"id": str(m.id), "sender_type": m.sender_type, "message_text": m.message_text,
                "created_at": str(m.created_at)} for m in msgs], rid, "complaint.messages.list")


# ── List resolutions ──────────────────────────────────────────────────────────
@customer_complaint_router.get("/{complaint_id}/resolutions")
async def list_resolutions(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """MODULE-L5-02 bug #35: the customer could accept or reject a resolution
    (POST .../resolutions/{resolution_id}/accept|reject) but had NO endpoint to
    list them — so they could never see what had been offered, and had no way to
    obtain the resolution_id those endpoints require. The provider has had this
    endpoint all along; the customer's accept/reject was effectively unusable."""
    rid = getattr(r.state, "request_id", "—") if r else "—"
    await _complaint.get_customer_complaint(db, u.user_id, complaint_id)
    resolutions = await _complaint.list_resolutions(db, complaint_id)
    return ok([{"id": str(res.id), "status": res.status,
                "resolution_type": res.resolution_type,
                "description": res.description,
                "customer_visible_notes": res.customer_visible_notes,
                "created_at": str(res.created_at)} for res in resolutions],
              rid, "complaint.resolutions.list")


# ── AI settlement: answer the clarifying questions ────────────────────────────
@customer_complaint_router.post("/{complaint_id}/cancel")
async def cancel_complaint(
    complaint_id: uuid.UUID,
    body: CancelComplaintIn,
    r: Request       = None,
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
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

@customer_complaint_router.get("/records/refunds")
async def list_customer_refunds(
    status: Optional[str] = None, r: Request = None,
    u: UserContext = Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "-") if r else "-"
    refunds = await _refund.list_refund_requests(db, customer_id=u.user_id, status=status)
    return ok([refund.to_customer_dict() for refund in refunds], rid, "refund.customer.list")


@customer_complaint_router.post("/records/refunds/from-job")
async def create_job_refund(
    body: CreateJobRefundIn, r: Request = None,
    u: UserContext = Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "-") if r else "-"
    refund = await _refund.create_job_refund_request(
        db,
        customer_id=u.user_id,
        job_id=body.job_id,
        reason=body.reason,
        requested_amount=body.requested_amount,
        request_id=rid,
    )
    return ok(refund.to_customer_dict(), rid, "refund.requested")

@customer_complaint_router.get("/records/refunds/{refund_id}")
async def get_customer_refund(
    refund_id: uuid.UUID, r: Request = None,
    u: UserContext = Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "-") if r else "-"
    refund = await _refund.get_refund(db, refund_id)
    if str(refund.customer_id) != str(u.user_id):
        raise ServiceOSException("REFUND_NOT_FOUND", "Refund request not found.", status_code=404)
    return ok(refund.to_customer_dict(), rid, "refund.customer.get")


# ── Settlement proposals (Sprint 75) ──────────────────────────────────────────
class SettlementRespondIn(BaseModel):
    response:            str
    counter_description: Optional[str] = None


@customer_complaint_router.get("/{complaint_id}/settlement-proposals")
async def list_settlement_proposals(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_customer),
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
    u: UserContext   = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—") if r else "—"
    proposal = await _complaint.customer_respond_to_settlement(
        db, u.user_id, complaint_id, proposal_id,
        body.response, counter_description=body.counter_description, request_id=rid,
    )
    return ok(proposal.to_dict(), rid, "customer.settlement.responded")
