"""Sprint 25 — Provider Complaint API."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import uuid
from decimal import Decimal

from app.dependencies.auth import get_current_user, UserContext
from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.rework_service import ServiceReworkService
from app.engines.complaints.refund_service import RefundRequestService

provider_complaint_router = APIRouter(prefix="/v1/provider/complaints", tags=["provider-complaints"])
provider_rework_router    = APIRouter(prefix="/v1/provider/rework-requests", tags=["provider-rework"])
provider_refund_router    = APIRouter(prefix="/v1/provider/refund-requests", tags=["provider-refunds"])

_complaint = ComplaintService()
_rework    = ServiceReworkService()
_refund    = RefundRequestService()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _rid(r):
    return getattr(r.state, "request_id", "—") if r else "—"


class AddMessageIn(BaseModel):
    message_text:          str
    visibility:            Optional[str] = "public_to_case"


class OfferResolutionIn(BaseModel):
    resolution_type:       str
    description:           str
    customer_visible_notes: Optional[str] = None


class CreateReworkIn(BaseModel):
    rework_reason:          str
    customer_visible_notes: Optional[str] = None


class ScheduleReworkIn(BaseModel):
    scheduled_date:        Optional[str] = None
    scheduled_time_window: Optional[str] = None


class AssignReworkIn(BaseModel):
    staff_member_id: uuid.UUID


class ReworkNotesIn(BaseModel):
    notes: Optional[str] = None


class RefundReviewIn(BaseModel):
    notes: Optional[str] = None


# ── Complaints ────────────────────────────────────────────────────────────────
@provider_complaint_router.get("")
async def list_complaints(
    status: Optional[str] = None,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    complaints = await _complaint.provider_list_complaints(db, u.tenant_id, status=status)
    return ok([c.to_provider_dict() for c in complaints], _rid(r), "provider.complaints.list")


@provider_complaint_router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _complaint.provider_get_complaint(db, u.tenant_id, complaint_id)
    return ok(c.to_provider_dict(), _rid(r), "provider.complaints.get")


@provider_complaint_router.post("/{complaint_id}/respond")
async def respond_to_complaint(
    complaint_id: uuid.UUID,
    body: AddMessageIn,
    r: Request       = None,
    # Slice 2F-9: previously get_current_user only -- any authenticated
    # user of any role/tenant could respond to any tenant's complaint.
    # No existing COMPLAINT_* permission exists in the registry; using
    # the narrowest existing composed dependency (tenant_owner role,
    # access-scope-aware) rather than inventing a new permission.
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    msg = await _complaint.provider_add_response(
        db, u.tenant_id, complaint_id, u.user_id, body.message_text, request_id=_rid(r)
    )
    return ok({"id": str(msg.id), "message_text": msg.message_text}, _rid(r), "provider.complaint.responded")


@provider_complaint_router.get("/{complaint_id}/messages")
async def list_messages(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _complaint.provider_get_complaint(db, u.tenant_id, complaint_id)
    msgs = await _complaint.list_messages(db, complaint_id, viewer="provider")
    return ok([{"id": str(m.id), "sender_type": m.sender_type,
                "message_text": m.message_text, "created_at": str(m.created_at)} for m in msgs],
              _rid(r), "provider.complaint.messages")


@provider_complaint_router.post("/{complaint_id}/offer-resolution")
async def offer_resolution(
    complaint_id: uuid.UUID,
    body: OfferResolutionIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    res = await _complaint.provider_offer_resolution(
        db, u.tenant_id, complaint_id, u.user_id,
        body.resolution_type, body.description,
        customer_visible_notes=body.customer_visible_notes,
        request_id=_rid(r),
    )
    return ok({"id": str(res.id), "status": res.status, "resolution_type": res.resolution_type},
              _rid(r), "provider.resolution.offered")


@provider_complaint_router.get("/{complaint_id}/resolutions")
async def list_resolutions(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _complaint.provider_get_complaint(db, u.tenant_id, complaint_id)
    resolutions = await _complaint.list_resolutions(db, complaint_id)
    return ok([{"id": str(res.id), "status": res.status, "resolution_type": res.resolution_type,
                "description": res.description, "customer_visible_notes": res.customer_visible_notes,
                "created_at": str(res.created_at)} for res in resolutions], _rid(r), "provider.resolutions.list")


# ── Rework requests ───────────────────────────────────────────────────────────
@provider_rework_router.get("")
async def list_rework_requests(
    status: Optional[str] = None,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reworks = await _rework.list_rework_requests(db, tenant_id=u.tenant_id, status=status)
    return ok([{"id": str(rw.id), "status": rw.status, "complaint_id": str(rw.complaint_id),
                "rework_reason": rw.rework_reason, "scheduled_date": str(rw.scheduled_date) if rw.scheduled_date else None,
                "created_at": str(rw.created_at)} for rw in reworks], _rid(r), "provider.rework.list")


@provider_rework_router.get("/{rework_id}")
async def get_rework(
    rework_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.get_rework(db, rework_id)
    return ok({"id": str(rw.id), "status": rw.status, "rework_reason": rw.rework_reason,
               "complaint_id": str(rw.complaint_id), "customer_visible_notes": rw.customer_visible_notes,
               "scheduled_date": str(rw.scheduled_date) if rw.scheduled_date else None,
               "completed_at": str(rw.completed_at) if rw.completed_at else None},
              _rid(r), "provider.rework.get")


@provider_rework_router.post("/{rework_id}/schedule")
async def schedule_rework(
    rework_id: uuid.UUID,
    body: ScheduleReworkIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.schedule_rework(db, rework_id, u.user_id,
                                       scheduled_date=body.scheduled_date,
                                       scheduled_time_window=body.scheduled_time_window,
                                       request_id=_rid(r), tenant_id=u.tenant_id)
    return ok({"id": str(rw.id), "status": rw.status}, _rid(r), "provider.rework.scheduled")


@provider_rework_router.post("/{rework_id}/start")
async def start_rework(
    rework_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.mark_rework_in_progress(db, rework_id, u.user_id, tenant_id=u.tenant_id)
    return ok({"id": str(rw.id), "status": rw.status}, _rid(r), "provider.rework.started")


@provider_rework_router.post("/{rework_id}/complete")
async def complete_rework(
    rework_id: uuid.UUID,
    body: ReworkNotesIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    rw = await _rework.mark_rework_completed(db, rework_id, u.user_id, notes=body.notes, request_id=_rid(r), tenant_id=u.tenant_id)
    return ok({"id": str(rw.id), "status": rw.status}, _rid(r), "provider.rework.completed")


# ── Refund requests ───────────────────────────────────────────────────────────
@provider_refund_router.get("")
async def list_refund_requests(
    status: Optional[str] = None,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    refunds = await _refund.list_refund_requests(db, tenant_id=u.tenant_id, status=status)
    return ok([{"id": str(rf.id), "status": rf.status, "complaint_id": str(rf.complaint_id),
                "refund_type": rf.refund_type, "requested_amount": str(rf.requested_amount) if rf.requested_amount else None,
                "created_at": str(rf.created_at)} for rf in refunds], _rid(r), "provider.refund.list")


@provider_refund_router.post("/{refund_id}/review")
async def review_refund(
    refund_id: uuid.UUID,
    body: RefundReviewIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    rf = await _refund.provider_review_refund(db, refund_id, u.user_id, notes=body.notes, request_id=_rid(r), tenant_id=u.tenant_id)
    return ok({"id": str(rf.id), "status": rf.status}, _rid(r), "provider.refund.reviewed")


# ── Settlement proposals (Sprint 75) ──────────────────────────────────────────
class CreateSettlementIn(BaseModel):
    proposal_type:   str
    description:     str
    proposal_amount: Optional[Decimal] = None
    conditions:      Optional[str]     = None


class SettlementRespondIn(BaseModel):
    response: str


class AIAnswersIn(BaseModel):
    answers: list[str]


@provider_complaint_router.get("/{complaint_id}/ai-session")
async def get_ai_session(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The provider must be able to SEE the questions the AI asked them."""
    await _complaint.provider_get_complaint(db, u.tenant_id, complaint_id)
    session = await _complaint.get_ai_session(db, complaint_id)
    if not session:
        return ok(None, _rid(r), "provider.complaint.ai_session.get")
    # provider-safe view — never expose the customer's answers to the other side
    return ok({
        "id":               str(session.id),
        "status":           session.status,
        "tenant_questions": session.tenant_questions,
        "tenant_answers":   session.tenant_answers,
        "awaiting_your_answers": session.tenant_answers is None,
    }, _rid(r), "provider.complaint.ai_session.get")


