"""Serviceability Engine — Router.
Customer Addresses · Tenant Service Areas · Admin Service Areas · Serviceability checks.
"""
from __future__ import annotations
import uuid
import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.serviceability.service import ServiceabilityService
from app.engines.serviceability.schemas import (
    AddressCreate, AddressUpdate, ServiceAreaCreate, ServiceAreaUpdate,
    ServiceAreaValidateRequest,
    ServiceMappingCreate, ServiceMappingUpdate, ServiceabilityCheckRequest,
    MatchingTenantsRequest, AvailableServicesRequest, AdminServiceabilityTestRequest,
)
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("serviceability.router")
router = APIRouter(tags=["Serviceability"])
ENGINE_ID = "serviceability"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> ServiceabilityService:
    return ServiceabilityService(
        db=db, request_id=_rid(r),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role,
        actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None,
    )


def _require_role(u: UserContext, *roles: str) -> None:
    if u.role not in roles:
        raise ServiceOSException("PERMISSION_DENIED",
                                  f"Role '{u.role}' cannot perform this action.", status_code=403)


@router.get("/v1/serviceability/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Serviceability Engine", "version": "1.0.0",
            "endpoint_count": 22, "status": "active",
            "capabilities": ["zipcode_matching", "city_matching", "ranked_tenant_matching",
                              "customer_addresses", "booking_preflight", "serviceability_audit"]}


# ══════════════════════════════════════════════════════════════════════════════
# Customer Addresses — /v1/customers/me/addresses
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/v1/customers/me/addresses", tags=["Customer Addresses"],
            summary="List my saved addresses", response_model=ApiResponse[dict])
async def list_my_addresses(r: Request,
                             u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_READ_OWN)),
                             s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_addresses(uuid.UUID(u.user_id)), _rid(r), ENGINE_ID)


@router.post("/v1/customers/me/addresses", tags=["Customer Addresses"],
              summary="Add a new address", status_code=status.HTTP_201_CREATED,
              response_model=ApiResponse[dict])
async def create_my_address(body: AddressCreate, r: Request,
                             u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_CREATE_OWN)),
                             s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    tenant_id = uuid.UUID(u.tenant_id) if u.tenant_id else None
    data = await s.create_address(uuid.UUID(u.user_id), tenant_id, body.model_dump())
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/v1/customers/me/addresses/{address_id}", tags=["Customer Addresses"],
            summary="Get one address", response_model=ApiResponse[dict])
async def get_my_address(address_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_READ_OWN)),
                          s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_address_dict(address_id), _rid(r), ENGINE_ID)


@router.put("/v1/customers/me/addresses/{address_id}", tags=["Customer Addresses"],
            summary="Update an address", response_model=ApiResponse[dict])
async def update_my_address(address_id: uuid.UUID, body: AddressUpdate, r: Request,
                             u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_UPDATE_OWN)),
                             s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    return ok(await s.update_address(address_id, payload), _rid(r), ENGINE_ID)


@router.delete("/v1/customers/me/addresses/{address_id}", tags=["Customer Addresses"],
               summary="Delete (soft) an address", response_model=ApiResponse[dict])
async def delete_my_address(address_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_DELETE_OWN)),
                             s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_address(address_id), _rid(r), ENGINE_ID)


@router.post("/v1/customers/me/addresses/{address_id}/set-default", tags=["Customer Addresses"],
             summary="Set as default address", response_model=ApiResponse[dict])
async def set_default_address(address_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_UPDATE_OWN)),
                               s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.set_default_address(address_id), _rid(r), ENGINE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# Admin / Tenant Owner read access to customer addresses
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/v1/admin/customers/{customer_id}/addresses", tags=["Customer Addresses"],
            summary="[Admin] List a customer's addresses", response_model=ApiResponse[dict])
async def admin_list_customer_addresses(
    customer_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_ADMIN_READ)),
    s: ServiceabilityService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(await s.admin_list_addresses(customer_id), _rid(r), ENGINE_ID)


@router.get("/v1/admin/customers/{customer_id}/addresses/{address_id}", tags=["Customer Addresses"],
            summary="[Admin] Get one of a customer's addresses", response_model=ApiResponse[dict])
async def admin_get_customer_address(
    customer_id: uuid.UUID, address_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.CUSTOMER_ADDRESS_ADMIN_READ)),
    s: ServiceabilityService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(await s.admin_get_address(customer_id, address_id), _rid(r), ENGINE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# Tenant Service Areas — /v1/tenant/service-areas
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/v1/tenant/service-areas", tags=["Tenant Service Areas"],
            summary="List my service areas", response_model=ApiResponse[dict])
