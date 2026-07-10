"""Geo Engine — Router (12 endpoints)."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.geo.service import GeoService
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException

logger = structlog.get_logger("geo.router")
router = APIRouter(prefix="/v1/geo", tags=["Geo Engine"])
ENGINE_ID = "geo"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> GeoService:
    return GeoService(db=db, request_id=getattr(r.state,"request_id","—"),
                       actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Geo Engine", "version": "8.0.0",
            "endpoint_count": 12, "status": "active",
            "capabilities": ["service_zones","staff_location","radius_search",
                             "pincode_lookup","coverage_map","redis_geo_index"]}

@router.post("/tenants/{tenant_id}/zones", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_zone(tenant_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                       s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.create_zone(tenant_id, await r.json()), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/zones", response_model=ApiResponse[dict])
async def list_zones(tenant_id: uuid.UUID, r: Request,
                      active_only: bool = Query(True),
                      u: UserContext = Depends(get_current_user),
                      s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_tenant_zones(tenant_id, active_only), _rid(r), ENGINE_ID)

@router.get("/zones/{zone_id}", response_model=ApiResponse[dict])
async def get_zone(zone_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_zone(zone_id), _rid(r), ENGINE_ID)

@router.put("/zones/{zone_id}", response_model=ApiResponse[dict])
async def update_zone(zone_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                       s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_zone(zone_id, await r.json()), _rid(r), ENGINE_ID)

@router.delete("/zones/{zone_id}", response_model=ApiResponse[dict])
async def delete_zone(zone_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                       s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_zone(zone_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/zones/check", response_model=ApiResponse[dict])
async def check_pincode(tenant_id: uuid.UUID, r: Request,
                         pincode: str = Query(...),
                         u: UserContext = Depends(get_current_user),
                         s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.check_pincode_in_zone(tenant_id, pincode), _rid(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/staff/{staff_id}/location", response_model=ApiResponse[dict])
async def update_location(tenant_id: uuid.UUID, staff_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    # A technician can only report their OWN GPS position, never spoof a colleague's.
    if u.role == "staff" and (not u.user_id or uuid.UUID(u.user_id) != staff_id):
        raise ServiceOSException("PERMISSION_DENIED", "Staff can only update their own location.")
    body = await r.json()
    return ok(await s.update_staff_location(staff_id, tenant_id, body["latitude"],
              body["longitude"], body.get("accuracy_m"), body.get("status")), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/staff/{staff_id}/location", response_model=ApiResponse[dict])
async def get_location(tenant_id: uuid.UUID, staff_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_staff_location(staff_id, tenant_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/staff/radius", response_model=ApiResponse[dict])
async def staff_in_radius(tenant_id: uuid.UUID, r: Request,
                           lat: float = Query(...), lng: float = Query(...),
                           radius_km: float = Query(10.0),
                           staff_status: str | None = Query(None),
                           u: UserContext = Depends(get_current_user),
                           s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_staff_in_radius(tenant_id, lat, lng, radius_km, staff_status), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/coverage", response_model=ApiResponse[dict])
async def coverage_map(tenant_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: GeoService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_coverage_map(tenant_id), _rid(r), ENGINE_ID)
