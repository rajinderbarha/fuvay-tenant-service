"""Admin provider, staff, and customer directories scoped by vertical.

Complaint case handling is provider/customer-owned and intentionally absent.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.vertical_directory_scope import (
    VerticalScope,
    require_vertical_domain_scope,
)
from app.engines.vertical_directory.service import (
    VerticalCustomerDirectoryService,
    VerticalProviderDirectoryService,
    VerticalStaffDirectoryService,
)
from app.schemas.base import ApiResponse, ok


router = APIRouter(prefix="/v1/admin/verticals/{vertical}", tags=["Vertical Directory"])
_providers = VerticalProviderDirectoryService()
_staff = VerticalStaffDirectoryService()
_customers = VerticalCustomerDirectoryService()


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("/providers", response_model=ApiResponse)
async def list_providers(
    request: Request, search: str | None = Query(None), status: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("providers", "view")),
):
    data = await _providers.list_providers(
        db, scope, search=search, status=status, page=page, page_size=page_size,
    )
    return ok(data, _rid(request))


@router.get("/providers/summary", response_model=ApiResponse)
async def providers_summary(
    request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("providers", "view")),
):
    return ok(await _providers.get_summary(db, scope), _rid(request))


@router.get("/providers/{tenant_id}", response_model=ApiResponse)
async def get_provider(
    tenant_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("providers", "view")),
):
    return ok(await _providers.get_provider(db, scope, tenant_id), _rid(request))


@router.get("/staff", response_model=ApiResponse)
async def list_staff(
    request: Request, search: str | None = Query(None),
    verification_status: str | None = Query(None),
    assignment_status: str | None = Query(None), availability: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    data = await _staff.list_staff(
        db, scope, search=search, verification_status=verification_status,
        assignment_status=assignment_status, availability=availability,
        page=page, page_size=page_size,
    )
    return ok(data, _rid(request))


@router.get("/staff/summary", response_model=ApiResponse)
async def staff_summary(
    request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_summary(db, scope), _rid(request))


@router.get("/staff/export", response_model=ApiResponse)
async def staff_export(
    request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "export")),
):
    return ok(await _staff.list_staff(db, scope, page=1, page_size=1000), _rid(request))


@router.get("/staff/{staff_id}", response_model=ApiResponse)
async def get_staff(
    staff_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_staff_detail(db, scope, staff_id), _rid(request))


@router.get("/staff/{staff_id}/capabilities", response_model=ApiResponse)
async def staff_capabilities(
    staff_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_capabilities(db, scope, staff_id), _rid(request))


@router.get("/staff/{staff_id}/workload", response_model=ApiResponse)
async def staff_workload(
    staff_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_workload(db, scope, staff_id), _rid(request))


@router.get("/staff/{staff_id}/performance", response_model=ApiResponse)
async def staff_performance(
    staff_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "view")),
):
    return ok(await _staff.get_performance(db, scope, staff_id), _rid(request))


@router.get("/staff/{staff_id}/activity", response_model=ApiResponse)
async def staff_activity(
    staff_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "audit")),
):
    return ok(await _staff.get_activity(db, scope, staff_id), _rid(request))


class StaffActionRequest(BaseModel):
    reason: str = ""


async def _staff_action(
    action: str, staff_id: uuid.UUID, body: StaffActionRequest,
    request: Request, db: AsyncSession, scope: VerticalScope,
):
    method = getattr(_staff, action)
    data = await method(db, scope, staff_id, reason=body.reason, actor=scope.actor)
    return ok(data, _rid(request))


@router.post("/staff/{staff_id}/request-changes", response_model=ApiResponse)
async def staff_request_changes(
    staff_id: uuid.UUID, body: StaffActionRequest, request: Request,
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "request_changes")),
):
    return await _staff_action("request_changes", staff_id, body, request, db, scope)


@router.post("/staff/{staff_id}/verify", response_model=ApiResponse)
async def staff_verify(
    staff_id: uuid.UUID, body: StaffActionRequest, request: Request,
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "verify")),
):
    return await _staff_action("verify", staff_id, body, request, db, scope)


@router.post("/staff/{staff_id}/reject", response_model=ApiResponse)
async def staff_reject(
    staff_id: uuid.UUID, body: StaffActionRequest, request: Request,
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "verify")),
):
    return await _staff_action("reject", staff_id, body, request, db, scope)


@router.post("/staff/{staff_id}/restrict", response_model=ApiResponse)
async def staff_restrict(
    staff_id: uuid.UUID, body: StaffActionRequest, request: Request,
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "restrict")),
):
    return await _staff_action("restrict", staff_id, body, request, db, scope)


@router.post("/staff/{staff_id}/suspend", response_model=ApiResponse)
async def staff_suspend(
    staff_id: uuid.UUID, body: StaffActionRequest, request: Request,
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "suspend")),
):
    return await _staff_action("suspend", staff_id, body, request, db, scope)


@router.post("/staff/{staff_id}/reactivate", response_model=ApiResponse)
async def staff_reactivate(
    staff_id: uuid.UUID, body: StaffActionRequest, request: Request,
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("staff", "reactivate")),
):
    return await _staff_action("reactivate", staff_id, body, request, db, scope)


@router.get("/customers", response_model=ApiResponse)
async def list_customers(
    request: Request, search: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("customers", "view")),
):
    data = await _customers.list_customers(
        db, scope, search=search, page=page, page_size=page_size,
    )
    return ok(data, _rid(request))


@router.get("/customers/summary", response_model=ApiResponse)
async def customers_summary(
    request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("customers", "view")),
):
    return ok(await _customers.get_summary(db, scope), _rid(request))


@router.get("/customers/{customer_id}", response_model=ApiResponse)
async def get_customer(
    customer_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("customers", "view")),
):
    return ok(await _customers.get_customer(db, scope, customer_id), _rid(request))