async def list_tenant_service_areas(
    r: Request, u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_READ)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_service_areas(uuid.UUID(u.tenant_id)), _rid(r), ENGINE_ID)


@router.post("/v1/tenant/service-areas", tags=["Tenant Service Areas"],
             summary="Create a service area", status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_tenant_service_area(
    body: ServiceAreaCreate, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_CREATE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_service_area(uuid.UUID(u.tenant_id), body.model_dump())
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/v1/tenant/service-areas/limits", tags=["Tenant Service Areas"],
            summary="Get service area plan limits", response_model=ApiResponse[dict])
async def get_tenant_service_area_limits(
    r: Request, u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_READ)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_service_area_limits(uuid.UUID(u.tenant_id)), _rid(r), ENGINE_ID)


@router.post("/v1/tenant/service-areas/validate", tags=["Tenant Service Areas"],
             summary="Validate a candidate service area before saving", response_model=ApiResponse[dict])
async def validate_tenant_service_area(
    body: ServiceAreaValidateRequest, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_CREATE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.validate_service_area(uuid.UUID(u.tenant_id), body.model_dump())
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/v1/tenant/service-areas/{area_id}", tags=["Tenant Service Areas"],
            summary="Get one service area", response_model=ApiResponse[dict])
async def get_tenant_service_area(
    area_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_READ)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_service_area_dict(area_id), _rid(r), ENGINE_ID)


@router.put("/v1/tenant/service-areas/{area_id}", tags=["Tenant Service Areas"],
            summary="Update a service area", response_model=ApiResponse[dict])
async def update_tenant_service_area(
    area_id: uuid.UUID, body: ServiceAreaUpdate, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_UPDATE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    return ok(await s.update_service_area(area_id, payload), _rid(r), ENGINE_ID)


@router.delete("/v1/tenant/service-areas/{area_id}", tags=["Tenant Service Areas"],
               summary="Deactivate a service area", response_model=ApiResponse[dict])
async def delete_tenant_service_area(
    area_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_DELETE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.deactivate_service_area(area_id), _rid(r), ENGINE_ID)


@router.post("/v1/tenant/service-areas/{area_id}/set-primary", tags=["Tenant Service Areas"],
             summary="Set a service area as the primary coverage area", response_model=ApiResponse[dict])
async def set_primary_tenant_service_area(
    area_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_UPDATE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.set_primary_service_area(area_id), _rid(r), ENGINE_ID)


@router.post("/v1/tenant/service-areas/{area_id}/services", tags=["Tenant Service Areas"],
             summary="Add a service mapping to an area", status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def add_service_mapping(
    area_id: uuid.UUID, body: ServiceMappingCreate, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_SERVICE_CREATE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.add_service_mapping(area_id, body.model_dump())
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/v1/tenant/service-areas/{area_id}/services", tags=["Tenant Service Areas"],
            summary="List service mappings for an area", response_model=ApiResponse[dict])
async def list_service_mappings(
    area_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_SERVICE_READ)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_service_mappings(area_id), _rid(r), ENGINE_ID)


@router.put("/v1/tenant/service-areas/{area_id}/services/{mapping_id}", tags=["Tenant Service Areas"],
            summary="Update a service mapping", response_model=ApiResponse[dict])
async def update_service_mapping(
    area_id: uuid.UUID, mapping_id: uuid.UUID, body: ServiceMappingUpdate, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_SERVICE_UPDATE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    return ok(await s.update_service_mapping(area_id, mapping_id, payload), _rid(r), ENGINE_ID)


@router.delete("/v1/tenant/service-areas/{area_id}/services/{mapping_id}", tags=["Tenant Service Areas"],
               summary="Remove a service mapping", response_model=ApiResponse[dict])
async def delete_service_mapping(
    area_id: uuid.UUID, mapping_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.TENANT_SERVICE_AREA_SERVICE_DELETE)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_service_mapping(area_id, mapping_id), _rid(r), ENGINE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# Admin Service Areas — /v1/admin/tenants/{tenant_id}/service-areas
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/v1/admin/tenants/{tenant_id}/service-areas", tags=["Tenant Service Areas"],
            summary="[Super Admin] List a tenant's service areas", response_model=ApiResponse[dict])
async def admin_list_service_areas(
    tenant_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.PLATFORM_ADMIN)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_service_areas(tenant_id), _rid(r), ENGINE_ID)


