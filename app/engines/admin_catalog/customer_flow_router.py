"""Sprint 34J — Customer Flow Router.

Routers:
  customer_router  — /v1/customer/flow  (public + customer auth)
  admin_router     — /v1/admin/customer-flow  (super-admin only)

Customer endpoints expose only active catalog choices validated by backend.
AI cannot invent IDs. All selections pass through backend validation.
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_super_admin, UserContext
from app.dependencies.db import get_db
from app.engines.admin_catalog.customer_flow_service import CustomerFlowService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("customer_flow_router")

# ── Customer-facing router (public catalog + auth for drafts) ─────────────────
customer_router = APIRouter(
    prefix="/v1/customer/flow",
    tags=["Customer Booking Flow"],
)

# ── Admin oversight router ────────────────────────────────────────────────────
admin_router = APIRouter(
    prefix="/v1/admin/customer-flow",
    tags=["Admin Customer Flow"],
)


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> CustomerFlowService:
    return CustomerFlowService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC CATALOG — no auth required
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@customer_router.get(
    "/categories",
    response_model=ApiResponse[dict],
    summary="List active categories visible to customers",
)
async def customer_list_categories(
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
):
    return ok(await svc.list_active_categories(), _rid(r))


@customer_router.get(
    "/services",
    response_model=ApiResponse[dict],
    summary="List active services for a category",
)
async def customer_list_services(
    r: Request,
    category_id: Optional[uuid.UUID] = Query(None),
    svc: CustomerFlowService = Depends(_svc),
):
    return ok(await svc.list_active_services(category_id=category_id), _rid(r))


@customer_router.get(
    "/flow-config",
    response_model=ApiResponse[dict],
    summary="Get flow config for a category (service_booking / appointment_booking / lead_capture)",
)
async def customer_get_flow_config(
    r: Request,
    category_id: uuid.UUID = Query(...),
    svc: CustomerFlowService = Depends(_svc),
):
    return ok(await svc.get_flow_config(category_id), _rid(r))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DRAFT ENDPOINTS — customer auth required
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@customer_router.post(
    "/drafts",
    response_model=ApiResponse[dict],
    summary="Start a new booking draft",
)
async def create_draft(
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    body          = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id   = uuid.UUID(u.user_id)
    flow_type     = body.get("flow_type", "service_booking")
    category_id   = uuid.UUID(body["category_id"]) if body.get("category_id") else None
    service_id    = uuid.UUID(body["service_id"])  if body.get("service_id")  else None
    ai_session_id = uuid.UUID(body["ai_session_id"]) if body.get("ai_session_id") else None
    result = await svc.create_draft(
        flow_type=flow_type,
        customer_id=customer_id,
        ai_session_id=ai_session_id,
        category_id=category_id,
        service_id=service_id,
        extra_fields=body.get("extra_fields"),
    )
    return ok(result, _rid(r))


@customer_router.get(
    "/drafts",
    response_model=ApiResponse[dict],
    summary="List my booking drafts",
)
async def list_drafts(
    r: Request,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    return ok(
        await svc.list_drafts(
            customer_id=uuid.UUID(u.user_id),
            status=status,
            page=page,
            page_size=page_size,
        ),
        _rid(r),
    )


@customer_router.get(
    "/drafts/{draft_id}",
    response_model=ApiResponse[dict],
    summary="Get a specific booking draft",
)
async def get_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    return ok(await svc.get_draft(draft_id, uuid.UUID(u.user_id)), _rid(r))


@customer_router.patch(
    "/drafts/{draft_id}",
    response_model=ApiResponse[dict],
    summary="Update a booking draft (catalog selections, address, contact info)",
)
async def update_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    body = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    # Convert string UUIDs to UUID objects where needed
    for field in ("category_id", "service_id", "brand_id", "issue_type_id", "selected_tenant_id"):
        if body.get(field):
            body[field] = uuid.UUID(str(body[field]))
    return ok(await svc.update_draft(draft_id, uuid.UUID(u.user_id), **body), _rid(r))


@customer_router.post(
    "/drafts/{draft_id}/estimate",
    response_model=ApiResponse[dict],
    summary="Get a price estimate for this draft",
)
async def estimate_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    return ok(await svc.estimate_draft(draft_id, uuid.UUID(u.user_id)), _rid(r))


@customer_router.post(
    "/drafts/{draft_id}/confirm",
    response_model=ApiResponse[dict],
    summary="Confirm a booking draft — triggers provider assignment flow",
)
async def confirm_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    body          = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id   = uuid.UUID(u.user_id)
    result = await svc.confirm_draft(
        draft_id=draft_id,
        customer_id=customer_id,
        customer_name=body.get("customer_name"),
        customer_phone=body.get("customer_phone"),
        customer_email=body.get("customer_email"),
    )
    return ok(result, _rid(r))


@customer_router.post(
    "/drafts/{draft_id}/cancel",
    response_model=ApiResponse[dict],
    summary="Cancel a booking draft",
)
async def cancel_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    u: UserContext = Depends(get_current_user),
):
    return ok(await svc.cancel_draft(draft_id, uuid.UUID(u.user_id)), _rid(r))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADMIN OVERSIGHT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@admin_router.get(
    "/flow-configs",
    response_model=ApiResponse[dict],
    summary="List all customer flow configs (admin)",
)
async def admin_list_flow_configs(
    r: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    svc: CustomerFlowService = Depends(_svc),
    _: UserContext = Depends(require_super_admin),
):
    return ok(await svc.list_flow_configs(page=page, page_size=page_size), _rid(r))


@admin_router.get(
    "/drafts",
    response_model=ApiResponse[dict],
    summary="List all customer booking drafts across all customers (admin oversight)",
)
async def admin_list_drafts(
    r: Request,
    status: Optional[str] = Query(None),
    flow_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    svc: CustomerFlowService = Depends(_svc),
    _: UserContext = Depends(require_super_admin),
):
    return ok(
        await svc.admin_list_drafts(
            status=status,
            flow_type=flow_type,
            page=page,
            page_size=page_size,
        ),
        _rid(r),
    )


@admin_router.get(
    "/drafts/{draft_id}",
    response_model=ApiResponse[dict],
    summary="Get any booking draft (admin)",
)
async def admin_get_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: CustomerFlowService = Depends(_svc),
    _: UserContext = Depends(require_super_admin),
):
    return ok(await svc.get_draft(draft_id), _rid(r))
