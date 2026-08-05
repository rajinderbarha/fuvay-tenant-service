"""Tenant-facing Home Services Reviews & Service Quality — read aggregation.

Mutations (reply, moderation flag) are NOT here -- see hs_quality_service.py
docstring. The frontend calls the existing, already-secured
POST /v1/provider/reviews/{id}/reply and POST /v1/provider/reviews/{id}/flag.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.schemas.base import ok
from app.engines.customer_reviews.hs_quality_service import (
    get_reviews_summary, get_reviews_kpis, get_rating_trend,
    get_rating_distribution, get_quality_signals, get_review_detail,
)

router = APIRouter(prefix="/v1/tenant/home-services/reviews", tags=["Tenant Home Services Reviews"])


@router.get("")
async def list_reviews_endpoint(
    request: Request,
    rating: int | None = Query(None, ge=1, le=5),
    reply_status: str | None = Query(None),
    technician_id: uuid.UUID | None = Query(None),
    complaint_linked: bool | None = Query(None),
    moderation_status: str | None = Query(None),
    search: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
):
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    tid = uuid.UUID(user.tenant_id)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    failed: list[str] = []
    async def _safe(coro, key):
        try:
            return await coro
        except Exception:
            failed.append(key)
            return None

    reviews = await _safe(get_reviews_summary(
        db, tid, rating=rating, reply_status=reply_status, technician_id=technician_id,
        complaint_linked=complaint_linked, moderation_status=moderation_status,
        search=search, date_from=date_from, date_to=date_to, limit=limit, offset=offset,
    ), "reviews") or {"items": [], "total": 0, "limit": limit, "offset": offset}
    kpis = await _safe(get_reviews_kpis(db, tid), "summary") or None
    trend = await _safe(get_rating_trend(db, tid), "rating_trend") or []
    distribution = await _safe(get_rating_distribution(db, tid), "rating_distribution") or []
    quality = await _safe(get_quality_signals(db, tid), "quality_signals") or None

    return ok({
        "reviews": reviews["items"], "total": reviews["total"], "limit": reviews["limit"], "offset": reviews["offset"],
        "summary": kpis, "rating_trend": trend, "rating_distribution": distribution, "quality_signals": quality,
        "failed_modules": failed, "generated_at": None,
    }, request_id=rid)


@router.get("/{review_id}")
async def get_review_detail_endpoint(
    review_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
):
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    data = await get_review_detail(db, uuid.UUID(user.tenant_id), review_id)
    if not data:
        raise HTTPException(404, "Review not found")
    return ok(data, request_id=rid)
