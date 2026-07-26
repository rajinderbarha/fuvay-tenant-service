"""Sprint 34E — Customer-facing service option + issue catalog endpoints."""
import uuid
from fastapi import APIRouter, Depends, Query, Request

from app.dependencies.db import get_db
from app.engines.admin_catalog.service_option_service import ServiceOptionService
from app.schemas.base import ApiResponse, ok
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/customer/catalog", tags=["Customer Service Diagnostics"])


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> ServiceOptionService:
    return ServiceOptionService(
        db=db, actor_id=None, actor_role="customer",
        request_id=getattr(r.state, "request_id", "—"))


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/service-options", response_model=ApiResponse[list])
async def get_customer_service_options(r: Request,
                                        service_id: uuid.UUID | None = Query(None),
                                        category_id: uuid.UUID | None = Query(None),
                                        job_type_id: uuid.UUID | None = Query(None),
                                        tenant_id: uuid.UUID | None = Query(None),
                                        s: ServiceOptionService = Depends(_svc)):
    # job_type_id: only options mapped to this exact Job Type are eligible
    # (no Master-Service-only fallback). tenant_id: once a provider is
    # selected/matched, only options with a resolvable tenant price are
    # returned when they affect the estimate -- customer never sees an
    # option with no real price behind it.
    return ok(await s.get_customer_options(service_id, category_id, job_type_id, tenant_id), _rid(r))


@router.get("/issue-types", response_model=ApiResponse[list])
async def get_customer_issue_types(r: Request,
                                    service_id: uuid.UUID | None = Query(None),
                                    category_id: uuid.UUID | None = Query(None),
                                    s: ServiceOptionService = Depends(_svc)):
    return ok(await s.get_customer_issue_types(service_id, category_id), _rid(r))


@router.post("/service-diagnostics/validate", response_model=ApiResponse[dict])
async def validate_service_diagnostics(r: Request,
                                        s: ServiceOptionService = Depends(_svc)):
    return ok(await s.validate_service_diagnostics(await r.json()), _rid(r))
