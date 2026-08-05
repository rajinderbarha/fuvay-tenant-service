"""VERTICAL-MONETIZATION: Platform > Finance > Vertical Monetization admin API.

Only vertical availability (in vertical_catalog) and this policy's own
draft/publish workflow are ever mutated here. Tenant service prices are
never read or written by this router.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.vertical_catalog.models import Vertical, VerticalAuditLog, TenantVerticalEnrollment
from app.engines.vertical_monetization.policy_service import VerticalMonetizationPolicyService
from app.engines.vertical_monetization.models import VerticalMonetizationPolicy

router = APIRouter(prefix="/v1/admin/monetization", tags=["Vertical Monetization"])
_svc = VerticalMonetizationPolicyService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/verticals", response_model=ApiResponse)
async def list_vertical_monetization(
    r: Request,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_MONETIZATION_READ)),
):
    """Policy table rows -- one per Business Vertical, joined to its current
    published policy (or 'Not configured' if none exists yet)."""
    verticals = (await db.execute(select(Vertical).order_by(Vertical.sort_order))).scalars().all()
    rows = []
    configured = 0
    subscription_based = 0
    needs_review = 0
    unsaved_drafts = 0
    invalid_mappings = 0
    for v in verticals:
        current = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        draft = (await db.execute(select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == v.id, VerticalMonetizationPolicy.status == "draft",
        ))).scalar_one_or_none()
        mapping_invalid = False
        if current:
            configured += 1
            if current.provider_model == "SUBSCRIPTION":
                subscription_based += 1
            # Vertical.finance_model is a free descriptive tag set independently
            # of this policy engine (Phase 1 audit: three unconnected "finance
            # model" surfaces exist). When both are set and disagree, that's a
            # real drift signal for an admin to investigate -- surfaced here,
            # not silently ignored or auto-corrected.
            if v.finance_model and v.finance_model.upper() != current.provider_model:
                mapping_invalid = True
                invalid_mappings += 1
        else:
            needs_review += 1
        if draft:
            unsaved_drafts += 1
        rows.append({
            "vertical_key": v.key, "vertical_label": v.label, "is_enabled": v.is_enabled,
            "revenue_model": current.provider_model if current else "NOT_CONFIGURED",
            "provider_charge": _provider_charge_label(current),
            "customer_fee": _customer_fee_label(current),
            "policy_source": "Finance policy" if current else "None",
            "effective_version": current.version_number if current else None,
            "status": ("Active" if current else ("Draft" if draft else "Needs review")),
            "has_draft": draft is not None,
            "mapping_invalid": mapping_invalid,
        })
    return ok({
        "items": rows,
        "summary": {
            "active_verticals": sum(1 for v in verticals if v.is_enabled),
            "configured": configured, "subscription_based": subscription_based,
            "needs_review": needs_review, "unsaved_changes": unsaved_drafts,
            "invalid_mappings": invalid_mappings,
        },
    }, _rid(r), "vertical_monetization")


def _provider_charge_label(p: VerticalMonetizationPolicy | None) -> str:
    if not p or p.provider_model == "NONE":
        return "—"
    if p.provider_model == "COMPLETION_CREDITS":
        return "Per completed job"
    if p.provider_model == "PERCENTAGE_COMMISSION":
        return f"{p.provider_percentage}% commission"
    if p.provider_model == "FIXED_COMPLETION_CHARGE":
        return f"Fixed ₹{(p.provider_fixed_amount_minor or 0)/100:.2f}"
    if p.provider_model == "SUBSCRIPTION":
        return "Monthly plan"
    if p.provider_model == "LEAD_FEE":
        return "Per lead"
    return p.provider_model


def _customer_fee_label(p: VerticalMonetizationPolicy | None) -> str:
    if not p or p.customer_fee_model == "NONE":
        return "0%" if p else "Not applicable"
    if p.customer_fee_model == "PERCENTAGE":
        return f"{p.customer_fee_percentage}%"
    if p.customer_fee_model == "FIXED":
        return f"₹{(p.customer_fee_fixed_amount_minor or 0)/100:.2f}"
    if p.customer_fee_model == "PERCENTAGE_WITH_MIN_MAX":
        return f"{p.customer_fee_percentage}% (₹{(p.customer_fee_min_minor or 0)/100:.0f}–₹{(p.customer_fee_max_minor or 0)/100:.0f})"
    return p.customer_fee_model


@router.get("/verticals/{key}", response_model=ApiResponse)
async def get_vertical_monetization_detail(
    key: str, r: Request, db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_MONETIZATION_READ)),
):
    current = await _svc.get_current(db, key)
    draft = await _svc.get_draft(db, key)
    return ok({"vertical_key": key, "current": current, "draft": draft}, _rid(r), "vertical_monetization")


@router.get("/verticals/{key}/impact", response_model=ApiResponse)
async def get_vertical_monetization_impact(
    key: str, r: Request, db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_MONETIZATION_READ)),
):
    """Selected Policy Inspector's impact numbers -- read-only, never blocked
    by vertical-disabled state (a disabled vertical's historical policy and
    its last-known impact must still be viewable)."""
    return ok(await _svc.get_impact(db, key), _rid(r), "vertical_monetization")


@router.get("/verticals/{key}/history", response_model=ApiResponse)
async def get_policy_history(
    key: str, r: Request, db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_MONETIZATION_READ)),
):
    return ok({"items": await _svc.list_history(db, key)}, _rid(r), "vertical_monetization")


@router.post("/verticals/{key}/draft", response_model=ApiResponse)
async def save_draft(
    key: str, r: Request, db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_MONETIZATION_DRAFT)),
):
    body = await r.json()
    data = await _svc.save_draft(db, key, body, actor_id=uuid.UUID(_user.user_id) if _user.user_id else None)
    return ok(data, _rid(r), "vertical_monetization")


@router.post("/validate", response_model=ApiResponse)
async def validate_policy(r: Request, _user=Depends(require_permission(P.FINANCE_MONETIZATION_DRAFT))):
    body = await r.json()
    return ok(_svc.validate(body), _rid(r), "vertical_monetization")


@router.post("/preview", response_model=ApiResponse)
async def preview_policy(r: Request, _user=Depends(require_permission(P.FINANCE_MONETIZATION_DRAFT))):
    body = await r.json()
    draft = body.get("draft", {})
    example_amount = Decimal(str(body.get("example_service_amount", "500")))
    return ok(_svc.preview(draft, example_amount), _rid(r), "vertical_monetization")


@router.post("/verticals/{key}/publish", response_model=ApiResponse)
async def publish_policy(
    key: str, r: Request, db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_MONETIZATION_PUBLISH)),
):
    body = await r.json()
    data = await _svc.publish(db, key, actor_id=uuid.UUID(_user.user_id) if _user.user_id else None,
                              reason=body.get("reason", ""))
    return ok(data, _rid(r), "vertical_monetization")


@router.get("/verticals/{key}/audit", response_model=ApiResponse)
async def get_monetization_audit(
    key: str, r: Request, limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.FINANCE_AUDIT_READ)),
):
    v = (await db.execute(select(Vertical).where(Vertical.key == key))).scalar_one_or_none()
    if not v:
        return ok({"items": []}, _rid(r), "vertical_monetization")
    rows = (await db.execute(select(VerticalAuditLog).where(
        VerticalAuditLog.vertical_id == v.id, VerticalAuditLog.action_type.like("monetization.%"),
    ).order_by(VerticalAuditLog.created_at.desc()).limit(limit))).scalars().all()
    return ok({"items": [{
        "id": str(x.id), "action_type": x.action_type, "notes": x.notes,
        "before_state": x.before_state, "after_state": x.after_state,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in rows]}, _rid(r), "vertical_monetization")
