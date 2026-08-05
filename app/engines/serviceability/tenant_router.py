"""Coverage & Service Areas -- tenant-scoped workspace (Phase 1).

Groups the canonical per-pincode `tenant_service_areas` rows into named
"areas" via (zone_name or city) -- no new CoverageArea table is introduced
in this phase; the existing schema's `zone_name` field is exactly the
tenant-facing grouping label the reference design calls an "area". Real
exact-serviceability resolution is delegated to
`exact_serviceability_service.resolve_exact_serviceability`.
"""
import uuid
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.serviceability.models import (
    TenantServiceArea, TenantServiceAreaService, TenantServiceAreaRequest,
)
from app.engines.admin_catalog.models import TenantService, MasterService
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.engines.home_service_booking.exact_serviceability_service import resolve_exact_serviceability

router = APIRouter(prefix="/v1/tenant/home-services/coverage", tags=["tenant-coverage"])
serviceability_router = APIRouter(prefix="/v1/tenant/home-services/serviceability", tags=["tenant-serviceability"])


def _rid(r: Request | None) -> str:
    return getattr(r.state, "request_id", "—") if r else "—"


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException(error_code="TENANT_SCOPE_VIOLATION",
                                  detail="No tenant context on this session.", status_code=403)
    return user.tenant_id


def _area_key(row: TenantServiceArea) -> str:
    return row.zone_name or row.city


def _status_label(rows: list[TenantServiceArea]) -> str:
    """Published/draft/partial/inactive for a grouped area -- derived from
    the real per-pincode ACTIVE/SUSPENDED/EXPIRED/REVOKED + is_active state,
    never a separately-stored area status."""
    active = [r for r in rows if r.is_active and r.status == "ACTIVE"]
    if not active:
        return "inactive"
    if len(active) < len(rows):
        return "partial"
    return "published"


async def _service_matrix(db: AsyncSession, tenant_id: uuid.UUID, area_ids: list[uuid.UUID]) -> list[dict]:
    published = (await db.execute(
        select(TenantService).where(TenantService.tenant_id == tenant_id, TenantService.setup_status == "published",
                                     TenantService.is_enabled.is_(True))
    )).scalars().all()
    if not published:
        return []
    ms_ids = [p.master_service_id for p in published]
    ms_rows = (await db.execute(select(MasterService).where(MasterService.id.in_(ms_ids)))).scalars().all()
    ms_names = {m.id: m.service_name for m in ms_rows}

    mappings = (await db.execute(
        select(TenantServiceAreaService).where(TenantServiceAreaService.tenant_service_area_id.in_(area_ids))
    )).scalars().all()
    by_service: dict[uuid.UUID, list[TenantServiceAreaService]] = {}
    for m in mappings:
        by_service.setdefault(m.service_id, []).append(m)

    staff = (await db.execute(
        select(ProviderTeamMember).where(ProviderTeamMember.tenant_id == tenant_id,
                                          ProviderTeamMember.status == "active",
                                          ProviderTeamMember.deleted_at.is_(None))
    )).scalars().all()

    rows = []
    for p in published:
        maps = by_service.get(p.master_service_id, [])
        enabled = any(m.is_available and m.status == "ACTIVE" for m in maps)
        eligible = 0
        area_id_strs = {str(a) for a in area_ids}
        for s in staff:
            # supported_offering_ids stores tenant_services.id, not
            # master_services.id -- see exact_serviceability_service.py.
            area_ids_s = [str(a) for a in (s.service_area_ids or [])]
            offering_ids = [str(o) for o in (s.supported_offering_ids or [])]
            if area_ids_s and not (set(area_ids_s) & area_id_strs):
                continue
            if offering_ids and str(p.id) not in offering_ids:
                continue
            eligible += 1
        blockers = []
        if not enabled:
            blockers.append("JOB_TYPE_NOT_ENABLED")
        if eligible == 0:
            blockers.append("NO_ELIGIBLE_TECHNICIAN")
        readiness = "ready" if enabled and eligible > 0 else ("partial" if enabled or eligible > 0 else "blocked")
        rows.append({
            "master_service_id": str(p.master_service_id),
            "master_service_name": ms_names.get(p.master_service_id),
            "offering_published": True,
            "enabled_in_area": enabled,
            "eligible_technicians": eligible,
            "readiness": readiness,
            "blockers": blockers,
            "requires_brand": p.requires_brand,
            "requires_type": p.requires_type,
        })
    return rows


