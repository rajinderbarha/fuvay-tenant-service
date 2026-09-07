"""Admin Catalog Engine — Tenant Catalog Router.
Tenants enable admin master services into their own active service catalog.
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.schemas.base import ApiResponse, ok

from app.dependencies.setup_sequence import enforce_setup_sequence

router = APIRouter(dependencies=[Depends(enforce_setup_sequence)], prefix="/v1/tenant/catalog", tags=["Tenant Service Catalog"])
ENGINE_ID = "admin_catalog"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> TenantCatalogService:
    return TenantCatalogService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role,
        actor_tenant_id=uuid.UUID(u.tenant_id) if getattr(u, "tenant_id", None) else None,
    )


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/available-services", response_model=ApiResponse[dict],
            summary="List all active admin services (with tenant's enabled status)")
async def list_available_services(r: Request,
                                   tenant_id: uuid.UUID | None = Query(None),
                                   u: UserContext = Depends(get_current_user),
                                   s: TenantCatalogService = Depends(_svc)):
    return ok(await s.list_available_services(tenant_id), _rid(r), ENGINE_ID)


@router.get("/home-services/available-services", response_model=ApiResponse[dict],
            summary="List Home Services-only admin catalog (with tenant's enabled status)",
            tags=["Tenant Home Services Setup"])
async def list_home_services_available_services(r: Request,
                                                  tenant_id: uuid.UUID | None = Query(None),
                                                  u: UserContext = Depends(get_current_user),
                                                  s: TenantCatalogService = Depends(_svc)):
    return ok(await s.list_home_services_available(tenant_id), _rid(r), ENGINE_ID)


@router.get("/services/{master_service_id}/requirements", response_model=ApiResponse[dict],
            summary="Read-only: Problems, Questions and Checklists the platform attached to this service")
async def get_service_requirements(master_service_id: uuid.UUID, r: Request,
                                    tenant_id: uuid.UUID | None = Query(None),
                                    job_type_id: uuid.UUID | None = Query(None),
                                    u: UserContext = Depends(get_current_user),
                                    s: TenantCatalogService = Depends(_svc)):
    """Lets a tenant see what the customer will be asked at booking and what
    the technician must complete on site. Admin-authored and read-only here;
    403s for a service this tenant has not enabled."""
    return ok(await s.get_service_requirements(master_service_id, tenant_id, job_type_id), _rid(r), ENGINE_ID)


@router.get("/home-services/enabled-services", response_model=ApiResponse[dict],
            summary="List tenant's enabled Home Services (setup wizard's Enabled Services list)",
            tags=["Tenant Home Services Setup"])
async def list_home_services_enabled_services(r: Request,
                                               tenant_id: uuid.UUID | None = Query(None),
                                               u: UserContext = Depends(get_current_user),
                                               s: TenantCatalogService = Depends(_svc)):
    return ok(await s.list_home_services_enabled(tenant_id), _rid(r), ENGINE_ID)


@router.get("/home-services/pricing-policy", response_model=ApiResponse[dict],
            summary="Get provider-wide Home Services pricing policy",
            tags=["Tenant Home Services Setup"])
async def get_home_services_pricing_policy(r: Request,
                                            tenant_id: uuid.UUID | None = Query(None),
                                            u: UserContext = Depends(get_current_user),
                                            s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_home_services_pricing_policy(tenant_id), _rid(r), ENGINE_ID)


@router.put("/home-services/pricing-policy", response_model=ApiResponse[dict],
            summary="Set provider-wide Home Services pricing policy",
            tags=["Tenant Home Services Setup"])
async def update_home_services_pricing_policy(r: Request,
                                               tenant_id: uuid.UUID | None = Query(None),
                                               u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                               s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_home_services_pricing_policy(body, tenant_id), _rid(r), ENGINE_ID)


@router.get("/enabled-services", response_model=ApiResponse[dict],
            summary="List tenant's enabled services")
async def list_enabled_services(r: Request,
                                 tenant_id: uuid.UUID | None = Query(None),
                                 u: UserContext = Depends(get_current_user),
                                 s: TenantCatalogService = Depends(_svc)):
    return ok(await s.list_enabled_services(tenant_id), _rid(r), ENGINE_ID)


@router.post("/enable-service", response_model=ApiResponse[dict],
             status_code=status.HTTP_201_CREATED,
             summary="Enable an admin master service for this tenant")
async def enable_service(r: Request,
                          tenant_id: uuid.UUID | None = Query(None),
                          u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                          s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.enable_service(body, tenant_id), _rid(r), ENGINE_ID)


@router.get("/enabled-services/{tenant_service_id}", response_model=ApiResponse[dict],
            summary="Get a tenant enabled service detail")
async def get_enabled_service(tenant_service_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(get_current_user),
                               s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_enabled_service(tenant_service_id), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}", response_model=ApiResponse[dict],
            summary="Update tenant service overrides / display name")
async def update_enabled_service(tenant_service_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                  s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_enabled_service(tenant_service_id, body), _rid(r), ENGINE_ID)


@router.post("/disable-service", response_model=ApiResponse[dict],
             summary="Disable a master service for this tenant")
async def disable_service(r: Request,
                           tenant_id: uuid.UUID | None = Query(None),
                           master_service_id: uuid.UUID | None = Query(None),
                           u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                           s: TenantCatalogService = Depends(_svc)):
    body = await r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    effective_msid = master_service_id or body.get("master_service_id")
    payload = {**body, **({"master_service_id": str(effective_msid)} if effective_msid else {})}
    return ok(await s.disable_service(payload,
                                       tenant_id), _rid(r), ENGINE_ID)


# ── Tenant Service Types ──────────────────────────────────────────────────────

@router.get("/enabled-services/{tenant_service_id}/types", response_model=ApiResponse[dict],
            summary="Get tenant's supported types for service", tags=["Tenant Service Types"])
async def get_tenant_service_types(tenant_service_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(get_current_user),
                                    s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_tenant_service_types(tenant_service_id), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/types", response_model=ApiResponse[dict],
            summary="Set tenant's supported types for service", tags=["Tenant Service Types"])
async def set_tenant_service_types(tenant_service_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                    s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    type_ids = body.get("type_ids", [])
    return ok(await s.set_tenant_service_types(tenant_service_id, type_ids), _rid(r), ENGINE_ID)


# ── Tenant Service Brands ─────────────────────────────────────────────────────

@router.get("/enabled-services/{tenant_service_id}/brands", response_model=ApiResponse[dict],
            summary="Get tenant's supported brands for service", tags=["Tenant Service Brands"])
async def get_tenant_service_brands(tenant_service_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(get_current_user),
                                     s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_tenant_service_brands(tenant_service_id), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/brands", response_model=ApiResponse[dict],
            summary="Set tenant's supported brands for service", tags=["Tenant Service Brands"])
async def set_tenant_service_brands(tenant_service_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                     s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    brand_ids = body.get("brand_ids", [])
    return ok(await s.set_tenant_service_brands(tenant_service_id, brand_ids), _rid(r), ENGINE_ID)


# ── Home Services Service Setup Wizard: type/brand pricing, preview, publish ──

@router.get("/enabled-services/{tenant_service_id}/type-pricing", response_model=ApiResponse[dict],
            summary="Get provider price range + customer preview per selected type", tags=["Tenant Service Setup Pricing"])
async def get_tenant_type_pricing(tenant_service_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(get_current_user),
                                   s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_type_pricing_for_setup(tenant_service_id), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/types/{service_type_id}/pricing", response_model=ApiResponse[dict],
            summary="Set provider price range for one type", tags=["Tenant Service Setup Pricing"])
async def set_tenant_type_pricing(tenant_service_id: uuid.UUID, service_type_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                   s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.set_type_pricing(tenant_service_id, service_type_id,
                                        body.get("tenant_min_price"), body.get("tenant_max_price")),
               _rid(r), ENGINE_ID)


@router.delete("/enabled-services/{tenant_service_id}/types/{service_type_id}/pricing", response_model=ApiResponse[dict],
               summary="Clear provider Type price override", tags=["Tenant Service Setup Pricing"])
async def clear_tenant_type_pricing(tenant_service_id: uuid.UUID, service_type_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                    s: TenantCatalogService = Depends(_svc)):
    return ok(await s.clear_type_pricing(tenant_service_id, service_type_id), _rid(r), ENGINE_ID)


@router.get("/enabled-services/{tenant_service_id}/brand-pricing", response_model=ApiResponse[dict],
            summary="Get provider brand override price range + customer preview", tags=["Tenant Service Setup Pricing"])
async def get_tenant_brand_pricing(tenant_service_id: uuid.UUID, r: Request,
                                    service_type_id: uuid.UUID | None = Query(None),
                                    u: UserContext = Depends(get_current_user),
                                    s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_brand_pricing_for_setup(tenant_service_id, service_type_id), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/brands/{brand_id}/pricing", response_model=ApiResponse[dict],
            summary="Set provider brand override price range", tags=["Tenant Service Setup Pricing"])
async def set_tenant_brand_pricing(tenant_service_id: uuid.UUID, brand_id: uuid.UUID, r: Request,
                                    service_type_id: uuid.UUID | None = Query(None),
                                    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                    s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.set_brand_pricing(tenant_service_id, brand_id,
                                         body.get("tenant_min_price"), body.get("tenant_max_price"),
                                         service_type_id), _rid(r), ENGINE_ID)


@router.delete("/enabled-services/{tenant_service_id}/brands/{brand_id}/pricing", response_model=ApiResponse[dict],
               summary="Clear provider Brand price exception", tags=["Tenant Service Setup Pricing"])
async def clear_tenant_brand_pricing(tenant_service_id: uuid.UUID, brand_id: uuid.UUID, r: Request,
                                     service_type_id: uuid.UUID | None = Query(None),
                                     u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                     s: TenantCatalogService = Depends(_svc)):
    return ok(await s.clear_brand_pricing(tenant_service_id, brand_id, service_type_id), _rid(r), ENGINE_ID)


@router.get("/enabled-services/{tenant_service_id}/resolve-price", response_model=ApiResponse[dict],
            summary="Deterministic tenant price resolution for a type/brand combination "
                    "(exact type+brand > type > brand > tenant default > none)",
            tags=["Tenant Service Setup Pricing"])
async def resolve_tenant_price(tenant_service_id: uuid.UUID, r: Request,
                                service_type_id: uuid.UUID | None = Query(None),
                                brand_id: uuid.UUID | None = Query(None),
                                u: UserContext = Depends(get_current_user),
                                s: TenantCatalogService = Depends(_svc)):
    return ok(await s.resolve_tenant_price(tenant_service_id, service_type_id, brand_id), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/type-coverage-mode", response_model=ApiResponse[dict],
            summary="Set Type coverage mode: all / selected / all_except", tags=["Tenant Service Setup Pricing"])
async def set_type_coverage_mode(tenant_service_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                  s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.set_type_coverage_mode(tenant_service_id, body["mode"]), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/brand-coverage-mode", response_model=ApiResponse[dict],
            summary="Set Brand coverage mode: all / selected / all_except", tags=["Tenant Service Setup Pricing"])
async def set_brand_coverage_mode(tenant_service_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                   s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.set_brand_coverage_mode(tenant_service_id, body["mode"]), _rid(r), ENGINE_ID)


@router.put("/enabled-services/{tenant_service_id}/wizard-step", response_model=ApiResponse[dict],
            summary="Persist the tenant's last-active wizard step (draft resume pointer)",
            tags=["Tenant Service Setup Pricing"])
async def update_last_active_step(tenant_service_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                   s: TenantCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_last_active_step(tenant_service_id, body["step"]), _rid(r), ENGINE_ID)


@router.get("/enabled-services/{tenant_service_id}/validate-for-publish", response_model=ApiResponse[dict],
            summary="Field-level publish validation -- {valid, errors:[{step,job_type_id,dimension_path,code,message}]}",
            tags=["Tenant Service Setup Pricing"])
async def validate_for_publish(tenant_service_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(get_current_user),
                                s: TenantCatalogService = Depends(_svc)):
    return ok(await s.validate_for_publish(tenant_service_id), _rid(r), ENGINE_ID)


@router.get("/enabled-services/{tenant_service_id}/blueprint-update-status", response_model=ApiResponse[dict],
            summary="Whether this tenant's setup was built against an outdated admin blueprint version",
            tags=["Tenant Service Setup Pricing"])
async def get_blueprint_update_status(tenant_service_id: uuid.UUID, r: Request,
                                       u: UserContext = Depends(get_current_user),
                                       s: TenantCatalogService = Depends(_svc)):
    return ok(await s.get_blueprint_update_status(tenant_service_id), _rid(r), ENGINE_ID)


@router.post("/enabled-services/{tenant_service_id}/publish", response_model=ApiResponse[dict],
             summary="Publish a service — validates completeness, requires an active service area", tags=["Tenant Service Setup Pricing"])
async def publish_tenant_service(tenant_service_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                  s: TenantCatalogService = Depends(_svc)):
    return ok(await s.publish_service(tenant_service_id), _rid(r), ENGINE_ID)


@router.post("/enabled-services/{tenant_service_id}/save-draft", response_model=ApiResponse[dict],
             summary="Save current setup progress as a draft", tags=["Tenant Service Setup Pricing"])
async def save_tenant_service_draft(tenant_service_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                                     s: TenantCatalogService = Depends(_svc)):
    return ok(await s.save_draft(tenant_service_id), _rid(r), ENGINE_ID)
