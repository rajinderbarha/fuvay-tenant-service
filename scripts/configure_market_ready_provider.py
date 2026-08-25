"""Configure the single development Home Services provider for the live catalog.

This script is intentionally provider-scoped. Admin catalog scripts own structure;
this script uses the tenant catalog service for provider-owned selections/prices,
then connects the already-approved PIN areas and active technician to every
published offering. It is idempotent and refuses to guess when more than one
non-synthetic provider exists.

Run::

    python scripts/configure_market_ready_provider.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import create_engine
from app.engines.admin_catalog.models import (
    Brand,
    JobTypeDefinition,
    MasterService,
    MasterServiceBrand,
    MasterServiceJobType,
    MasterServiceType,
    ServiceGroup,
    ServiceType,
    TenantService,
)
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.entitlement.service import entitlement_service
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService
from app.engines.tenant_engine.models import Tenant
from app.engines.auth.models import User


TARGET_GROUPS = (
    "ac_services",
    "geyser_services",
    "refrigerator_services",
    "washing_machine_services",
    "chimney_services",
    "ro_services",
)

# Provider-owned market-ready ranges. Admin intentionally stores no service
# amount. Inspection-first services use only visit_fee; fixed services use the
# range for every supported Type and inherit it for every supported Brand.
PRICES = {
    "ac_repair": {"visit_fee": 299},
    "ac_installation": {"range": (1499, 2499)},
    "ac_maintenance": {"range": (499, 899)},
    "ac_gas_refill": {"visit_fee": 299},
    "geyser_repair": {"visit_fee": 249},
    "geyser_installation": {"range": (599, 999)},
    "geyser_maintenance": {"range": (399, 699)},
    "refrigerator_repair": {"visit_fee": 299},
    "refrigerator_maintenance": {"range": (499, 799)},
    "washing_machine_repair": {"visit_fee": 299},
    "washing_machine_installation": {"range": (499, 799)},
    "washing_machine_maintenance": {"range": (499, 899)},
    "chimney_repair": {"visit_fee": 299},
    "chimney_installation": {"range": (899, 1499)},
    "chimney_deep_clean": {"range": (599, 1199)},
    "ro_repair": {"visit_fee": 249},
    "ro_installation": {"range": (499, 899)},
    "ro_maintenance": {"range": (399, 899)},
}


async def _one_real_tenant(db) -> tuple[Tenant, User]:
    rows = (await db.execute(
        select(Tenant, User)
        .join(User, User.tenant_id == Tenant.id)
        .where(
            Tenant.archived_at.is_(None),
            Tenant.terminated_at.is_(None),
            Tenant.status.notin_(("archived", "terminated")),
            User.role == "tenant_owner",
            User.is_active.is_(True),
            ~Tenant.tenant_name.ilike("Login E2E Biz%"),
        )
        .order_by(Tenant.created_at)
    )).all()
    by_tenant: dict[uuid.UUID, tuple[Tenant, User]] = {}
    for tenant, owner in rows:
        by_tenant.setdefault(tenant.id, (tenant, owner))
    if len(by_tenant) != 1:
        raise RuntimeError(
            f"Expected exactly one active non-synthetic provider, found {len(by_tenant)}. "
            "Pass no guesses into market configuration."
        )
    return next(iter(by_tenant.values()))


async def _catalog_rows(db):
    rows = (await db.execute(
        select(MasterService, ServiceGroup, MasterServiceJobType, JobTypeDefinition)
        .join(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
        .join(MasterServiceJobType, and_(
            MasterServiceJobType.master_service_id == MasterService.id,
            MasterServiceJobType.is_active.is_(True),
        ))
        .join(JobTypeDefinition, and_(
            JobTypeDefinition.id == MasterServiceJobType.job_type_id,
            JobTypeDefinition.is_active.is_(True),
        ))
        .where(
            ServiceGroup.slug.in_(TARGET_GROUPS),
            ServiceGroup.status == "active",
            ServiceGroup.deleted_at.is_(None),
            MasterService.slug.in_(tuple(PRICES)),
            MasterService.is_active.is_(True),
            MasterService.deleted_at.is_(None),
        )
        .order_by(ServiceGroup.display_order, MasterService.display_order, MasterService.slug)
    )).all()
    slugs = {master.slug for master, _, _, _ in rows}
    missing = sorted(set(PRICES) - slugs)
    if missing:
        raise RuntimeError(f"Admin catalog is incomplete; missing services: {', '.join(missing)}")
    if len(rows) != len(PRICES):
        raise RuntimeError("A configured master service has multiple active job types; explicit pricing is required.")
    return rows


async def _all_dimensions(db, master_id: uuid.UUID) -> tuple[list[str], list[str]]:
    type_ids = [str(value) for value in (await db.execute(
        select(ServiceType.id)
        .join(MasterServiceType, MasterServiceType.service_type_id == ServiceType.id)
        .where(
            MasterServiceType.master_service_id == master_id,
            MasterServiceType.is_active.is_(True),
            ServiceType.is_active.is_(True),
            ServiceType.deleted_at.is_(None),
        )
        .order_by(ServiceType.display_order, ServiceType.name)
    )).scalars().all()]
    brand_ids = [str(value) for value in (await db.execute(
        select(Brand.id)
        .join(MasterServiceBrand, MasterServiceBrand.brand_id == Brand.id)
        .where(
            MasterServiceBrand.master_service_id == master_id,
            MasterServiceBrand.is_active.is_(True),
            MasterServiceBrand.status == "active",
            Brand.is_active.is_(True),
            Brand.deleted_at.is_(None),
        )
        .order_by(Brand.display_order, Brand.name)
    )).scalars().all()]
    if not type_ids or not brand_ids:
        raise RuntimeError(f"Service {master_id} is missing its admin Type or Brand mapping.")
    return type_ids, brand_ids


async def _ensure_area_mapping(db, area: TenantServiceArea, ts: TenantService) -> None:
    rows = (await db.execute(select(TenantServiceAreaService).where(
        TenantServiceAreaService.tenant_service_area_id == area.id,
        TenantServiceAreaService.service_id == ts.master_service_id,
        TenantServiceAreaService.job_type == ts.job_type,
    ))).scalars().all()
    active = next((row for row in rows if row.is_available), None)
    if active is None:
        active = rows[0] if rows else TenantServiceAreaService(
            tenant_service_area_id=area.id,
            tenant_id=area.tenant_id,
            service_id=ts.master_service_id,
            job_type=ts.job_type,
        )
        if not rows:
            db.add(active)
    active.is_available = True
    active.status = "ACTIVE"
    # Coverage is eligibility, never a second pricing authority.
    active.base_price = None
    active.min_price = None
    active.max_price = None
    for duplicate in rows:
        if duplicate.id != active.id:
            duplicate.is_available = False
            duplicate.status = "REVOKED"


async def _ensure_skills_and_technician(db, *, tenant: Tenant, owner: User,
                                        services: list[TenantService], areas: list[TenantServiceArea]) -> ProviderTeamMember:
    candidates = (await db.execute(
        select(ProviderTeamMember, User)
        .join(User, User.id == ProviderTeamMember.user_id)
        .where(
            ProviderTeamMember.tenant_id == tenant.id,
            ProviderTeamMember.deleted_at.is_(None),
            ProviderTeamMember.member_type == "technician",
            ProviderTeamMember.status == "active",
            User.is_active.is_(True),
        )
        .order_by(ProviderTeamMember.created_at)
    )).all()
    if not candidates:
        raise RuntimeError("No active technician with an active staff-app login exists for this provider.")
    member = next((m for m, _ in candidates if "rajinder" in (m.full_name or "").lower()), candidates[0][0])

    master_by_id = {master.id: (master, group) for master, group in (await db.execute(
        select(MasterService, ServiceGroup)
        .join(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
        .where(MasterService.id.in_([ts.master_service_id for ts in services]))
    )).all()}
    skill_ids: list[str] = []
    skill_names: list[str] = []
    for order, ts in enumerate(services, start=1):
        master, group = master_by_id[ts.master_service_id]
        description = f"Deliver {master.service_name} using the published workflow and completion checklist."
        row = (await db.execute(text("""
            INSERT INTO category_skills
              (category_id, service_group_id, code, name, description, status,
               requires_verification, display_order, created_by_user_id, updated_by_user_id)
            VALUES (:category_id,:group_id,:code,:name,:description,'active',true,:display_order,:actor,:actor)
            ON CONFLICT (category_id, code) DO UPDATE SET
              service_group_id=EXCLUDED.service_group_id,
              name=EXCLUDED.name,
              description=EXCLUDED.description,
              status='active', retired_at=NULL,
              requires_verification=true,
              display_order=EXCLUDED.display_order,
              updated_by_user_id=EXCLUDED.updated_by_user_id,
              updated_at=now()
            RETURNING id::text, name
        """), {
            "category_id": str(master.category_id), "group_id": str(group.id),
            "code": master.slug, "name": master.service_name, "description": description,
            "display_order": order * 10, "actor": str(owner.id),
        })).first()
        skill_ids.append(row.id)
        skill_names.append(row.name)

    offering_ids = [str(ts.id) for ts in services]
    area_ids = [str(area.id) for area in areas]
    member.supported_offering_ids = offering_ids
    member.service_area_ids = area_ids
    member.skills = skill_names
    member.can_receive_assignment = True
    member.availability_state = "available"
    member.max_concurrent_jobs = max(4, int(member.max_concurrent_jobs or 0))

    for skill_id in skill_ids:
        await db.execute(text("""
            INSERT INTO provider_team_member_skills
              (tenant_id, staff_member_id, skill_id, verification_status, assigned_by_user_id)
            VALUES (:tenant_id,:member_id,:skill_id,'verified',:actor)
            ON CONFLICT (staff_member_id, skill_id) DO UPDATE SET
              verification_status='verified', assigned_by_user_id=EXCLUDED.assigned_by_user_id,
              updated_at=now()
        """), {"tenant_id": str(tenant.id), "member_id": str(member.id),
               "skill_id": skill_id, "actor": str(owner.id)})

    # Each technician owns one unit of slot capacity. Copy the provider's
    # recurring hours only when that technician has no schedule of their own.
    has_staff_hours = (await db.execute(text(
        "SELECT 1 FROM provider_availability_rules WHERE tenant_id=:tid "
        "AND scope_type='staff_member' AND scope_id=:mid AND is_active=true LIMIT 1"
    ), {"tid": str(tenant.id), "mid": str(member.id)})).scalar()
    if not has_staff_hours:
        await db.execute(text("""
            INSERT INTO provider_availability_rules
              (tenant_id, scope_type, scope_id, category_id, day_of_week,
               start_time, end_time, slot_duration_minutes, max_bookings_per_slot,
               break_start_time, break_end_time, max_jobs_per_day, timezone,
               emergency_available, is_active)
            SELECT tenant_id, 'staff_member', :member_id, category_id, day_of_week,
                   start_time, end_time, slot_duration_minutes, 1,
                   break_start_time, break_end_time, COALESCE(max_jobs_per_day,4), timezone,
                   emergency_available, is_active
              FROM provider_availability_rules
             WHERE tenant_id=:tenant_id AND scope_type='provider' AND scope_id IS NULL AND is_active=true
        """), {"tenant_id": str(tenant.id), "member_id": str(member.id)})
    return member


async def run() -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        tenant, owner = await _one_real_tenant(db)
        catalog = await _catalog_rows(db)

        await entitlement_service.grant_registration_defaults(
            db, tenant_id=tenant.id, module_key="home_services",
            actor_id=owner.id, actor_role="tenant_owner",
            request_id="market-ready-provider-configuration", commit=False,
        )
        service = TenantCatalogService(
            db, request_id="market-ready-provider-configuration",
            actor_id=owner.id, actor_role="tenant_owner", actor_tenant_id=tenant.id,
        )
        await service.update_home_services_pricing_policy({"consultation_fee": 299}, tenant.id)

        areas = (await db.execute(select(TenantServiceArea).where(
            TenantServiceArea.tenant_id == tenant.id,
            TenantServiceArea.is_active.is_(True),
            TenantServiceArea.status == "ACTIVE",
            TenantServiceArea.coverage_type == "zipcode",
        ).order_by(TenantServiceArea.is_primary.desc(), TenantServiceArea.zipcode))).scalars().all()
        if not areas:
            raise RuntimeError("The provider has no approved active PIN coverage.")

        configured: list[TenantService] = []
        for master, group, mapping, job_type in catalog:
            current = (await db.execute(select(TenantService).where(
                TenantService.tenant_id == tenant.id,
                TenantService.master_service_id == master.id,
                TenantService.job_type_id == job_type.id,
                TenantService.deleted_at.is_(None),
            ))).scalar_one_or_none()
            price = PRICES[master.slug]
            if current is None:
                result = await service.enable_service({
                    "master_service_id": str(master.id),
                    "job_type_id": str(job_type.id),
                    "tenant_visit_fee": price.get("visit_fee"),
                    "tenant_min_price": (price.get("range") or (None, None))[0],
                    "tenant_max_price": (price.get("range") or (None, None))[1],
                    "warranty_days": 5,
                }, tenant.id)
                current = await db.get(TenantService, uuid.UUID(result["tenant_service_id"]))
            else:
                current.is_enabled = True
                current.deleted_at = None
                current.job_type = job_type.key
                current.job_type_id = job_type.id

            current.tenant_base_price = None
            current.tenant_emergency_surcharge = None
            current.warranty_days = 5
            if "visit_fee" in price:
                current.tenant_visit_fee = Decimal(str(price["visit_fee"]))
                current.tenant_min_price = None
                current.tenant_max_price = None
            else:
                low, high = price["range"]
                current.tenant_visit_fee = None
                current.tenant_min_price = Decimal(str(low))
                current.tenant_max_price = Decimal(str(high))
            await db.flush()

            type_ids, brand_ids = await _all_dimensions(db, master.id)
            await service.set_tenant_service_types(current.id, type_ids)
            await service.set_tenant_service_brands(current.id, brand_ids)
            if "range" in price:
                low, high = price["range"]
                for type_id in type_ids:
                    await service.set_type_pricing(current.id, uuid.UUID(type_id), low, high)

            for area in areas:
                await _ensure_area_mapping(db, area, current)
            await db.flush()
            await service.publish_service(current.id)
            configured.append(current)

        member = await _ensure_skills_and_technician(
            db, tenant=tenant, owner=owner, services=configured, areas=areas,
        )
        await db.commit()

        print(f"Provider: {tenant.tenant_name} ({tenant.id})")
        print(f"Owner login: {owner.email} ({owner.id})")
        print(f"Published offerings: {len(configured)}")
        print(f"Approved PINs: {', '.join(str(area.zipcode) for area in areas)}")
        print(f"Assignable technician: {member.full_name} ({member.id})")
        if member.user_id:
            staff_user = await db.get(User, member.user_id)
            if staff_user:
                print(f"Staff login: {staff_user.email} ({staff_user.id})")
        print("Consultation fee: INR 299 (one provider-wide fee)")
        for ts in configured:
            master = next(master for master, _, _, _ in catalog if master.id == ts.master_service_id)
            price = PRICES[master.slug]
            label = f"visit INR {price['visit_fee']}" if "visit_fee" in price else f"INR {price['range'][0]}-{price['range'][1]}"
            print(f"  - {master.service_name}: {label}; warranty {ts.warranty_days} days")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
