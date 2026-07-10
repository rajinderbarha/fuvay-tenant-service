"""Location Engine — Router.

Admin and public endpoints for India location hierarchy:
  State → District → City → Zone/Pincode

Admin: /v1/admin/locations/*  (authenticated, write = super_admin)
Public: /v1/public/locations/* (no auth, read-only, for customer/provider forms)
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.location_engine.service import LocationService

router = APIRouter(tags=["Locations"])


def _svc(db: AsyncSession) -> LocationService:
    return LocationService(db)


def _ok(data: dict, request: Request) -> dict:
    return {
        "success": True, "data": data,
        "request_id": request.headers.get("X-Request-ID", "—"),
        "engine_id": "location",
    }


# ══════════════════════════════════════════════════════════════
# STATES
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/locations/states", summary="List states", tags=["Locations"])
async def admin_list_states(
    request: Request,
    country_code: str = Query("IN"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(await _svc(db).list_states(country_code, search, page, page_size), request)


@router.post("/v1/admin/locations/states", status_code=201, tags=["Locations"])
async def admin_create_state(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_super_admin),
) -> dict:
    return _ok(await _svc(db).create_state(payload), request)


# ══════════════════════════════════════════════════════════════
# DISTRICTS
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/locations/districts", summary="List districts for a state", tags=["Locations"])
async def admin_list_districts(
    request: Request,
    state_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(await _svc(db).list_districts(state_id, search, page, page_size), request)


@router.post("/v1/admin/locations/states/{state_id}/districts", status_code=201, tags=["Locations"])
async def admin_create_district(
    state_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_super_admin),
) -> dict:
    return _ok(await _svc(db).create_district(state_id, payload), request)


# ══════════════════════════════════════════════════════════════
# CITIES
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/locations/cities", summary="List cities for a district", tags=["Locations"])
async def admin_list_cities(
    request: Request,
    district_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(await _svc(db).list_cities(district_id, search, page, page_size), request)


@router.post("/v1/admin/locations/districts/{district_id}/cities", status_code=201, tags=["Locations"])
async def admin_create_city(
    district_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_super_admin),
) -> dict:
    return _ok(await _svc(db).create_city(district_id, payload), request)


# ══════════════════════════════════════════════════════════════
# ZONES
# ══════════════════════════════════════════════════════════════

@router.get("/v1/admin/locations/zones", summary="List zones for a city", tags=["Locations"])
async def admin_list_zones(
    request: Request,
    city_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(await _svc(db).list_zones(city_id, search, page, page_size), request)


@router.post("/v1/admin/locations/cities/{city_id}/zones", status_code=201, tags=["Locations"])
async def admin_create_zone(
    city_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_super_admin),
) -> dict:
    return _ok(await _svc(db).create_zone(city_id, payload), request)


# ── City tiers ─────────────────────────────────────────────────

@router.get("/v1/admin/locations/city-tiers", summary="Get city tier options", tags=["Locations"])
async def admin_list_city_tiers(
    request: Request, db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(get_current_user),
) -> dict:
    return _ok(await _svc(db).list_city_tiers(), request)


# ══════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS (no auth required)
# ══════════════════════════════════════════════════════════════

@router.get("/v1/public/locations/states", tags=["Locations"], include_in_schema=True)
async def public_list_states(
    request: Request,
    country_code: str = Query("IN"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return _ok(await _svc(db).list_states(country_code, search, page, page_size), request)


@router.get("/v1/public/locations/districts", tags=["Locations"])
async def public_list_districts(
    request: Request,
    state_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return _ok(await _svc(db).list_districts(state_id, search, page, page_size), request)


@router.get("/v1/public/locations/cities", tags=["Locations"])
async def public_list_cities(
    request: Request,
    district_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return _ok(await _svc(db).list_cities(district_id, search, page, page_size), request)


@router.get("/v1/public/locations/zones", tags=["Locations"])
async def public_list_zones(
    request: Request,
    city_id: uuid.UUID = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return _ok(await _svc(db).list_zones(city_id, search, page, page_size), request)
