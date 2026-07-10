"""Admin Customer Flow Config Router — Sprint 14.

Endpoints for managing per-category customer flow configuration.
Super Admin only.
"""
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.customer_flow.service import CustomerCategoryFlowService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin", tags=["Admin Customer Flow Config"])


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> CustomerCategoryFlowService:
    return CustomerCategoryFlowService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get(
    "/categories/{category_id}/customer-flow",
    response_model=ApiResponse[dict],
    summary="Get customer flow config for a category",
    tags=["Admin Customer Flow Config"],
)
async def get_customer_flow_config(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(get_current_user),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """Returns the customer flow configuration for the given category."""
    data = await svc.admin_get_flow_config(category_id)
    return ok(data, _rid(r), "customer_flow")


@router.put(
    "/categories/{category_id}/customer-flow",
    response_model=ApiResponse[dict],
    summary="Create or update customer flow config",
    tags=["Admin Customer Flow Config"],
)
async def upsert_customer_flow_config(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Creates or updates the customer flow config for a category.
    Validates flow_type and component_key against allowed values.
    Also mirrors the flow fields back to the service_categories row.

    Allowed customer_flow_type values:
        service_booking, appointment_booking, lead_capture,
        order_flow, inquiry_flow, product_inquiry, unsupported

    Allowed frontend_component_key values:
        ServiceBookingFlow, AppointmentBookingFlow, LeadCaptureFlow,
        OrderFlow, InquiryFlow, ProductInquiryFlow, UnsupportedFlow
    """
    body = await r.json()
    data = await svc.admin_upsert_flow_config(category_id, body)
    return ok(data, _rid(r), "customer_flow")


@router.post(
    "/categories/{category_id}/customer-flow/activate",
    response_model=ApiResponse[dict],
    summary="Activate customer flow config",
    tags=["Admin Customer Flow Config"],
)
async def activate_customer_flow_config(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """Activates the customer flow config for the given category."""
    data = await svc.admin_activate_flow_config(category_id)
    return ok(data, _rid(r), "customer_flow")


@router.post(
    "/categories/{category_id}/customer-flow/deactivate",
    response_model=ApiResponse[dict],
    summary="Deactivate customer flow config",
    tags=["Admin Customer Flow Config"],
)
async def deactivate_customer_flow_config(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """Deactivates the customer flow config. Category will be unavailable to customers."""
    data = await svc.admin_deactivate_flow_config(category_id)
    return ok(data, _rid(r), "customer_flow")