@provider_complaint_router.post("/{complaint_id}/ai-session/answers")
async def submit_ai_answers(
    complaint_id: uuid.UUID,
    body: AIAnswersIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    """MODULE-L5-02 bug #37: the AI settlement session asked the provider
    clarifying questions but there was NO endpoint to answer them. Once both
    sides have answered, the (previously orphaned) analysis runs and produces the
    settlement proposal."""
    complaint = await _complaint.provider_get_complaint(db, u.tenant_id, complaint_id)
    from app.engines.complaints.ai_settlement_service import AISettlementService
    session = await AISettlementService().submit_answers(
        db, complaint, "tenant", body.answers, request_id=_rid(r),
    )
    await db.commit()
    return ok({"id": str(session.id), "status": session.status},
              _rid(r), "provider.complaint.ai_answers.submitted")


@provider_complaint_router.get("/{complaint_id}/settlement-proposals")
async def list_settlement_proposals(
    complaint_id: uuid.UUID,
    r: Request       = None,
    u: UserContext   = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _complaint.provider_get_complaint(db, u.tenant_id, complaint_id)
    proposals = await _complaint.list_settlement_proposals(db, complaint_id)
    return ok([p.to_dict() for p in proposals], _rid(r), "provider.settlement.proposals.list")


@provider_complaint_router.post("/{complaint_id}/settlement-proposals")
async def create_settlement_proposal(
    complaint_id: uuid.UUID,
    body: CreateSettlementIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.complaints.constants import ACTOR_PROVIDER
    proposal = await _complaint.create_settlement_proposal(
        db, complaint_id,
        proposed_by=ACTOR_PROVIDER,
        proposed_by_user_id=u.user_id,
        proposal_type=body.proposal_type,
        description=body.description,
        proposal_amount=body.proposal_amount,
        conditions=body.conditions,
        request_id=_rid(r),
        tenant_id=u.tenant_id,
    )
    return ok(proposal.to_dict(), _rid(r), "provider.settlement.proposal.created")


@provider_complaint_router.post("/{complaint_id}/settlement-proposals/{proposal_id}/respond")
async def respond_to_settlement(
    complaint_id: uuid.UUID,
    proposal_id:  uuid.UUID,
    body: SettlementRespondIn,
    r: Request       = None,
    u: UserContext   = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    proposal = await _complaint.tenant_respond_to_settlement(
        db, u.tenant_id, complaint_id, proposal_id,
        body.response, actor_user_id=u.user_id, request_id=_rid(r),
    )
    return ok(proposal.to_dict(), _rid(r), "provider.settlement.responded")
