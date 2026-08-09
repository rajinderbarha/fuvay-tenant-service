"""Admin control of the customer Home layout.

Mirrors the customer_campaigns admin router's conventions (super-admin only,
`ok(...)` envelopes, request-id threading) rather than introducing a second
shape for the same kind of platform-level configuration.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.engines.customer_home.constants import HOME_SECTION_KEYS
from app.engines.customer_home.section_service import HomeSectionService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/home-sections", tags=["Customer Home Layout (Admin)"])
ENGINE_ID = "customer_home"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse[dict], summary="List Home sections and their order")
async def list_sections(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await HomeSectionService(db).list_admin()
    # `known_keys` is returned so the admin UI can label every row from one
    # source rather than keeping its own copy of the vocabulary in sync.
    return ok({"items": items, "total": len(items), "known_keys": list(HOME_SECTION_KEYS)},
              _rid(r), ENGINE_ID)


@router.put("/{section_key}", response_model=ApiResponse[dict], summary="Enable, rename or move one section")
async def update_section(
    section_key: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await HomeSectionService(db).update(section_key, body, actor_id=uuid.UUID(u.user_id))
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/reorder", response_model=ApiResponse[dict], summary="Set the full section order in one call")
async def reorder_sections(
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await HomeSectionService(db).reorder(
        body.get("ordered_keys") or [], actor_id=uuid.UUID(u.user_id))
    return ok({"items": items, "total": len(items)}, _rid(r), ENGINE_ID)
