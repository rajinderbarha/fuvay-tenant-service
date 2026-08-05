"""Home Services Customers — tenant-facing router (customer-privacy policy).

Mounted at /v1/tenant/home-services/customers. Wraps the SAME canonical
HomeServicesCustomerDirectoryService the platform-admin console uses
(app.engines.tenant_engine.hs_customer_directory_service) -- no second
aggregation engine -- but every call passes the caller's own JWT-resolved
tenant_id, so:

  - Every query is structurally scoped to this tenant's own bookings/jobs/
    payments/complaints/reviews (never another tenant's history).
  - The service drops raw name/phone/email and cross-tenant "providers used"
    whenever tenant_id is supplied, returning only the tenant-scoped,
    non-reversible customer_alias() instead (see
    app.engines.tenant_engine.customer_operational_access_policy).

There is deliberately no "addresses" or "providers used" route here --
those are exactly the permanent-directory / cross-tenant surfaces the
customer-privacy policy requires removing from any tenant-facing view.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.tenant_engine.hs_customer_directory_service import HomeServicesCustomerDirectoryService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/tenant/home-services/customers", tags=["Tenant Home Services Customers"])
ENGINE_ID = "hs_customer_directory"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException(error_code="TENANT_SCOPE_VIOLATION", detail="No tenant context.", status_code=403)
    return uuid.UUID(user.tenant_id)


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> HomeServicesCustomerDirectoryService:
    return HomeServicesCustomerDirectoryService(db=db, request_id=_rid(r))


@router.get("/metric-definitions", response_model=ApiResponse[dict])
async def metric_definitions(r: Request, s: HomeServicesCustomerDirectoryService = Depends(_svc),
                              u: UserContext = Depends(get_current_user)):
    return ok(s.get_metric_definitions(), _rid(r), ENGINE_ID)


@router.get("/summary", response_model=ApiResponse[dict])
async def summary(r: Request, s: HomeServicesCustomerDirectoryService = Depends(_svc),
                   u: UserContext = Depends(get_current_user)):
    return ok(await s.get_summary(tenant_id=_tid(u)), _rid(r), ENGINE_ID)


@router.get("", response_model=ApiResponse[dict])
async def list_customers(r: Request,
                          q: str | None = Query(None),
                          activity: str | None = Query(None, pattern="^(active|inactive)$"),
                          repeat_status: str | None = Query(None, pattern="^(repeat|one_time|none)$"),
                          page: int = Query(1, ge=1),
                          page_size: int = Query(20, ge=1, le=200),
                          s: HomeServicesCustomerDirectoryService = Depends(_svc),
                          u: UserContext = Depends(get_current_user)):
    return ok(await s.list_customers(
        q=q, activity=activity, repeat_status=repeat_status, page=page, page_size=page_size, tenant_id=_tid(u),
    ), _rid(r), ENGINE_ID)


@router.get("/{customer_id}", response_model=ApiResponse[dict])
async def customer_detail(customer_id: uuid.UUID, r: Request,
                           s: HomeServicesCustomerDirectoryService = Depends(_svc),
                           u: UserContext = Depends(get_current_user)):
    return ok(await s.get_customer_detail(customer_id, tenant_id=_tid(u)), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/jobs", response_model=ApiResponse[dict])
async def customer_jobs(customer_id: uuid.UUID, r: Request,
                         page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                         s: HomeServicesCustomerDirectoryService = Depends(_svc),
                         u: UserContext = Depends(get_current_user)):
    return ok(await s.get_customer_jobs(customer_id, page=page, page_size=page_size, tenant_id=_tid(u)), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/complaints", response_model=ApiResponse[dict])
async def customer_complaints(customer_id: uuid.UUID, r: Request,
                               page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                               s: HomeServicesCustomerDirectoryService = Depends(_svc),
                               u: UserContext = Depends(get_current_user)):
    return ok(await s.get_customer_complaints(customer_id, page=page, page_size=page_size, tenant_id=_tid(u)), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/payments", response_model=ApiResponse[dict])
async def customer_payments(customer_id: uuid.UUID, r: Request,
                             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                             s: HomeServicesCustomerDirectoryService = Depends(_svc),
                             u: UserContext = Depends(get_current_user)):
    return ok(await s.get_customer_payments(customer_id, page=page, page_size=page_size, tenant_id=_tid(u)), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/activity", response_model=ApiResponse[dict])
async def customer_activity(customer_id: uuid.UUID, r: Request,
                             page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
                             s: HomeServicesCustomerDirectoryService = Depends(_svc),
                             u: UserContext = Depends(get_current_user)):
    return ok(await s.get_customer_activity(customer_id, page=page, page_size=page_size, tenant_id=_tid(u)), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/reviews", response_model=ApiResponse[dict])
async def customer_reviews(customer_id: uuid.UUID, r: Request,
                            page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                            s: HomeServicesCustomerDirectoryService = Depends(_svc),
                            u: UserContext = Depends(get_current_user)):
    return ok(await s.get_customer_reviews(customer_id, page=page, page_size=page_size, tenant_id=_tid(u)), _rid(r), ENGINE_ID)
