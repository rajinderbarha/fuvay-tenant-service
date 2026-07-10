"""Sprint 34D — Brand Customer Catalog Router.

Customer-facing brand endpoints (no auth, read-only, provider-filtered).
Prefix: /v1/customer/catalog/brands
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.admin_catalog.brand_service import BrandService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/catalog/brands", tags=["Customer Catalog Brands"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> BrandService:
    return BrandService(db=db, request_id=_rid(r))


@router.get(
    "",
    response_model=ApiResponse[dict],
    summary="List valid brands for customer booking",
    description=(
        "Returns active brands mapped to the requested service that have at least one "
        "provider supporting them. Brands with zero provider support are hidden. "
        "service_id is the master_service_id."
    ),
)
async def get_customer_brands(
    r: Request,
    service_id: uuid.UUID | None = Query(None),
    zone_id: uuid.UUID | None = Query(None),
    s: BrandService = Depends(_svc),
):
    return ok(await s.get_customer_catalog_brands(service_id=service_id, zone_id=zone_id), _rid(r))


@router.post(
    "/validate",
    response_model=ApiResponse[dict],
    summary="Validate a brand is active and mapped to a service",
    description=(
        "Validates brand_id is active, mapped to service_id, and supported by at least one provider. "
        "Optionally tries fuzzy-match on typed_brand_name."
    ),
)
async def validate_brand(
    r: Request,
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    service_id = uuid.UUID(str(body["service_id"]))
    brand_id = uuid.UUID(str(body["brand_id"]))
    typed_name = body.get("typed_brand_name")
    return ok(await s.validate_brand(service_id, brand_id, typed_name), _rid(r))
