"""Customer Category Flow — Public/Customer API Router (Sprint 14).

Customer-safe endpoints. Returns only public metadata — no provider-private fields.
Authentication: optional (guest browsing supported for category/offering listings).
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user_optional, UserContext
from app.dependencies.db import get_db
from app.engines.customer_flow.service import CustomerCategoryFlowService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer", tags=["Customer Categories"])


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> CustomerCategoryFlowService:
    return CustomerCategoryFlowService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/categories",
    response_model=ApiResponse[dict],
    summary="List customer-visible categories",
    tags=["Customer Categories"],
)
async def list_customer_categories(
    r: Request,
    search: str | None = Query(None, description="Search by name"),
    category_type: str | None = Query(None, description="Filter by category_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Returns all active, customer-visible categories with their flow metadata.
    Inactive categories and categories with `is_customer_visible=false` are hidden.
    """
    data = await svc.list_customer_categories(
        search=search, category_type=category_type, page=page, page_size=page_size
    )
    return ok(data, _rid(r), "customer_flow")


@router.get(
    "/categories/{category_slug}",
    response_model=ApiResponse[dict],
    summary="Get customer category detail",
    tags=["Customer Categories"],
)
async def get_customer_category(
    category_slug: str,
    r: Request,
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Returns category detail including flow config and available offering count.
    Returns 404 if category is inactive or not customer-visible.
    """
    data = await svc.get_customer_category_detail(category_slug)
    return ok(data, _rid(r), "customer_flow")


@router.get(
    "/categories/{category_slug}/runtime",
    response_model=ApiResponse[dict],
    summary="Get customer category runtime (flow config)",
    tags=["Customer Categories"],
)
async def get_customer_category_runtime(
    category_slug: str,
    r: Request,
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Returns the customer flow runtime for a category — flow type, component key,
    required steps. Frontend uses this to determine which flow shell to render.
    """
    data = await svc.get_customer_category_runtime(category_slug)
    return ok(data, _rid(r), "customer_flow")


# ══════════════════════════════════════════════════════════════════════════════
# OFFERINGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/categories/{category_slug}/offerings",
    response_model=ApiResponse[dict],
    summary="List offerings for a category",
    tags=["Customer Offerings"],
)
async def list_customer_offerings(
    category_slug: str,
    r: Request,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Returns active offerings for the given category.
    Inactive offerings are hidden. Returns 404 if category is not visible.
    """
    data = await svc.list_customer_offerings(
        slug_or_id=category_slug, search=search, page=page, page_size=page_size
    )
    return ok(data, _rid(r), "customer_flow")


@router.get(
    "/categories/{category_slug}/offerings/{offering_slug}",
    response_model=ApiResponse[dict],
    summary="Get customer offering detail",
    tags=["Customer Offerings"],
)
async def get_customer_offering(
    category_slug: str,
    offering_slug: str,
    r: Request,
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Returns offering detail including required fields, flow hints, and price metadata.
    """
    data = await svc.get_customer_offering_detail(category_slug, offering_slug)
    return ok(data, _rid(r), "customer_flow")


# ══════════════════════════════════════════════════════════════════════════════
# FLOW RESOLUTION
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/flow/resolve",
    response_model=ApiResponse[dict],
    summary="Resolve customer flow for a category/offering",
    tags=["Customer Flow Routing"],
)
async def resolve_customer_flow(
    r: Request,
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Resolves the correct frontend flow component for a given category + offering.
    Frontend should call this before rendering any flow shell.

    Request body:
        category_slug (required), offering_slug (optional), city, zipcode
    """
    body = await r.json()
    category_slug = body.get("category_slug", "")
    offering_slug = body.get("offering_slug")
    city = body.get("city")
    zipcode = body.get("zipcode")

    if not category_slug:
        from app.exceptions import ServiceOSException
        raise ServiceOSException(
            "CUSTOMER_LOCATION_REQUIRED", "category_slug is required.", status_code=422
        )

    data = await svc.resolve_flow(
        category_slug=category_slug,
        offering_slug=offering_slug,
        city=city,
        zipcode=zipcode,
    )
    return ok(data, _rid(r), "customer_flow")


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/search",
    response_model=ApiResponse[dict],
    summary="Search categories and offerings",
    tags=["Customer Search"],
)
async def customer_search(
    r: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    category_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: CustomerCategoryFlowService = Depends(_svc),
):
    """
    Searches categories and offerings. Returns only customer-visible results.
    """
    cat_id = uuid.UUID(category_id) if category_id else None
    data = await svc.search(q=q, category_id=cat_id, page=page, page_size=page_size)
    return ok(data, _rid(r), "customer_flow")
