"""HOME-SERVICES-FINANCE: Home Services → Finance → Monetization.

Canonical route: /admin/home-services/finance?tab=monetization
Canonical API root: /v1/admin/home-services/finance/monetization

This is NOT a second monetization engine -- every endpoint here calls the
SAME VerticalMonetizationPolicyService/calculation_service used by the
generic Platform > Finance > Vertical Monetization workspace, with the
vertical hardcoded server-side to "home_services" (never a client-supplied
or URL-supplied value) so this route can never read or mutate another
vertical's policy.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import permission_checker
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException, VerticalDisabledException
from app.schemas.base import ApiResponse, ok
from app.engines.vertical_catalog.models import Vertical
from app.engines.vertical_monetization.policy_service import VerticalMonetizationPolicyService
from app.engines.vertical_monetization.models import VerticalMonetizationPolicy
from app.engines.vertical_monetization.calculation_service import calculate_customer_platform_fee, to_minor

router = APIRouter(prefix="/v1/admin/home-services/finance/monetization", tags=["Home Services Finance — Monetization"])
_svc = VerticalMonetizationPolicyService()
_HS_KEY = "home_services"
_HS_LIVE_PROVIDER_MODELS = {
    "NONE", "COMPLETION_CREDITS", "PERCENTAGE_COMMISSION", "FIXED_COMPLETION_CHARGE",
}


def _validate_hs_runtime(payload: dict) -> list[str]:
    model = payload.get("provider_model", "NONE")
    if model not in _HS_LIVE_PROVIDER_MODELS:
        return [
            f"{model} can be saved as a draft but cannot be published for Home Services because its runtime charging engine is not implemented."
        ]
    return []


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_hs_action(action: str):
    """Home-Services-only scope + permission check. The vertical is NEVER a
    path/query/body parameter here -- it is the one literal constant
    "home_services", so this route can never be pointed at another
    vertical's policy no matter what a client sends."""
    async def _dep(
        db: AsyncSession = Depends(get_db),
        user: UserContext = Depends(get_current_user),
    ) -> Vertical:
        v = (await db.execute(select(Vertical).where(Vertical.key == _HS_KEY))).scalar_one_or_none()
        if not v:
            raise ServiceOSException("NOT_FOUND", "Home Services vertical not found", status_code=404)
        if not v.is_enabled:
            raise VerticalDisabledException(_HS_KEY)
        permission = f"home_services:finance_monetization:{action}"
        if not permission_checker.has(role=user.role, permission=permission,
                                      overrides=getattr(user, "permission_overrides", None)):
            raise ServiceOSException("PERMISSION_DENIED", f"Missing permission '{permission}'.", status_code=403)
        return v
    return _dep


@router.get("/current", response_model=ApiResponse)
async def get_current(r: Request, db: AsyncSession = Depends(get_db), v: Vertical = Depends(_require_hs_action("view"))):
    return ok(await _svc.get_current(db, _HS_KEY), _rid(r))


@router.get("/draft", response_model=ApiResponse)
async def get_draft(r: Request, db: AsyncSession = Depends(get_db), v: Vertical = Depends(_require_hs_action("view"))):
    return ok(await _svc.get_draft(db, _HS_KEY), _rid(r))


@router.get("/history", response_model=ApiResponse)
async def get_history(r: Request, db: AsyncSession = Depends(get_db), v: Vertical = Depends(_require_hs_action("view"))):
    return ok({"items": await _svc.list_history(db, _HS_KEY)}, _rid(r))


@router.post("/draft", response_model=ApiResponse)
async def save_draft(r: Request, db: AsyncSession = Depends(get_db),
                     user: UserContext = Depends(get_current_user),
                     v: Vertical = Depends(_require_hs_action("draft"))):
    body = await r.json()
    data = await _svc.save_draft(db, _HS_KEY, body, actor_id=uuid.UUID(user.user_id) if user.user_id else None)
    return ok(data, _rid(r))


@router.delete("/draft", response_model=ApiResponse)
async def discard_draft(r: Request, db: AsyncSession = Depends(get_db),
                        user: UserContext = Depends(get_current_user),
                        v: Vertical = Depends(_require_hs_action("draft"))):
    data = await _svc.discard_draft(db, _HS_KEY, actor_id=uuid.UUID(user.user_id) if user.user_id else None)
    return ok(data, _rid(r))


@router.post("/validate", response_model=ApiResponse)
async def validate(r: Request, v: Vertical = Depends(_require_hs_action("validate"))):
    body = await r.json()
    result = _svc.validate(body)
    result["errors"] = [*result["errors"], *_validate_hs_runtime(body)]
    result["valid"] = len(result["errors"]) == 0
    return ok(result, _rid(r))


@router.post("/preview", response_model=ApiResponse)
async def preview(r: Request, v: Vertical = Depends(_require_hs_action("view"))):
    body = await r.json()
    draft = body.get("draft", {})
    example_amount = Decimal(str(body.get("example_service_amount", "500")))
    return ok(_svc.preview(draft, example_amount), _rid(r))


@router.post("/publish", response_model=ApiResponse)
async def publish(r: Request, db: AsyncSession = Depends(get_db),
                  user: UserContext = Depends(get_current_user),
                  v: Vertical = Depends(_require_hs_action("publish"))):
    body = await r.json()
    draft = await _svc.get_draft(db, _HS_KEY)
    if draft:
        runtime_errors = _validate_hs_runtime(draft)
        if runtime_errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(runtime_errors), status_code=422)
    data = await _svc.publish(db, _HS_KEY, actor_id=uuid.UUID(user.user_id) if user.user_id else None,
                              reason=body.get("reason", ""))
    return ok(data, _rid(r))


@router.get("/audit", response_model=ApiResponse)
async def audit(r: Request, limit: int = Query(50, ge=1, le=200),
                db: AsyncSession = Depends(get_db), v: Vertical = Depends(_require_hs_action("audit"))):
    from app.engines.vertical_catalog.models import VerticalAuditLog
    rows = (await db.execute(select(VerticalAuditLog).where(
        VerticalAuditLog.vertical_id == v.id, VerticalAuditLog.action_type.like("monetization.%"),
    ).order_by(VerticalAuditLog.created_at.desc()).limit(limit))).scalars().all()
    return ok({"items": [{
        "id": str(x.id), "action_type": x.action_type, "notes": x.notes,
        "before_state": x.before_state, "after_state": x.after_state,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in rows]}, _rid(r))


# ── Per-Job-Type rules ───────────────────────────────────────────────────────

@router.get("/policies/{policy_id}/job-type-rules", response_model=ApiResponse)
async def list_job_type_rules(policy_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                              v: Vertical = Depends(_require_hs_action("view"))):
    policy = await db.get(VerticalMonetizationPolicy, policy_id)
    if not policy or policy.vertical_id != v.id:
        raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED", "Policy does not belong to Home Services.", status_code=403)
    return ok({"items": await _svc.list_job_type_rules(db, policy_id)}, _rid(r))


@router.put("/policies/{policy_id}/job-type-rules/{job_type_id}", response_model=ApiResponse)
async def upsert_job_type_rule(policy_id: uuid.UUID, job_type_id: uuid.UUID, r: Request,
                               db: AsyncSession = Depends(get_db),
                               v: Vertical = Depends(_require_hs_action("draft"))):
    policy = await db.get(VerticalMonetizationPolicy, policy_id)
    if not policy or policy.vertical_id != v.id:
        raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED", "Policy does not belong to Home Services.", status_code=403)
    body = await r.json()
    return ok(await _svc.upsert_job_type_rule(db, policy_id, job_type_id, body), _rid(r))
