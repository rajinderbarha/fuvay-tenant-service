"""Sprint 18 — Admin Real Estate Lead Draft + Routing Rules API (10 endpoints)."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Request, Query

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok

router = APIRouter(
    prefix="/v1/admin/real-estate",
    tags=["Admin Real Estate Lead Drafts"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


# ── GET /lead-drafts ──────────────────────────────────────────────────────────

@router.get(
    "/lead-drafts",
    summary="List all real estate lead drafts (admin)",
    response_model=ApiResponse,
)
async def admin_list_drafts(
    r:      Request,
    status: str | None = Query(None, description="Filter by draft status"),
    city:   str | None = Query(None, description="Filter by city"),
    intent: str | None = Query(None, description="Filter by lead_intent"),
    limit:  int        = Query(50, ge=1, le=200),
    offset: int        = Query(0, ge=0),
):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_list_drafts(status=status, city=city, intent=intent,
                                              limit=limit, offset=offset)
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        raise


# ── GET /lead-drafts/{draft_id} ───────────────────────────────────────────────

@router.get(
    "/lead-drafts/{draft_id}",
    summary="Get a specific real estate lead draft (admin)",
    response_model=ApiResponse,
)
async def admin_get_draft(draft_id: uuid.UUID, r: Request):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_get_draft(draft_id)
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        raise


# ── GET /lead-drafts/{draft_id}/events ────────────────────────────────────────

@router.get(
    "/lead-drafts/{draft_id}/events",
    summary="Get event log for a real estate lead draft (admin)",
    response_model=ApiResponse,
)
async def admin_get_draft_events(draft_id: uuid.UUID, r: Request):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_get_draft_events(draft_id)
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        raise


# ── GET /lead-routing-rules ────────────────────────────────────────────────────

@router.get(
    "/lead-routing-rules",
    summary="List lead routing rules (admin)",
    response_model=ApiResponse,
)
async def admin_list_routing_rules(
    r:           Request,
    category_id: uuid.UUID | None = Query(None, description="Filter by category"),
    active_only: bool              = Query(True),
):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_list_routing_rules(category_id=category_id, active_only=active_only)
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        raise


# ── POST /lead-routing-rules ──────────────────────────────────────────────────

@router.post(
    "/lead-routing-rules",
    summary="Create a lead routing rule (admin)",
    response_model=ApiResponse,
)
async def admin_create_routing_rule(r: Request):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        body = await r.json()
        # Convert category_id string to UUID
        if "category_id" in body and isinstance(body["category_id"], str):
            body["category_id"] = uuid.UUID(body["category_id"])
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_create_routing_rule(body)
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── PUT /lead-routing-rules/{rule_id} ────────────────────────────────────────

@router.put(
    "/lead-routing-rules/{rule_id}",
    summary="Update a lead routing rule (admin)",
    response_model=ApiResponse,
)
async def admin_update_routing_rule(rule_id: uuid.UUID, r: Request):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        body = await r.json()
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_update_routing_rule(rule_id, body)
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /lead-routing-rules/{rule_id}/activate ──────────────────────────────

@router.post(
    "/lead-routing-rules/{rule_id}/activate",
    summary="Activate a lead routing rule (admin)",
    response_model=ApiResponse,
)
async def admin_activate_rule(rule_id: uuid.UUID, r: Request):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_toggle_routing_rule(rule_id, is_active=True)
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /lead-routing-rules/{rule_id}/deactivate ────────────────────────────

@router.post(
    "/lead-routing-rules/{rule_id}/deactivate",
    summary="Deactivate a lead routing rule (admin)",
    response_model=ApiResponse,
)
async def admin_deactivate_rule(rule_id: uuid.UUID, r: Request):
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.admin_toggle_routing_rule(rule_id, is_active=False)
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /seed ────────────────────────────────────────────────────────────────

@router.post(
    "/seed",
    summary="Seed Real Estate category, offerings, and routing rules (admin)",
    response_model=ApiResponse,
)
async def admin_seed_real_estate(r: Request):
    """Idempotent: safe to call multiple times. Creates or updates category,
    two master offerings, and four routing rules by their natural slug/key."""
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.seeders import run_all_seeds
        result = await run_all_seeds(db)
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception:
        await db.rollback()
        raise


# ── POST /expire-drafts ───────────────────────────────────────────────────────

@router.post(
    "/expire-drafts",
    summary="Expire all stale real estate lead drafts (admin / manual trigger)",
    response_model=ApiResponse,
)
async def admin_expire_drafts(r: Request):
    """Marks non-terminal drafts whose expires_at < now() as EXPIRED.
    Normally run by the scheduled job (python -m app.jobs.expire_drafts),
    but this endpoint allows manual triggering from the admin panel."""
    await get_current_user(r)
    db = await anext(get_db())
    try:
        from app.engines.real_estate_lead.draft_expiry import DraftExpiryService
        svc    = DraftExpiryService(db=db)
        result = await svc.expire_all()
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception:
        await db.rollback()
        raise
