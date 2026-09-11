"""Home Services Customers — admin router. Mounted at
/v1/admin/home-services/customers. Summary and list both call the same
HomeServicesCustomerDirectoryService._customer_aggregates -- see that
file's module docstring for why this prevents a summary/table mismatch.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.engines.tenant_engine.hs_customer_directory_service import HomeServicesCustomerDirectoryService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/home-services/customers", tags=["Home Services Customer Directory"])
ENGINE_ID = "hs_customer_directory"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.HOME_SERVICES_CUSTOMERS_VIEW))) -> HomeServicesCustomerDirectoryService:
    return HomeServicesCustomerDirectoryService(db=db, request_id=_rid(r),
                                                 actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


@router.get("/metric-definitions", response_model=ApiResponse[dict], summary="Home Services customer metric definitions")
async def hs_customer_metric_definitions(r: Request, s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(s.get_metric_definitions(), _rid(r), ENGINE_ID)


@router.get("/summary", response_model=ApiResponse[dict], summary="Home Services customers summary")
async def hs_customers_summary(r: Request, s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_summary(), _rid(r), ENGINE_ID)


@router.get("", response_model=ApiResponse[dict], summary="List Home Services customers")
async def hs_customers_list(r: Request,
                             q: str | None = Query(None, max_length=100),
                             activity: str | None = Query(None, pattern="^(active|inactive)$"),
                             repeat_status: str | None = Query(None, pattern="^(repeat|one_time|none)$"),
                             payment_reliability: str | None = Query(
                                 None, pattern="^(reliable|needs_review|insufficient_data)$",
                             ),
                             complaint_state: str | None = Query(None, pattern="^(open|clear)$"),
                             sort: str = Query(
                                 "last_activity_desc",
                                 pattern="^(last_activity_desc|last_activity_asc|completed_desc|complaints_desc|first_booking_desc)$",
                             ),
                             page: int = Query(1, ge=1),
                             page_size: int = Query(20, ge=1, le=200),
                             s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.list_customers(
        q=q, activity=activity, repeat_status=repeat_status,
        payment_reliability=payment_reliability, complaint_state=complaint_state,
        sort=sort, page=page, page_size=page_size,
    ), _rid(r), ENGINE_ID)


@router.get("/{customer_id}", response_model=ApiResponse[dict], summary="Home Services customer detail")
async def hs_customer_detail(customer_id: uuid.UUID, r: Request,
                              s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_detail(customer_id), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/jobs", response_model=ApiResponse[dict], summary="Home Services customer jobs (Customer 360 tab)")
async def hs_customer_jobs(customer_id: uuid.UUID, r: Request,
                            page: int = Query(1, ge=1),
                            page_size: int = Query(20, ge=1, le=100),
                            s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_jobs(customer_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/payments", response_model=ApiResponse[dict], summary="Home Services customer payments (Customer 360 tab)")
async def hs_customer_payments(customer_id: uuid.UUID, r: Request,
                                page: int = Query(1, ge=1),
                                page_size: int = Query(20, ge=1, le=100),
                                s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_payments(customer_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/complaints", response_model=ApiResponse[dict], summary="Home Services customer complaints (Customer 360 tab)")
async def hs_customer_complaints(customer_id: uuid.UUID, r: Request,
                                  page: int = Query(1, ge=1),
                                  page_size: int = Query(20, ge=1, le=100),
                                  s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_complaints(customer_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/activity", response_model=ApiResponse[dict], summary="Home Services customer activity & audit (Customer 360 tab)")
async def hs_customer_activity(customer_id: uuid.UUID, r: Request,
                                page: int = Query(1, ge=1),
                                page_size: int = Query(30, ge=1, le=100),
                                s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_activity(customer_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/reviews", response_model=ApiResponse[dict], summary="Home Services customer reviews (Customer 360 tab)")
async def hs_customer_reviews(customer_id: uuid.UUID, r: Request,
                               page: int = Query(1, ge=1),
                               page_size: int = Query(20, ge=1, le=100),
                               s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_reviews(customer_id, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.get("/{customer_id}/addresses", response_model=ApiResponse[dict], summary="Home Services customer addresses (Customer 360 tab)")
async def hs_customer_addresses(customer_id: uuid.UUID, r: Request,
                                 s: HomeServicesCustomerDirectoryService = Depends(_svc)):
    return ok(await s.get_customer_addresses(customer_id), _rid(r), ENGINE_ID)