@router.get("")
async def coverage_workspace(
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    all_rows = (await db.execute(
        select(TenantServiceArea).where(TenantServiceArea.tenant_id == tenant_id)
    )).scalars().all()

    groups: dict[str, list[TenantServiceArea]] = {}
    for row in all_rows:
        groups.setdefault(_area_key(row), []).append(row)

    published_services = (await db.execute(
        select(func.count(TenantService.id)).where(
            TenantService.tenant_id == tenant_id, TenantService.setup_status == "published",
            TenantService.is_enabled.is_(True),
        )
    )).scalar_one()
    covered_service_ids = (await db.execute(
        select(TenantServiceAreaService.service_id).where(
            TenantServiceAreaService.tenant_id == tenant_id, TenantServiceAreaService.is_available.is_(True),
            TenantServiceAreaService.status == "ACTIVE",
        ).distinct()
    )).scalars().all()

    technicians_total = (await db.execute(
        select(func.count(ProviderTeamMember.id)).where(
            ProviderTeamMember.tenant_id == tenant_id, ProviderTeamMember.status == "active",
            ProviderTeamMember.deleted_at.is_(None),
        )
    )).scalar_one()

    pending_changes = (await db.execute(
        select(func.count(TenantServiceAreaRequest.id)).where(
            TenantServiceAreaRequest.tenant_id == tenant_id,
            TenantServiceAreaRequest.status.in_(["DRAFT", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUESTED"]),
        )
    )).scalar_one()

    staff_rows = (await db.execute(
        select(ProviderTeamMember).where(ProviderTeamMember.tenant_id == tenant_id,
                                          ProviderTeamMember.status == "active",
                                          ProviderTeamMember.deleted_at.is_(None))
    )).scalars().all()

    areas = []
    coverage_gaps = 0
    for key, rows in groups.items():
        matrix = await _service_matrix(db, tenant_id, [r.id for r in rows])
        gaps = sum(1 for m in matrix if m["readiness"] != "ready")
        coverage_gaps += gaps
        row_ids = {str(row.id) for row in rows}
        technician_count = sum(
            1 for s in staff_rows
            if not (s.service_area_ids or []) or any(str(a) in row_ids for a in (s.service_area_ids or []))
        )
        areas.append({
            "area_key": key,
            "name": key,
            "city": rows[0].city,
            "state": rows[0].state,
            "status": _status_label(rows),
            "service_count": len(matrix),
            "pincode_count": len(rows),
            "technician_count": technician_count,
        })

    return ok({
        "kpis": {
            "active_areas": sum(1 for a in areas if a["status"] in ("published", "partial")),
            "serviceable_pincodes": len([row for row in all_rows if row.is_active and row.status == "ACTIVE"]),
            "published_services_covered": len(covered_service_ids),
            "published_services_total": published_services,
            "technicians_available": technicians_total,
            "coverage_gaps": coverage_gaps,
            "pending_changes": pending_changes,
        },
        "areas": sorted(areas, key=lambda a: a["name"]),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }, _rid(r), "tenant.coverage.workspace")


@router.get("/{area_key}")
async def coverage_area_detail(
    area_key: str,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    all_rows = (await db.execute(
        select(TenantServiceArea).where(TenantServiceArea.tenant_id == tenant_id)
    )).scalars().all()
    rows = [row for row in all_rows if _area_key(row) == area_key]
    if not rows:
        raise ServiceOSException(error_code="COVERAGE_AREA_NOT_FOUND",
                                  detail="No coverage area matches this key for your tenant.", status_code=404)

    matrix = await _service_matrix(db, tenant_id, [row.id for row in rows])
    return ok({
        "area_key": area_key,
        "name": area_key,
        "city": rows[0].city,
        "state": rows[0].state,
        "district": rows[0].district,
        "status": _status_label(rows),
        "pincodes": [{
            "id": str(row.id), "zipcode": row.zipcode, "coverage_type": row.coverage_type,
            "status": row.status, "is_active": row.is_active, "is_primary": row.is_primary,
            "effective_from": row.effective_from.isoformat() if row.effective_from else None,
            "effective_until": row.effective_until.isoformat() if row.effective_until else None,
        } for row in rows],
        "services": matrix,
    }, _rid(r), "tenant.coverage.area_detail")


class ServiceabilityCheckIn(BaseModel):
    pincode: str
    master_service_id: uuid.UUID
    job_type: Optional[str] = None
    brand_id: Optional[uuid.UUID] = None
    service_type_id: Optional[uuid.UUID] = None
    requested_at: Optional[dt.datetime] = None


@serviceability_router.post("/check")
async def check_serviceability(
    body: ServiceabilityCheckIn,
    r: Request = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    result = await resolve_exact_serviceability(
        db, tenant_id=tenant_id, pincode=body.pincode, master_service_id=body.master_service_id,
        job_type=body.job_type, brand_id=body.brand_id, service_type_id=body.service_type_id,
        requested_at=body.requested_at,
    )
    return ok(result, _rid(r), "tenant.serviceability.check")
