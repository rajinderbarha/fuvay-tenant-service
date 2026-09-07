"""Exact multi-factor serviceability resolver (Coverage & Service Areas Phase 1).

Existing `HomeServiceServiceabilityService.check()` only verifies category +
offering + zipcode/city. This resolver adds the remaining resolution-order
steps the tenant Coverage workspace needs: exact offering publication, tenant
service-area↔service mapping, tenant-scoped type/brand support, eligible
technician cross-reference, and live availability/capacity via the existing
per-technician resolver. No second schedule or coverage table is created;
every step reads canonical rows.

IMPORTANT semantics (confirmed against provider_portal/router.py's
_validate_offering_ids / _validate_type_brand_ids, the only existing writer
of these fields): `ProviderTeamMember.supported_offering_ids` holds
`tenant_services.id` (NOT master_services.id); `supported_type_ids` holds
`tenant_service_types.id`; `supported_brand_ids` holds `tenant_service_brands.id`.
These are per-tenant opt-in rows, not raw catalog IDs -- getting this wrong
silently makes every technician look ineligible for every service.
"""
from __future__ import annotations
import uuid
import datetime as dt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService
from app.engines.admin_catalog.models import TenantService, TenantServiceType, TenantServiceBrand
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.engines.home_service_assignment.availability_resolver import resolve_staff_day

# ── Reason codes (spec section 9) ────────────────────────────────────────────
R_PINCODE_NOT_COVERED       = "PINCODE_NOT_COVERED"
R_COVERAGE_NOT_PUBLISHED    = "COVERAGE_NOT_PUBLISHED"
R_OFFERING_NOT_PUBLISHED    = "OFFERING_NOT_PUBLISHED"
R_JOB_TYPE_NOT_ENABLED      = "JOB_TYPE_NOT_ENABLED"
R_BRAND_NOT_SUPPORTED       = "BRAND_NOT_SUPPORTED"
R_TYPE_NOT_SUPPORTED        = "TYPE_NOT_SUPPORTED"
R_NO_ELIGIBLE_TECHNICIAN    = "NO_ELIGIBLE_TECHNICIAN"
R_AVAILABILITY_NOT_CONFIGURED = "AVAILABILITY_NOT_CONFIGURED"
R_CAPACITY_UNAVAILABLE      = "CAPACITY_UNAVAILABLE"


def _covers(staff: ProviderTeamMember, *, tenant_service_id: str,
            tenant_service_type_id: str | None, tenant_service_brand_id: str | None,
            area_row_ids: set[str]) -> bool:
    area_ids = [str(a) for a in (staff.service_area_ids or [])]
    if area_ids and not (set(area_ids) & area_row_ids):
        return False
    offering_ids = [str(o) for o in (staff.supported_offering_ids or [])]
    if offering_ids and tenant_service_id not in offering_ids:
        return False
    if tenant_service_brand_id:
        brand_ids = [str(b) for b in (staff.supported_brand_ids or [])]
        if brand_ids and tenant_service_brand_id not in brand_ids:
            return False
    if tenant_service_type_id:
        type_ids = [str(t) for t in (staff.supported_type_ids or [])]
        if type_ids and tenant_service_type_id not in type_ids:
            return False
    return True


