"""Admin Catalog Engine — Customer Catalog Read Router (Sprint 34C).
Customers and unauthenticated users browse active master data.
All endpoints are read-only; no write access.
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.admin_catalog.models import ServiceCategory, MasterService
from app.engines.admin_catalog.service import AdminCatalogService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/catalog/master", tags=["Customer Master Catalog"])
ENGINE_ID = "admin_catalog"


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> AdminCatalogService:
    return AdminCatalogService(db=db, request_id=getattr(r.state, "request_id", "—"))


async def _resolve_canonical_flow_flags(db: AsyncSession, service_id: uuid.UUID):
    """Returns (requires_issue, requires_brand, requires_option, requires_schedule,
    requires_location) from the Job-Type Blueprint if `service_id` has EXACTLY
    ONE active job type, else None (ambiguous -- caller falls back to legacy)."""
    from app.engines.admin_catalog.models import (
        MasterServiceJobType, ServiceJobWorkflow, ServiceJobDimension, CatalogDimension,
        ServiceIssueMapping,
    )

    links = (await db.execute(select(MasterServiceJobType).where(
        MasterServiceJobType.master_service_id == service_id,
        MasterServiceJobType.is_active == True))).scalars().all()  # noqa: E712
    if len(links) != 1:
        return None
    job_type_id = links[0].job_type_id

    workflow = (await db.execute(select(ServiceJobWorkflow).where(
        ServiceJobWorkflow.master_service_id == service_id,
        ServiceJobWorkflow.job_type_id == job_type_id))).scalar_one_or_none()

    dim_rows = (await db.execute(
        select(ServiceJobDimension, CatalogDimension)
        .join(CatalogDimension, ServiceJobDimension.dimension_id == CatalogDimension.id)
        .where(ServiceJobDimension.master_service_id == service_id,
               ServiceJobDimension.job_type_id == job_type_id))).all()
    dims = {cd.key: sjd for sjd, cd in dim_rows}

    requires_brand = bool(dims.get("brand") and dims["brand"].enabled and dims["brand"].required)
    requires_option = bool(dims.get("type") and dims["type"].enabled and dims["type"].required)

    issue_count = (await db.execute(select(ServiceIssueMapping.id).where(
        ServiceIssueMapping.master_service_id == service_id,
        ServiceIssueMapping.deleted_at.is_(None)).limit(1))).first()
    requires_issue = issue_count is not None

    requires_schedule = bool(workflow and workflow.schedule_required)
    requires_location = bool(workflow and workflow.address_required)

    return (requires_issue, requires_brand, requires_option, requires_schedule, requires_location)


def _rid(r): return getattr(r.state, "request_id", "—")


def _app_catalog(payload):
    """Remove Instagram-only artwork from public/mobile API responses."""
    if isinstance(payload, dict):
        cleaned = {key: _app_catalog(value) for key, value in payload.items() if key != "image_url"}
        if cleaned.get("logo_url") and not cleaned.get("icon_url"):
            cleaned["icon_url"] = cleaned["logo_url"]
        return cleaned
    if isinstance(payload, list):
        return [_app_catalog(value) for value in payload]
    return payload


@router.get("/categories", response_model=ApiResponse[dict],
            summary="List active service categories (public)")
async def public_list_categories(r: Request, s: AdminCatalogService = Depends(_svc)):
    return ok(_app_catalog(await s.list_categories(is_active=True)), _rid(r), ENGINE_ID)


@router.get("/services", response_model=ApiResponse[dict],
            summary="List active master services for a category (public)")
async def public_list_services(r: Request,
                                category_id: uuid.UUID | None = Query(None),
                                job_type: str | None = Query(None),
                                s: AdminCatalogService = Depends(_svc)):
    return ok(_app_catalog(await s.list_master_services(category_id=category_id, job_type=job_type, is_active=True)), _rid(r), ENGINE_ID)


@router.get("/services/{service_id}", response_model=ApiResponse[dict],
            summary="Get active master service detail (public)")
async def public_get_service(service_id: uuid.UUID, r: Request,
                              s: AdminCatalogService = Depends(_svc)):
    return ok(_app_catalog(await s.get_master_service(service_id)), _rid(r), ENGINE_ID)


@router.get("/brands", response_model=ApiResponse[dict],
            summary="List active brands for a category (public)")
async def public_list_brands(r: Request,
                              category_id: uuid.UUID | None = Query(None),
                              s: AdminCatalogService = Depends(_svc)):
    return ok(_app_catalog(await s.list_brands(category_id=category_id, is_active=True)), _rid(r), ENGINE_ID)


@router.get("/service-types", response_model=ApiResponse[dict],
            summary="List active service types for a category (public)")
async def public_list_service_types(r: Request,
                                     category_id: uuid.UUID | None = Query(None),
                                     s: AdminCatalogService = Depends(_svc)):
    return ok(_app_catalog(await s.list_service_types(category_id=category_id, is_active=True)), _rid(r), ENGINE_ID)


@router.get("/issue-types", response_model=ApiResponse[dict],
            summary="List active issue types for browsing (public)")
async def public_list_issue_types(r: Request,
                                   category_id: uuid.UUID | None = Query(None),
                                   master_service_id: uuid.UUID | None = Query(None),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(_app_catalog(await s.list_issue_types(category_id=category_id,
                                                     master_service_id=master_service_id,
                                                     is_active=True)), _rid(r), ENGINE_ID)


@router.get("/service-options", response_model=ApiResponse[dict],
            summary="List active customer-selectable service options (public)")
async def public_list_service_options(r: Request,
                                       category_id: uuid.UUID | None = Query(None),
                                       master_service_id: uuid.UUID | None = Query(None),
                                       s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_service_options(category_id=category_id,
                                            master_service_id=master_service_id,
                                            is_active=True), _rid(r), ENGINE_ID)


@router.get("/service-groups", response_model=ApiResponse[dict],
            summary="List active service groups for a category (public)")
async def public_list_service_groups(r: Request,
                                      category_id: uuid.UUID | None = Query(None),
                                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_service_groups(category_id=category_id, status="active"), _rid(r), ENGINE_ID)


@router.get("/flow/config", response_model=ApiResponse[dict],
            summary="Get backend-driven customer flow config for a category/service")
async def get_flow_config(r: Request,
                           category_id: uuid.UUID | None = Query(None),
                           service_id: uuid.UUID | None = Query(None),
                           s: AdminCatalogService = Depends(_svc)):
    """Returns the flow configuration the customer app should use for this category/service.

    Ownership correction (migration 160): if `service_id` resolves to
    EXACTLY ONE job type (master_service_job_types), this now resolves
    requires_brand/requires_option/requires_schedule/requires_location from
    the canonical Job-Type Blueprint (service_job_workflow +
    service_job_dimensions) instead of the deprecated ServiceCategory/
    MasterService requires_* flags -- those stop being authoritative the
    moment a canonical blueprint exists for the service. A service with
    zero or multiple job types is ambiguous without a job_type_id param
    this endpoint doesn't yet accept (a separate, larger customer-app
    change), so it falls back to the legacy flags rather than guessing.
    """
    db = s.db
    cat_data: dict | None = None
    svc_data: dict | None = None

    if service_id:
        svc_data = await s.get_master_service(service_id)
        if not cat_data and svc_data.get("category_id"):
            cat_data = await s.get_category(uuid.UUID(svc_data["category_id"]))
    if category_id and not cat_data:
        cat_data = await s.get_category(category_id)

    if not cat_data:
        return ok({
            "flow_type": "service_booking",
            "requires_location": True,
            "requires_schedule": False,
            "requires_brand": False,
            "requires_service_option": False,
            "requires_issue_type": False,
            "steps": ["select_service", "confirm"],
        }, _rid(r), ENGINE_ID)

    # This is a public booking contract, so catalog lifecycle and visibility
    # must fail closed.  Returning a usable step list for a retired/hidden
    # category or service lets a stale deep link start a booking that the
    # provider/catalog engines will reject later.
    if cat_data.get("is_active", True) is False or cat_data.get("is_customer_visible", True) is False:
        return ok({
            "available": False,
            "reason": "CATEGORY_UNAVAILABLE",
            "category_id": cat_data.get("category_id"),
            "service_id": svc_data.get("service_id") if svc_data else None,
            "steps": [],
        }, _rid(r), ENGINE_ID)

    if svc_data and svc_data.get("is_active", True) is False:
        return ok({
            "available": False,
            "reason": "SERVICE_UNAVAILABLE",
            "category_id": cat_data.get("category_id"),
            "service_id": svc_data.get("service_id"),
            "steps": [],
        }, _rid(r), ENGINE_ID)

    canonical = await _resolve_canonical_flow_flags(db, service_id) if service_id else None

    if canonical is not None:
        requires_issue, requires_brand, requires_option, requires_schedule, requires_location = canonical
    elif svc_data:
        requires_issue = svc_data.get("requires_issue_type") or cat_data.get("requires_issue_type", False)
        requires_brand = svc_data.get("is_brand_required") or cat_data.get("requires_brand", False)
        requires_option = svc_data.get("is_type_required") or cat_data.get("requires_service_option", False)
        requires_schedule = svc_data.get("requires_schedule") or cat_data.get("requires_schedule", False)
        requires_location = svc_data.get("requires_address") or cat_data.get("requires_location", True)
    else:
        requires_issue = cat_data.get("requires_issue_type", False)
        requires_brand = cat_data.get("requires_brand", False)
        requires_option = cat_data.get("requires_service_option", False)
        requires_schedule = cat_data.get("requires_schedule", False)
        requires_location = cat_data.get("requires_location", True)

    steps: list[str] = []
    if requires_issue:
        steps.append("select_issue_type")
    if requires_brand:
        steps.append("select_brand")
    if requires_option:
        steps.append("select_option")
    if requires_location:
        steps.append("enter_location")
    if requires_schedule:
        steps.append("select_schedule")
    steps.append("confirm")

    return ok({
        "available": True,
        "category_id": cat_data.get("category_id"),
        "service_id": svc_data.get("service_id") if svc_data else None,
        "flow_type": cat_data.get("customer_flow_type") or "service_booking",
        "finance_model": cat_data.get("finance_model"),
        "requires_location": requires_location,
        "requires_schedule": requires_schedule,
        "requires_brand": requires_brand,
        "requires_service_option": requires_option,
        "requires_issue_type": requires_issue,
        "steps": steps,
    }, _rid(r), ENGINE_ID)
