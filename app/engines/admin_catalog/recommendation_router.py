"""Sprint 34I — Recommendation Rules + Engine routers.

Admin:   /v1/admin/recommendation-rules  (require_super_admin)
Shared:  /v1/recommendations             (require_super_admin or require_technician)
AI:      /v1/ai/recommendations          (require_super_admin — internal/service use)
Context: /v1/admin/bulk-setup/drafts/{id}/recommendations  (require_super_admin)
         /v1/provider/setup/recommendations                 (require_technician)
         /v1/customer/booking/recommendations               (require_customer)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import (
    UserContext,
    require_super_admin,
    require_technician,
    require_customer,
)
from app.engines.admin_catalog.recommendation_engine_service import (
    AdminRecommendationRuleService,
    RecommendationEngineService,
)

# ── Routers ────────────────────────────────────────────────────────────────────

admin_router    = APIRouter(prefix="/v1/admin/recommendation-rules",    tags=["Recommendation Rules"])
shared_router   = APIRouter(prefix="/v1/recommendations",               tags=["Recommendation Engine"])
ai_router       = APIRouter(prefix="/v1/ai",                            tags=["AI Recommendations"])
ctx_admin_router = APIRouter(prefix="/v1/admin/bulk-setup",             tags=["Admin Bulk Setup Recommendations"])
ctx_provider_router = APIRouter(prefix="/v1/provider/setup",            tags=["Provider Recommendations"])
ctx_customer_router = APIRouter(prefix="/v1/customer/booking",          tags=["Customer Recommendations"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rule_svc(r: Request, db: AsyncSession, u: UserContext) -> AdminRecommendationRuleService:
    return AdminRecommendationRuleService(
        db=db,
        actor_id=uuid.UUID(u.user_id) if u.user_id else uuid.uuid4(),
        actor_role=u.role,
        request_id=getattr(r.state, "request_id", str(uuid.uuid4())),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — Rule CRUD + Lifecycle + Simulate + Results
# ═══════════════════════════════════════════════════════════════════════════════

@admin_router.get("", summary="List recommendation rules")
async def list_rules(
    r: Request,
    status: str | None = Query(None),
    rule_type: str | None = Query(None),
    scope: str | None = Query(None),
    vertical_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    return await svc.list_rules(status=status, rule_type=rule_type, scope=scope,
                                vertical_type=vertical_type, page=page, page_size=page_size)


@admin_router.post("", summary="Create recommendation rule")
async def create_rule(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.create_rule(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_router.get("/{rule_id}", summary="Get recommendation rule")
async def get_rule(
    r: Request,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        rule = await svc.get_rule(rule_id)
        return rule.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@admin_router.put("/{rule_id}", summary="Update recommendation rule")
async def update_rule(
    r: Request,
    rule_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.update_rule(rule_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_router.delete("/{rule_id}", summary="Delete (archive) recommendation rule")
async def delete_rule(
    r: Request,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.delete_rule(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@admin_router.post("/{rule_id}/activate", summary="Activate recommendation rule")
async def activate_rule(
    r: Request,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.activate_rule(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_router.post("/{rule_id}/deactivate", summary="Deactivate recommendation rule")
async def deactivate_rule(
    r: Request,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.deactivate_rule(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_router.post("/{rule_id}/archive", summary="Archive recommendation rule")
async def archive_rule(
    r: Request,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.archive_rule(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_router.post("/{rule_id}/simulate", summary="Simulate recommendation rule without mutation")
async def simulate_rule(
    r: Request,
    rule_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    try:
        return await svc.simulate_rule(rule_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@admin_router.get("/results/list", summary="List recommendation results")
async def list_results(
    r: Request,
    context_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _rule_svc(r, db, u)
    return await svc.list_results(context_type=context_type, status=status,
                                  page=page, page_size=page_size)


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED — Evaluate / Validate / Accept / Reject
# ═══════════════════════════════════════════════════════════════════════════════

@shared_router.post("/evaluate", summary="Evaluate recommendation rules for a context")
async def evaluate_recommendations(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    engine = RecommendationEngineService(db)
    return await engine.get_recommendations(body)


@shared_router.post("/validate", summary="Validate a specific recommended entity")
async def validate_recommendation(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    engine = RecommendationEngineService(db)
    entity_type = body.get("entity_type")
    entity_id = body.get("entity_id")
    if not entity_type or not entity_id:
        raise HTTPException(status_code=400, detail="entity_type and entity_id are required")
    try:
        return await engine.validate_recommendation(entity_type, entity_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@shared_router.post("/{result_id}/accept", summary="Accept a recommendation result")
async def accept_recommendation(
    r: Request,
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    engine = RecommendationEngineService(db)
    try:
        return await engine.accept_recommendation(result_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@shared_router.post("/{result_id}/reject", summary="Reject a recommendation result")
async def reject_recommendation(
    r: Request,
    result_id: uuid.UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    engine = RecommendationEngineService(db)
    reason = (body or {}).get("reason")
    try:
        return await engine.reject_recommendation(result_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# AI — Backend-validated recommendations for AI/chat context
# ═══════════════════════════════════════════════════════════════════════════════

@ai_router.post("/recommendations", summary="AI-safe recommendation endpoint (backend-validated)")
async def ai_recommendations(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    """AI can request backend recommendations; cannot invent IDs or bypass validation."""
    context = {**body, "context_type": body.get("context_type", "ai_chat")}
    engine = RecommendationEngineService(db)
    result = await engine.get_recommendations(context)

    allowed_next_steps: list[str] = []
    for rec in result["recommendations"]:
        et = rec.get("entity_type", "")
        if et == "issue_type" and "water" in rec.get("name", "").lower():
            allowed_next_steps.append("ask_photo")
        if et == "brand":
            allowed_next_steps.append("ask_brand")
        if et == "service_option":
            allowed_next_steps.append("ask_option")

    return {
        "success": True,
        "data": {
            "recommendations":  result["recommendations"],
            "allowed_next_steps": list(dict.fromkeys(allowed_next_steps)),
            "warnings":          result["warnings"],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT — Draft/Setup/Booking-specific recommendation endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@ctx_admin_router.post("/drafts/{draft_id}/recommendations", summary="Get recommendations for bulk setup draft")
async def bulk_setup_draft_recommendations(
    r: Request,
    draft_id: uuid.UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    ctx = {**(body or {}), "context_type": "admin_bulk_setup", "context_id": str(draft_id)}
    engine = RecommendationEngineService(db)
    return await engine.get_recommendations(ctx)


@ctx_provider_router.post("/recommendations", summary="Get recommendations for provider setup")
async def provider_setup_recommendations(
    r: Request,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_technician),
):
    ctx = {**(body or {}), "context_type": "tenant_setup"}
    engine = RecommendationEngineService(db)
    return await engine.get_recommendations(ctx)


@ctx_customer_router.post("/recommendations", summary="Get customer-safe booking recommendations")
async def customer_booking_recommendations(
    r: Request,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_customer),
):
    ctx = {**(body or {}), "context_type": "customer_booking"}
    engine = RecommendationEngineService(db)
    result = await engine.get_recommendations(ctx)
    safe_recs = [
        {k: v for k, v in rec.items() if k not in ("rule_id", "rule_code")}
        for rec in result["recommendations"]
        if rec.get("entity_type") in ("issue_type", "service_option", "brand")
    ]
    return {"recommendations": safe_recs, "warnings": result["warnings"]}
