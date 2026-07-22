"""Sprint 21 — Real Estate lead execution routers (agent + provider + customer + admin)."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.dependencies.auth import get_current_user, require_super_admin, require_customer, UserContext
from app.core.permissions import require_owner_or_office_staff_mutation
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.execution.real_estate_service import RealEstateLeadExecutionService

_svc = RealEstateLeadExecutionService()


async def require_owner_or_office_staff_read(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """Slice 2F-11A: read-only counterpart to
    `require_owner_or_office_staff_mutation` -- same role set
    (super_admin/tenant_owner/staff, technician excluded), but without the
    read-only-access-scope deny (a read-only tenant persona must still be
    able to read). No mutation guard was reused here because applying a
    *_mutation dependency to a GET route would incorrectly block
    legitimate read-only staff from viewing their own tenant's leads.
    Technician is excluded per Slice 2F-11A's direct finding: no
    technician/mobile caller exists anywhere for this module, and
    `require_staff_or_above`'s technician admission on the 3 provider/agent
    read routes was implementation evidence only, not product-policy
    evidence (the same standard already applied to the 11 mutations in
    Slice 2F-11)."""
    from app.exceptions import ServiceOSException
    if user.role not in ("super_admin", "tenant_owner", "staff"):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Owner or office staff access required. Your role: '{user.role}'.",
            blocking_rule="required_role: tenant_owner | staff | super_admin",
        )
    return user

# ── Agent / Staff router ──────────────────────────────────────────────────────
agent_router = APIRouter(prefix="/v1/staff/real-estate-leads", tags=["Sprint21-Agent-RealEstate"])


class ReasonBody(BaseModel):
    reason: str


class NoteBody(BaseModel):
    note_text: str
    is_customer_visible: bool = False


class OptionalNoteBody(BaseModel):
    notes: Optional[str] = None


@agent_router.post("/{lead_id}/accept")
async def agent_accept(lead_id: uuid.UUID, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.accept_lead(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-accept")


@agent_router.post("/{lead_id}/reject")
async def agent_reject(lead_id: uuid.UUID, body: ReasonBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.reject_lead(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), reason=body.reason, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-reject")


@agent_router.post("/{lead_id}/mark-contacted")
async def agent_mark_contacted(lead_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_contacted(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-contacted")


@agent_router.post("/{lead_id}/schedule-follow-up")
async def agent_follow_up(lead_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.schedule_follow_up(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-follow-up")


@agent_router.post("/{lead_id}/plan-site-visit")
async def agent_plan_site_visit(lead_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.plan_site_visit(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-site-plan")


@agent_router.post("/{lead_id}/complete-site-visit")
async def agent_complete_site_visit(lead_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.complete_site_visit(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-site-done")


@agent_router.post("/{lead_id}/qualify")
async def agent_qualify(lead_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.qualify_lead(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-qualify")


@agent_router.post("/{lead_id}/disqualify")
async def agent_disqualify(lead_id: uuid.UUID, body: ReasonBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.disqualify_lead(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), reason=body.reason, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-disqualify")


@agent_router.post("/{lead_id}/convert")
async def agent_convert(lead_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.convert_lead(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-convert")


@agent_router.post("/{lead_id}/close-lost")
async def agent_close_lost(lead_id: uuid.UUID, body: ReasonBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.close_lost(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), reason=body.reason, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-close-lost")


@agent_router.post("/{lead_id}/notes")
async def agent_add_note(lead_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(require_owner_or_office_staff_mutation), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.add_note(db, lead_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), note_text=body.note_text, is_customer_visible=body.is_customer_visible, request_id=rid)
    await db.commit()
    return ok(result, rid, "agent-re-note")


@agent_router.get("/{lead_id}/timeline")
async def agent_timeline(lead_id: uuid.UUID, r: Request, user=Depends(require_owner_or_office_staff_read), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_timeline(db, lead_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "agent-re-timeline")


# ── Provider router ───────────────────────────────────────────────────────────
provider_router = APIRouter(prefix="/v1/provider/real-estate-leads", tags=["Sprint21-Provider-RealEstate"])


@provider_router.get("/{lead_id}/timeline")
async def provider_timeline(lead_id: uuid.UUID, r: Request, user=Depends(require_owner_or_office_staff_read), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_timeline(db, lead_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "provider-re-timeline")


@provider_router.get("/{lead_id}/notes")
async def provider_notes(lead_id: uuid.UUID, r: Request, user=Depends(require_owner_or_office_staff_read), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_notes(db, lead_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "provider-re-notes")


# ── Customer tracking router ──────────────────────────────────────────────────
customer_router = APIRouter(prefix="/v1/customer/real-estate-leads", tags=["Sprint21-Customer-RealEstate"])


@customer_router.get("/{lead_id}/tracking")
async def customer_tracking(lead_id: uuid.UUID, r: Request, user=Depends(require_customer), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.final_records.models import RealEstateLead
    res = await db.execute(select(RealEstateLead).where(
        RealEstateLead.id == lead_id,
        RealEstateLead.customer_id == uuid.UUID(str(user.user_id))
    ))
    lead = res.scalars().first()
    if not lead:
        from app.engines.execution.constants import ERR_RECORD_NOT_FOUND
        raise ValueError(ERR_RECORD_NOT_FOUND)
    notes = await _svc.get_notes(db, lead_id, lead.tenant_id, customer_only=True)
    return ok({"lead": lead.to_dict(), "notes": notes}, rid, "customer-re-tracking")


# ── Admin router ──────────────────────────────────────────────────────────────
admin_router = APIRouter(prefix="/v1/admin/real-estate-leads", tags=["Sprint21-Admin-RealEstate"])


@admin_router.get("/{lead_id}/execution-timeline")
async def admin_timeline(lead_id: uuid.UUID, r: Request, user=Depends(require_super_admin), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_timeline(db, lead_id)
    return ok(result, rid, "admin-re-timeline")


@admin_router.get("/{lead_id}/notes")
async def admin_notes(lead_id: uuid.UUID, r: Request, user=Depends(require_super_admin), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_notes(db, lead_id)
    return ok(result, rid, "admin-re-notes")
