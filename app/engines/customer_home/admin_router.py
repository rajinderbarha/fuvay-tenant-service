"""Super-admin controls for safe customer Home merchandising."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, get_current_user, require_super_admin
from app.dependencies.db import get_db
from app.engines.customer_home.merchandising import (
    CustomerHomeMerchandisingService,
    HomeCompositionWrite,
    HomePlacementPatch,
    HomePlacementWrite,
)
from app.schemas.base import ok

router = APIRouter(
    prefix="/v1/admin/customer-home",
    tags=["Admin Customer Home"],
    dependencies=[Depends(require_super_admin)],
)
service = CustomerHomeMerchandisingService()


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("/placements", summary="List Home placement controls and content")
async def list_placements(request: Request, db: AsyncSession = Depends(get_db)):
    return ok(await service.list(db), _rid(request), "admin.customer_home")


@router.get("/composition", summary="Get the ordered native Home composition")
async def get_composition(request: Request, db: AsyncSession = Depends(get_db)):
    return ok(await service.get_composition(db), _rid(request), "admin.customer_home")


@router.put("/composition", summary="Publish the ordered native Home composition")
async def update_composition(
    body: HomeCompositionWrite,
    request: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(
        await service.update_composition(
            db,
            body=body,
            actor_user_id=uuid.UUID(user.user_id),
            request_id=_rid(request),
        ),
        _rid(request),
        "admin.customer_home",
    )


@router.post("/placements", summary="Create a Home placement item")
async def create_placement(
    body: HomePlacementWrite,
    request: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await service.create(
        db,
        body=body,
        actor_user_id=uuid.UUID(user.user_id),
    )
    return ok(data, _rid(request), "admin.customer_home")


@router.put("/placements/{campaign_id}", summary="Update a Home placement item")
async def update_placement(
    campaign_id: uuid.UUID,
    body: HomePlacementPatch,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await service.update(db, campaign_id=campaign_id, body=body)
    return ok(data, _rid(request), "admin.customer_home")


@router.post("/placements/{campaign_id}/archive", summary="Archive a Home placement item")
async def archive_placement(
    campaign_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return ok(
        await service.archive(db, campaign_id),
        _rid(request),
        "admin.customer_home",
    )
