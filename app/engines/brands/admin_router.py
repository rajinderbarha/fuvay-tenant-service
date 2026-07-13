"""Sprint 34D — Admin Brand Management Router.
All write endpoints require require_super_admin.
Read endpoints require any authenticated user.
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.brands.service import BrandService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin", tags=["Admin Brand Management"])


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> BrandService:
    return BrandService(
        db=db,
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role,
        request_id=getattr(r.state, "request_id", "—"),
    )


def _rid(r): return getattr(r.state, "request_id", "—")


# ═══════════════════════════════════════════════════════════
# BRAND CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/brands", response_model=ApiResponse[dict], summary="List brands")
async def list_brands(
    r: Request,
    status: str | None = Query(None),
    is_active: bool | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    is_global: bool | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brands(status=status, is_active=is_active, category_id=category_id,
                                   is_global=is_global, q=q, limit=limit, offset=offset), _rid(r), "brands")


@router.post("/brands", response_model=ApiResponse[dict], summary="Create brand",
             status_code=201)
async def create_brand(
    r: Request,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.create_brand(body), _rid(r), "brands")


@router.get("/brands/{brand_id}", response_model=ApiResponse[dict], summary="Get brand")
async def get_brand(
    r: Request, brand_id: uuid.UUID,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.get_brand(brand_id), _rid(r), "brands")


@router.put("/brands/{brand_id}", response_model=ApiResponse[dict], summary="Update brand")
async def update_brand(
    r: Request, brand_id: uuid.UUID,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.update_brand(brand_id, body), _rid(r), "brands")


@router.post("/brands/{brand_id}/activate", response_model=ApiResponse[dict], summary="Activate brand")
async def activate_brand(
    r: Request, brand_id: uuid.UUID,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.activate_brand(brand_id), _rid(r), "brands")


@router.post("/brands/{brand_id}/deactivate", response_model=ApiResponse[dict], summary="Deactivate brand")
async def deactivate_brand(
    r: Request, brand_id: uuid.UUID,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.deactivate_brand(brand_id), _rid(r), "brands")


@router.post("/brands/{brand_id}/archive", response_model=ApiResponse[dict], summary="Archive brand")
async def archive_brand(
    r: Request, brand_id: uuid.UUID,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.archive_brand(brand_id), _rid(r), "brands")


@router.post("/brands/{brand_id}/merge", response_model=ApiResponse[dict], summary="Merge brand into target")
async def merge_brands(
    r: Request, brand_id: uuid.UUID,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    target_id = uuid.UUID(str(body["target_brand_id"]))
    return ok(await s.merge_brands(brand_id, target_id, body.get("admin_note")), _rid(r), "brands")


@router.post("/brands/{brand_id}/map-categories", response_model=ApiResponse[dict],
             summary="Map brand to categories")
async def map_brand_categories(
    r: Request, brand_id: uuid.UUID,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.map_categories(brand_id, body.get("category_ids") or []), _rid(r), "brands")


@router.get("/brands/{brand_id}/categories", response_model=ApiResponse[dict],
            summary="List brand category mappings")
async def list_brand_categories(
    r: Request, brand_id: uuid.UUID,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brand_categories(brand_id), _rid(r), "brands")


@router.post("/brands/{brand_id}/map-services", response_model=ApiResponse[dict],
             summary="Map brand to master services")
async def map_brand_services(
    r: Request, brand_id: uuid.UUID,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.map_services(brand_id, body.get("service_ids") or []), _rid(r), "brands")


@router.get("/brands/{brand_id}/services", response_model=ApiResponse[dict],
            summary="List brand service mappings")
async def list_brand_services(
    r: Request, brand_id: uuid.UUID,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brand_services(brand_id), _rid(r), "brands")


# ═══════════════════════════════════════════════════════════
# BRAND REQUESTS
# ═══════════════════════════════════════════════════════════

@router.get("/brand-requests", response_model=ApiResponse[dict], summary="List brand requests")
async def list_brand_requests(
    r: Request,
    status: str | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brand_requests(status=status, tenant_id=tenant_id), _rid(r), "brands")


@router.post("/brand-requests/{request_id}/approve", response_model=ApiResponse[dict],
             summary="Approve brand request")
async def approve_brand_request(
    r: Request, request_id: uuid.UUID,
    body: dict = Body(default={}),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.approve_brand_request(request_id, body.get("admin_note")), _rid(r), "brands")


@router.post("/brand-requests/{request_id}/reject", response_model=ApiResponse[dict],
             summary="Reject brand request")
async def reject_brand_request(
    r: Request, request_id: uuid.UUID,
    body: dict = Body(default={}),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.reject_brand_request(request_id, body.get("admin_note")), _rid(r), "brands")


@router.post("/brand-requests/{request_id}/merge", response_model=ApiResponse[dict],
             summary="Mark brand request as matched to existing brand")
async def merge_brand_request(
    r: Request, request_id: uuid.UUID,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    matched_id = uuid.UUID(str(body["matched_brand_id"]))
    return ok(await s.merge_brand_request(request_id, matched_id, body.get("admin_note")), _rid(r), "brands")


# ═══════════════════════════════════════════════════════════
# BRAND TEMPLATES
# ═══════════════════════════════════════════════════════════

@router.get("/brand-templates", response_model=ApiResponse[dict], summary="List brand templates")
async def list_brand_templates(
    r: Request,
    status: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_templates(status=status, category_id=category_id), _rid(r), "brands")


@router.post("/brand-templates", response_model=ApiResponse[dict], summary="Create brand template",
             status_code=201)
async def create_brand_template(
    r: Request,
    body: dict = Body(...),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.create_template(body), _rid(r), "brands")


@router.post("/brand-templates/{template_id}/apply", response_model=ApiResponse[dict],
             summary="Apply brand template to category/services")
async def apply_brand_template(
    r: Request, template_id: uuid.UUID,
    body: dict = Body(default={}),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    cat_id = uuid.UUID(str(body["category_id"])) if body.get("category_id") else None
    svc_ids = body.get("service_ids") or []
    return ok(await s.apply_template(template_id, cat_id, svc_ids), _rid(r), "brands")


# ═══════════════════════════════════════════════════════════
# SEED
# ═══════════════════════════════════════════════════════════

@router.post("/brands/seed", response_model=ApiResponse[dict], summary="Seed 25 starter brands",
             status_code=201)
async def seed_brands(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.seed_starter_brands(), _rid(r), "brands")
