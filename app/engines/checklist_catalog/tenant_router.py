"""Checklist Catalog Engine — TENANT endpoints: choosing which authored
checklist points this provider's technicians must complete per service.

Division of responsibility (product rule):
  ADMIN  authors the library         -> admin_router.py (require_super_admin)
  TENANT selects >= 5 points/service -> here
  RUNTIME narrows each job's checklist to that selection -> service.py

A tenant can only ever choose from what the admin authored AND mapped to that
service's job types; every submitted id is validated server-side in
`svc.set_tenant_selection`, so a crafted payload cannot introduce a checklist
point or borrow one from another service.

`tenant_id` is always taken from the authenticated user context, never from
the path or body -- there is no route here through which one provider could
read or write another provider's selection.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.checklist_catalog import service as svc

router = APIRouter(prefix="/v1/tenant/checklist-selection", tags=["tenant-checklist-selection"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get(
    "/services/{master_service_id}/selectable",
    summary="Checklist points the admin has authored for this service",
    description=(
        "Every point this provider MAY select, from PUBLISHED template versions "
        "mapped to the service's job types. A DRAFT version is never offered."
    ),
)
async def list_selectable(
    master_service_id: uuid.UUID, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    items = await svc.selectable_items_for_service(db, master_service_id)
    readiness = await svc.tenant_selection_readiness(
        db, uuid.UUID(str(user.tenant_id)), master_service_id,
    )
    return ok({"items": items, "readiness": readiness}, _rid(r), "tenant-checklist-selectable")


@router.get(
    "/services/{master_service_id}",
    summary="This provider's current selection + whether the minimum is met",
)
async def get_selection(
    master_service_id: uuid.UUID, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    readiness = await svc.tenant_selection_readiness(
        db, uuid.UUID(str(user.tenant_id)), master_service_id,
    )
    return ok(readiness, _rid(r), "tenant-checklist-selection")


@router.put(
    "/services/{master_service_id}",
    summary="Set this provider's checklist points for a service (minimum 5)",
    description=(
        "Replaces the selection. Returns 422 CHECKLIST_SELECTION_TOO_SMALL with the "
        "shortfall when fewer than the minimum are submitted, and 422 "
        "CHECKLIST_ITEM_NOT_SELECTABLE when an id is not authored for this service. "
        "Deselected points are deactivated, not deleted, so an older job's checklist "
        "remains explainable."
    ),
)
async def set_selection(
    master_service_id: uuid.UUID, body: dict, r: Request,
    user=Depends(require_tenant_owner_mutation), db: AsyncSession = Depends(get_db),
):
    raw = body.get("checklist_item_ids") or []
    item_ids = [uuid.UUID(str(x)) for x in raw]
    result = await svc.set_tenant_selection(
        db, uuid.UUID(str(user.tenant_id)), master_service_id, item_ids,
        selected_by_user_id=uuid.UUID(str(user.user_id)),
    )
    await db.commit()
    return ok(result, _rid(r), "tenant-checklist-selection-set")