async def resolve_exact_serviceability(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    pincode: str,
    master_service_id: uuid.UUID,
    job_type: str | None = None,
    job_type_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    service_type_id: uuid.UUID | None = None,
    requested_at: dt.datetime | None = None,
) -> dict:
    requested_at = requested_at or dt.datetime.now(dt.timezone.utc)
    requested_date = requested_at.date()
    reasons: list[str] = []
    result: dict = {
        "serviceable": False,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "reasons": [],
        "coverage_area": None,
        "offering_published": False,
        "job_type_enabled": None,
        "brand_supported": None,
        "type_supported": None,
        "eligible_technician_count": 0,
        "remaining_capacity": 0,
        "next_available_date": None,
    }

    # Step: pincode covered by an ACTIVE tenant service area
    area = (await db.execute(
        select(TenantServiceArea).where(
            TenantServiceArea.tenant_id == tenant_id,
            TenantServiceArea.zipcode == pincode,
            TenantServiceArea.is_active.is_(True),
        )
    )).scalars().first()
    if not area:
        reasons.append(R_PINCODE_NOT_COVERED)
        result["reasons"] = reasons
        return result
    if area.status != "ACTIVE":
        reasons.append(R_COVERAGE_NOT_PUBLISHED)
        result["reasons"] = reasons
        return result
    result["coverage_area"] = {
        "id": str(area.id), "city": area.city, "zone_name": area.zone_name,
        "state": area.state, "zipcode": area.zipcode,
    }

    # Step: tenant offering published
    offering = (await db.execute(
        select(TenantService).where(
            TenantService.tenant_id == tenant_id,
            TenantService.master_service_id == master_service_id,
            *( [TenantService.job_type_id == job_type_id] if job_type_id else [] ),
            *( [TenantService.job_type == job_type] if job_type else [] ),
            TenantService.is_active.is_(True),
            TenantService.is_enabled.is_(True),
            TenantService.setup_status == "published",
        )
    )).scalars().first()
    if not offering:
        reasons.append(R_OFFERING_NOT_PUBLISHED)
        result["reasons"] = reasons
        return result
    result["offering_published"] = True

    # Step: exact job type enabled in this area (tenant_service_area_services)
    if job_type:
        mapping = (await db.execute(
            select(TenantServiceAreaService).where(
                TenantServiceAreaService.tenant_service_area_id == area.id,
                TenantServiceAreaService.service_id == master_service_id,
                TenantServiceAreaService.job_type == job_type,
            )
        )).scalars().first()
        job_type_ok = bool(mapping and mapping.is_available and mapping.status == "ACTIVE")
        result["job_type_enabled"] = job_type_ok
        if not job_type_ok:
            reasons.append(R_JOB_TYPE_NOT_ENABLED)
            result["reasons"] = reasons
            return result

    # Step: tenant-scoped brand support (tenant_service_brands, keyed off THIS
    # tenant's offering row -- not the admin catalog brand list).
    tenant_service_brand_id: str | None = None
    if brand_id:
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        catalog = TenantCatalogService(db, request_id="exact-serviceability")
        supported = await catalog.is_brand_supported(offering, brand_id, service_type_id)
        brand_row = (await db.execute(
            select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == offering.id,
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.service_type_id.is_(None),
                TenantServiceBrand.is_enabled.is_(True),
            )
        )).scalars().first()
        result["brand_supported"] = supported
        if not supported:
            reasons.append(R_BRAND_NOT_SUPPORTED)
            result["reasons"] = reasons
            return result
        # Keep a selected brand context even for All coverage without marker
        # rows, so a technician's explicit restrictions cannot be bypassed.
        tenant_service_brand_id = str(brand_row.id) if brand_row else str(brand_id)

    # Step: tenant-scoped type support (tenant_service_types)
    tenant_service_type_id: str | None = None
    if service_type_id:
        type_row = (await db.execute(
            select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == offering.id,
                TenantServiceType.service_type_id == service_type_id,
                TenantServiceType.is_enabled.is_(True),
            )
        )).scalars().first()
        result["type_supported"] = bool(type_row)
        if not type_row:
            reasons.append(R_TYPE_NOT_SUPPORTED)
            result["reasons"] = reasons
            return result
        tenant_service_type_id = str(type_row.id)

    # Step: eligible technicians -- cross-references service_area_ids +
    # supported_offering_ids/type/brand, which nothing else in the codebase
    # reads today (write-only fields until this resolver).
    staff_rows = (await db.execute(
        select(ProviderTeamMember).where(
            ProviderTeamMember.tenant_id == tenant_id,
            ProviderTeamMember.status == "active",
            ProviderTeamMember.deleted_at.is_(None),
            ProviderTeamMember.can_receive_assignment.is_(True),
        )
    )).scalars().all()

    area_row_ids = {str(area.id)}
    candidates = [
        s for s in staff_rows
        if _covers(s, tenant_service_id=str(offering.id),
                   tenant_service_type_id=tenant_service_type_id,
                   tenant_service_brand_id=tenant_service_brand_id,
                   area_row_ids=area_row_ids)
    ]
    if not candidates:
        reasons.append(R_NO_ELIGIBLE_TECHNICIAN)
        result["reasons"] = reasons
        return result

    # Step: availability + capacity for the requested date, real per-technician
    # resolver (no second schedule) -- also scan forward for next available date.
    eligible_count = 0
    remaining_capacity = 0
    any_availability_configured = False
    for staff in candidates:
        day = await resolve_staff_day(db, tenant_id, staff.id, requested_date)
        if day.get("business_hours") or day.get("working_hours") or day.get("daily_capacity"):
            any_availability_configured = True
        if day["available"]:
            eligible_count += 1
            dc = (day.get("daily_capacity") or {}).get("remaining")
            cc = (day.get("concurrent_capacity") or {}).get("remaining")
            remaining_capacity += min(v for v in (dc, cc) if v is not None) if (dc is not None or cc is not None) else 1

    result["eligible_technician_count"] = eligible_count
    result["remaining_capacity"] = remaining_capacity

    if not any_availability_configured:
        reasons.append(R_AVAILABILITY_NOT_CONFIGURED)
        result["reasons"] = reasons
        return result

    if eligible_count == 0 or remaining_capacity <= 0:
        # Distinguish "no capacity today" from "no coverage at all" (spec
        # section 14) -- scan the next 6 days for the first serviceable slot.
        for offset in range(1, 7):
            probe_date = requested_date + dt.timedelta(days=offset)
            probe_eligible = 0
            for staff in candidates:
                day = await resolve_staff_day(db, tenant_id, staff.id, probe_date)
                if day["available"]:
                    dc = (day.get("daily_capacity") or {}).get("remaining")
                    cc = (day.get("concurrent_capacity") or {}).get("remaining")
                    cap = min(v for v in (dc, cc) if v is not None) if (dc is not None or cc is not None) else 1
                    if cap > 0:
                        probe_eligible += 1
            if probe_eligible > 0:
                result["next_available_date"] = probe_date.isoformat()
                break
        reasons.append(R_CAPACITY_UNAVAILABLE)
        result["reasons"] = reasons
        return result

    result["serviceable"] = True
    result["next_available_date"] = requested_date.isoformat()
    return result
