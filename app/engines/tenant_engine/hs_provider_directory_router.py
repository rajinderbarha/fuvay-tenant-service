"""Home Services Provider Directory — admin router.

Mounted at /v1/admin/home-services/providers. Summary and list both call
the same HomeServicesProviderDirectoryService._base_query -- see that
file's module docstring for why this structurally prevents the "1 provider
but empty table" mismatch class of bug.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.engines.tenant_engine.hs_provider_directory_service import HomeServicesProviderDirectoryService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/home-services/providers", tags=["Home Services Provider Directory"])
ENGINE_ID = "hs_provider_directory"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.HOME_SERVICES_PROVIDERS_VIEW))) -> HomeServicesProviderDirectoryService:
    return HomeServicesProviderDirectoryService(db=db, request_id=_rid(r),
                                                 actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


@router.get("/summary", response_model=ApiResponse[dict], summary="Home Services provider directory summary")
async def hs_providers_summary(r: Request, q: str | None = Query(None),
                                s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_summary(q=q), _rid(r), ENGINE_ID)


@router.get("", response_model=ApiResponse[dict], summary="List Home Services providers")
async def hs_providers_list(r: Request,
                             q: str | None = Query(None),
                             status: str | None = Query(None),
                             status_in: str | None = Query(None, description="Comma-separated statuses, e.g. 'suspended,archived'"),
                             verification_status: str | None = Query(None),
                             city: str | None = Query(None),
                             state: str | None = Query(None),
                             health_band: str | None = Query(None),
                             page: int = Query(1, ge=1),
                             page_size: int = Query(20, ge=1, le=200),
                             sort_by: str = Query("created_at"),
                             sort_dir: str = Query("desc"),
                             s: HomeServicesProviderDirectoryService = Depends(_svc)):
    status_list = [x.strip() for x in status_in.split(",") if x.strip()] if status_in else None
    return ok(await s.list_providers(
        q=q, status=status, status_in=status_list, verification_status=verification_status,
        city=city, state=state, health_band=health_band,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
    ), _rid(r), ENGINE_ID)


@router.get("/{provider_id}", response_model=ApiResponse[dict], summary="Home Services provider detail")
async def hs_provider_detail(provider_id: uuid.UUID, r: Request,
                              s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_detail(provider_id), _rid(r), ENGINE_ID)


@router.get("/{provider_id}/finance", response_model=ApiResponse[dict], summary="Home Services provider finance (Provider 360 Finance tab)")
async def hs_provider_finance(provider_id: uuid.UUID, r: Request,
                               s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_finance(provider_id), _rid(r), ENGINE_ID)


@router.get("/{provider_id}/quality", response_model=ApiResponse[dict], summary="Home Services provider quality & complaints (Provider 360 tab)")
async def hs_provider_quality(provider_id: uuid.UUID, r: Request,
                               page: int = Query(1, ge=1),
                               page_size: int = Query(20, ge=1, le=100),
                               s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_quality(provider_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{provider_id}/team", response_model=ApiResponse[dict], summary="Home Services provider team & capacity (Provider 360 tab)")
async def hs_provider_team(provider_id: uuid.UUID, r: Request,
                            page: int = Query(1, ge=1),
                            page_size: int = Query(20, ge=1, le=100),
                            s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_team(provider_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{provider_id}/operations", response_model=ApiResponse[dict], summary="Home Services provider operations (Provider 360 tab)")
async def hs_provider_operations(provider_id: uuid.UUID, r: Request,
                                  page: int = Query(1, ge=1),
                                  page_size: int = Query(20, ge=1, le=100),
                                  s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_operations(provider_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{provider_id}/activity", response_model=ApiResponse[dict], summary="Home Services provider documents & activity (Provider 360 tab)")
async def hs_provider_activity(provider_id: uuid.UUID, r: Request,
                                page: int = Query(1, ge=1),
                                page_size: int = Query(30, ge=1, le=100),
                                s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_activity(provider_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{provider_id}/services", response_model=ApiResponse[dict], summary="Home Services provider services & coverage (Provider 360 tab)")
async def hs_provider_services(provider_id: uuid.UUID, r: Request,
                                s: HomeServicesProviderDirectoryService = Depends(_svc)):
    return ok(await s.get_provider_services(provider_id), _rid(r), ENGINE_ID)
