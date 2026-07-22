"""Phase 2A — Technician My Work endpoint.

GET /v1/staff/my-work — read-only aggregation over ServiceJob + PartsRequest
for the logged-in technician. See my_work_service.py for derivation logic and
docs/workflow-rearchitecture/phase-01a/my-work-contract.md for the item
contract this implements.

Scope: technician role only, ServiceJob pipeline only. Deliberately excludes
Booking and field_ops Job (see booking-job-canonical-decision.md — those
pipelines remain unresolved and out of scope until separately approved).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.execution.my_work_service import TechnicianMyWorkService

router = APIRouter(prefix="/v1/staff/my-work", tags=["Phase2A-MyWork-Staff"])

_svc = TechnicianMyWorkService()


async def _resolve_staff_member_id(user: UserContext, db: AsyncSession) -> uuid.UUID:
    """Same resolution + fallback as home_service_assignment/staff_router.py
    and execution/home_service_router.py — provider_team_members is
    unpopulated in real/demo data, so ServiceJob.assigned_staff_id actually
    stores the raw auth user id. Kept identical here rather than imported
    from either sibling module to avoid coupling this new read-only endpoint
    to their internal (underscore-prefixed) helpers."""
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember
    res = await db.execute(
        select(ProviderTeamMember.id).where(
            ProviderTeamMember.user_id == uuid.UUID(str(user.user_id))
        )
    )
    row = res.scalars().first()
    if row:
        return row
    return uuid.UUID(str(user.user_id))


@router.get("", summary="My Work — technician action queue")
async def get_my_work(
    r: Request,
    category: str | None = Query(default=None, description="Filter: URGENT, REQUIRES_MY_ACTION, WAITING_FOR_OTHERS, SCHEDULED, FAILED"),
    priority: str | None = Query(default=None, description="Filter: urgent, normal"),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—")
    staff_id = await _resolve_staff_member_id(user, db)
    tenant_id = uuid.UUID(str(user.tenant_id))

    result = await _svc.get_items(db, staff_id, tenant_id)

    items = result["items"]
    if category:
        items = [it for it in items if it["category"] == category.upper()]
    if priority:
        items = [it for it in items if it["priority"] == priority.lower()]

    return ok(
        {
            "items": items,
            "count": len(items),
            "total_before_filter": result["count"],
            "sources_unavailable": result["sources_unavailable"],
        },
        rid,
        "staff-my-work",
    )