@router.post("/v1/admin/tenants/{tenant_id}/service-areas", tags=["Tenant Service Areas"],
             summary="[Super Admin] Create a service area for a tenant",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def admin_create_service_area(
    tenant_id: uuid.UUID, body: ServiceAreaCreate, r: Request,
    u: UserContext = Depends(require_permission(P.PLATFORM_ADMIN)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_service_area(tenant_id, body.model_dump())
    return ok(data, _rid(r), ENGINE_ID)


@router.put("/v1/admin/tenants/{tenant_id}/service-areas/{area_id}", tags=["Tenant Service Areas"],
            summary="[Super Admin] Update a tenant's service area", response_model=ApiResponse[dict])
async def admin_update_service_area(
    tenant_id: uuid.UUID, area_id: uuid.UUID, body: ServiceAreaUpdate, r: Request,
    u: UserContext = Depends(require_permission(P.PLATFORM_ADMIN)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    return ok(await s.update_service_area(area_id, payload), _rid(r), ENGINE_ID)


@router.delete("/v1/admin/tenants/{tenant_id}/service-areas/{area_id}", tags=["Tenant Service Areas"],
               summary="[Super Admin] Deactivate a tenant's service area", response_model=ApiResponse[dict])
async def admin_delete_service_area(
    tenant_id: uuid.UUID, area_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.PLATFORM_ADMIN)),
    s: ServiceabilityService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.deactivate_service_area(area_id), _rid(r), ENGINE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# Serviceability checks
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/v1/serviceability/check", tags=["Serviceability"],
             summary="Check if a service is available at an address",
             response_model=ApiResponse[dict])
async def check_serviceability(
    body: ServiceabilityCheckRequest, r: Request,
    u: UserContext = Depends(require_permission(P.SERVICEABILITY_CHECK)),
    s: ServiceabilityService = Depends(_svc),
) -> ApiResponse[dict]:
    customer_id = uuid.UUID(u.user_id) if u.role == "customer" and u.user_id else None
    data = await s.check_serviceability(
        address_id=body.address_id, city=body.city, state=body.state, zipcode=body.zipcode,
        latitude=body.latitude, longitude=body.longitude,
        service_id=body.service_id, job_type=body.job_type, customer_id=customer_id,
    )
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/v1/serviceability/matching-tenants", tags=["Serviceability"],
             summary="Get ranked list of matching tenants for a service+address",
             response_model=ApiResponse[dict])
async def matching_tenants(
    body: MatchingTenantsRequest, r: Request,
    u: UserContext = Depends(require_permission(P.SERVICEABILITY_MATCH)),
    s: ServiceabilityService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await s.get_matching_tenants(
        address_id=body.address_id, city=body.city, state=body.state, zipcode=body.zipcode,
        latitude=body.latitude, longitude=body.longitude,
        service_id=body.service_id, job_type=body.job_type,
    )
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/v1/customer/services/available", tags=["Customer Available Services"],
             summary="Get services available at a customer's location",
             response_model=ApiResponse[dict])
async def available_services(
    body: AvailableServicesRequest, r: Request,
    u: UserContext = Depends(require_permission(P.SERVICEABILITY_AVAILABLE_SERVICES)),
    s: ServiceabilityService = Depends(_svc),
) -> ApiResponse[dict]:
    customer_id = uuid.UUID(u.user_id) if u.role == "customer" and u.user_id else None
    data = await s.get_available_services_for_address(
        address_id=body.address_id, city=body.city, state=body.state, zipcode=body.zipcode,
        latitude=body.latitude, longitude=body.longitude, customer_id=customer_id,
    )
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/v1/admin/serviceability/test", tags=["Admin Serviceability"],
             summary="[Super Admin] Debug serviceability matching for a location",
             response_model=ApiResponse[dict])
async def admin_serviceability_test(
    body: AdminServiceabilityTestRequest, r: Request,
    u: UserContext = Depends(require_permission(P.SERVICEABILITY_ADMIN_TEST)),
    s: ServiceabilityService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await s.admin_serviceability_test(
        city=body.city, state=body.state, zipcode=body.zipcode,
        latitude=body.latitude, longitude=body.longitude,
        service_id=body.service_id, job_type=body.job_type,
    )
    return ok(data, _rid(r), ENGINE_ID)


# NOTE: POST /v1/bookings/preflight was moved to app/engines/booking/router.py in Step 4.
# It now lives in BookingService.run_booking_preflight() for proper domain ownership.
