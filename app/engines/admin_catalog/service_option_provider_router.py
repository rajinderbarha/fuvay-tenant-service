"""Sprint 34E — Provider endpoints for service option selection."""
import uuid
from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import UserContext, require_technician
from app.dependencies.db import get_db
from app.engines.admin_catalog.service_option_service import ServiceOptionService
from app.schemas.base import ApiResponse, ok
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/provider/setup/services", tags=["Provider Service Options"])


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_technician)) -> ServiceOptionService:
    tenant_id = uuid.UUID(u.tenant_id) if u.tenant_id else None
    return ServiceOptionService(
        db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, request_id=getattr(r.state, "request_id", "—"),
        tenant_id=tenant_id)


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/{service_id}/available-options", response_model=ApiResponse[list])
async def get_available_options(service_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_technician),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.get_available_options_for_service(service_id), _rid(r))


@router.get("/{service_id}/supported-options", response_model=ApiResponse[list])
async def get_supported_options(service_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_technician),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.get_provider_supported_options(service_id), _rid(r))


@router.post("/{service_id}/supported-options", response_model=ApiResponse[dict])
async def set_supported_options(service_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_technician),
                                 s: ServiceOptionService = Depends(_svc)):
    return ok(await s.set_provider_supported_options(service_id, await r.json()), _rid(r))
