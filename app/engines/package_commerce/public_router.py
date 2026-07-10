"""Public (unauthenticated) packages endpoint.

Signup page calls this to load active, signup-visible packages
filtered by vertical_type.  No auth required.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.package_commerce.service import PackageCommerceService

router = APIRouter(tags=["Public Packages"])

ENGINE_ID = "package_credit"


def _svc(db: AsyncSession, request: Request) -> PackageCommerceService:
    return PackageCommerceService(
        db=db,
        request_id=request.headers.get("X-Request-ID", "—"),
        actor_id=None,
        actor_role="public",
    )


def _ok(data: dict, request: Request) -> dict:
    return {
        "success": True,
        "data": data,
        "request_id": request.headers.get("X-Request-ID", "—"),
        "engine_id": ENGINE_ID,
    }


@router.get(
    "/v1/public/packages",
    summary="List public signup packages",
    tags=["Public Packages"],
)
async def list_public_packages(
    request: Request,
    vertical_type: str | None = Query(None, description="Filter by vertical (e.g. home_services)"),
    package_context: str | None = Query(None, description="Context hint (signup, upgrade …)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns active, signup-visible packages for the given vertical.
    No authentication required — called by the public registration page.
    """
    svc = _svc(db, request)
    result = await svc.list_public_packages(
        vertical_type=vertical_type,
        package_context=package_context,
    )
    return _ok(result, request)
