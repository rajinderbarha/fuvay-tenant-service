"""Serviceability Engine — ServiceabilityService.

Core responsibility: answer "which tenants can serve this customer's address
for this service+job_type" with deterministic, ranked matching:
  zipcode > zone > city > radius
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.serviceability.constants import (
    CoverageType, MatchLevel, MATCH_LEVEL_PRIORITY, JOB_TYPES,
    ERR_ADDRESS_NOT_FOUND, ERR_INVALID_ZIPCODE, ERR_INVALID_CITY,
    ERR_SERVICE_NOT_FOUND, ERR_SERVICE_NOT_ACTIVE, ERR_NOT_AVAILABLE,
    ERR_NO_TENANT, ERR_NO_STAFF, ERR_AREA_NOT_FOUND, ERR_DUPLICATE_AREA,
    ERR_INVALID_COVERAGE, ERR_ZIPCODE_REQUIRED, ERR_CITY_REQUIRED,
    ERR_ZONE_REQUIRED, ERR_RADIUS_REQUIRED, ERR_MAPPING_NOT_FOUND,
    ERR_DUPLICATE_MAPPING, ERR_INVALID_JOB_TYPE, ERR_INVALID_PRICE_RANGE,
    ERR_INVALID_SLA, ERR_LIMIT_REACHED, PINCODE_PREFIX_LOOKUP,
    # Step 3 — request validation
    ERR_CHECK_CITY_REQUIRED, ERR_CHECK_STATE_REQUIRED,
    ERR_SERVICE_ID_REQUIRED, ERR_LOCATION_REQUIRED,
)
from app.engines.serviceability.models import (
    CustomerAddress, TenantServiceArea, TenantServiceAreaService,
    ServiceabilityAuditLog,
)
from app.engines.tenant_engine.models import Tenant, TenantLimits
from app.engines.service_catalog.models import ServiceCatalogItem
from app.engines.auth.models import User
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("serviceability.service")
utcnow = lambda: datetime.now(timezone.utc)


class ServiceabilityService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    # ══════════════════════════════════════════════════════════════════════════
    # Customer Addresses
    # ══════════════════════════════════════════════════════════════════════════

    def _assert_owns_address(self, address: CustomerAddress) -> None:
        if self.actor_role == "customer" and (
            self.actor_id is None or address.customer_id != self.actor_id
        ):
            raise NotFoundException("CustomerAddress", str(address.id))

    async def list_addresses(self, customer_id: uuid.UUID) -> dict:
        rows = (await self.db.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id,
                   CustomerAddress.is_active.is_(True))
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        )).scalars().all()
        return {"addresses": [a.to_dict() for a in rows], "total": len(rows)}

    async def create_address(self, customer_id: uuid.UUID, tenant_id: uuid.UUID | None,
                              payload: dict) -> dict:
        if not payload.get("zipcode"):
            raise ServiceOSException(ERR_INVALID_ZIPCODE, "zipcode is required.", status_code=422)
        if not payload.get("city"):
            raise ServiceOSException(ERR_INVALID_CITY, "city is required.", status_code=422)

        is_default = bool(payload.get("is_default", False))
        if is_default:
            await self._clear_default(customer_id)
        else:
            # First address for a customer is default automatically
            existing = (await self.db.execute(
                select(func.count()).select_from(CustomerAddress)
                .where(CustomerAddress.customer_id == customer_id,
                       CustomerAddress.is_active.is_(True))
            )).scalar_one()
            if existing == 0:
                is_default = True

        addr = CustomerAddress(
            customer_id=customer_id, tenant_id=tenant_id,
            name=payload.get("name"), phone=payload.get("phone"),
            address_line_1=payload["address_line_1"],
            address_line_2=payload.get("address_line_2"),
            landmark=payload.get("landmark"),
            city=payload["city"], district=payload.get("district"),
            state=payload["state"], country=payload.get("country", "India"),
            zipcode=payload["zipcode"],
            latitude=payload.get("latitude"), longitude=payload.get("longitude"),
            is_default=is_default, is_active=True,
        )
        self.db.add(addr)
        await self.db.commit()
        await self.db.refresh(addr)
        logger.info("address.created", customer_id=str(customer_id), address_id=str(addr.id))
        return addr.to_dict()

    async def _clear_default(self, customer_id: uuid.UUID) -> None:
        rows = (await self.db.execute(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default.is_(True),
            )
        )).scalars().all()
        for r in rows:
            r.is_default = False

    async def get_address(self, address_id: uuid.UUID) -> CustomerAddress:
        addr = await self.db.get(CustomerAddress, address_id)
        if not addr or not addr.is_active:
            raise ServiceOSException(ERR_ADDRESS_NOT_FOUND,
                                      f"Address '{address_id}' not found.", status_code=404)
        self._assert_owns_address(addr)
        return addr

    async def get_address_dict(self, address_id: uuid.UUID) -> dict:
        return (await self.get_address(address_id)).to_dict()

    async def update_address(self, address_id: uuid.UUID, payload: dict) -> dict:
        addr = await self.get_address(address_id)
        if payload.get("is_default"):
            await self._clear_default(addr.customer_id)
        for k, v in payload.items():
            if v is not None and hasattr(addr, k):
                setattr(addr, k, v)
        await self.db.commit()
        await self.db.refresh(addr)
        return addr.to_dict()

    async def delete_address(self, address_id: uuid.UUID) -> dict:
        addr = await self.get_address(address_id)
        was_default = addr.is_default
        customer_id = addr.customer_id
        addr.is_active = False
        addr.is_default = False
        await self.db.commit()

        if was_default:
            next_addr = (await self.db.execute(
                select(CustomerAddress)
                .where(CustomerAddress.customer_id == customer_id,
                       CustomerAddress.is_active.is_(True),
                       CustomerAddress.id != address_id)
                .order_by(CustomerAddress.created_at.desc())
            )).scalars().first()
            if next_addr:
                next_addr.is_default = True
                await self.db.commit()

        return {"address_id": str(address_id), "deleted": True}

    async def set_default_address(self, address_id: uuid.UUID) -> dict:
        addr = await self.get_address(address_id)
        await self._clear_default(addr.customer_id)
        addr.is_default = True
        await self.db.commit()
        await self.db.refresh(addr)
        return addr.to_dict()

    # ── Admin / tenant_owner read access to customer addresses ────────────────

    async def _assert_admin_can_view_customer(self, customer_id: uuid.UUID) -> None:
        if self.actor_role == "super_admin":
            return
        if self.actor_role == "tenant_owner":
            if self.actor_tenant_id is None:
                raise NotFoundException("CustomerAddress", str(customer_id))
            from app.engines.booking.models import Booking
            from app.engines.field_ops.models import Job
            has_booking = (await self.db.execute(
                select(func.count()).select_from(Booking).where(
                    Booking.customer_id == customer_id, Booking.tenant_id == self.actor_tenant_id,
                )
            )).scalar_one()
            if has_booking == 0:
                has_job = (await self.db.execute(
                    select(func.count()).select_from(Job).where(
                        Job.customer_id == customer_id, Job.tenant_id == self.actor_tenant_id,
                    )
                )).scalar_one()
                if has_job == 0:
                    raise NotFoundException("CustomerAddress", str(customer_id))
            return
        raise NotFoundException("CustomerAddress", str(customer_id))

    async def admin_list_addresses(self, customer_id: uuid.UUID) -> dict:
        await self._assert_admin_can_view_customer(customer_id)
        rows = (await self.db.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id,
                   CustomerAddress.is_active.is_(True))
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        )).scalars().all()
        return {"addresses": [a.to_dict() for a in rows], "total": len(rows)}

    async def admin_get_address(self, customer_id: uuid.UUID, address_id: uuid.UUID) -> dict:
        await self._assert_admin_can_view_customer(customer_id)
        addr = await self.db.get(CustomerAddress, address_id)
        if not addr or not addr.is_active or addr.customer_id != customer_id:
            raise ServiceOSException(ERR_ADDRESS_NOT_FOUND,
                                      f"Address '{address_id}' not found.", status_code=404)
        return addr.to_dict()

    # ══════════════════════════════════════════════════════════════════════════
    # Tenant Service Areas
    # ══════════════════════════════════════════════════════════════════════════

    def _validate_coverage(self, coverage_type: str, city: str | None, state: str | None,
                            zipcode: str | None, zone_id, zone_name: str | None,
                            latitude, longitude, radius_km) -> None:
        if coverage_type not in CoverageType.ALL:
            raise ServiceOSException(ERR_INVALID_COVERAGE,
                f"coverage_type must be one of {CoverageType.ALL}.", status_code=422)
        if coverage_type == CoverageType.CITY and (not city or not state):
            raise ServiceOSException(ERR_CITY_REQUIRED,
                "city and state are required for city coverage.", status_code=422)
        if coverage_type == CoverageType.ZIPCODE and (not city or not state or not zipcode):
            raise ServiceOSException(ERR_ZIPCODE_REQUIRED,
                "city, state, and zipcode are required for zipcode coverage.", status_code=422)
        if coverage_type == CoverageType.ZONE:
            if not (city or state) or not (zone_id or zone_name):
                raise ServiceOSException(ERR_ZONE_REQUIRED,
                    "city/state and zone_id-or-zone_name are required for zone coverage.",
                    status_code=422)
        if coverage_type == CoverageType.RADIUS:
            if latitude is None or longitude is None or radius_km is None:
                raise ServiceOSException(ERR_RADIUS_REQUIRED,
                    "latitude, longitude, and radius_km are required for radius coverage.",
                    status_code=422)

    def _assert_owns_tenant(self, tenant_id: uuid.UUID) -> None:
        if self.actor_role == "tenant_owner" and (
            self.actor_tenant_id is None or self.actor_tenant_id != tenant_id
        ):
            raise NotFoundException("TenantServiceArea", str(tenant_id))

    async def list_service_areas(self, tenant_id: uuid.UUID) -> dict:
        self._assert_owns_tenant(tenant_id)
        rows = (await self.db.execute(
            select(TenantServiceArea)
            .where(TenantServiceArea.tenant_id == tenant_id, TenantServiceArea.is_active.is_(True))
            .order_by(TenantServiceArea.created_at.desc())
        )).scalars().all()
        out = []
        for area in rows:
            d = area.to_dict()
            count = (await self.db.execute(
                select(func.count()).select_from(TenantServiceAreaService)
                .where(TenantServiceAreaService.tenant_service_area_id == area.id,
                       TenantServiceAreaService.is_available.is_(True))
            )).scalar_one()
            d["service_count"] = count
            out.append(d)
        return {"areas": out, "total": len(out)}

    async def _check_duplicate_area(self, tenant_id: uuid.UUID, coverage_type: str,
                                     city: str | None, zipcode: str | None,
                                     zone_id, zone_name: str | None,
                                     exclude_id: uuid.UUID | None = None) -> None:
        conditions = [
            TenantServiceArea.tenant_id == tenant_id,
            TenantServiceArea.coverage_type == coverage_type,
            TenantServiceArea.is_active.is_(True),
        ]
        if coverage_type == CoverageType.ZONE:
            zone_conditions = []
            if zone_id:
                zone_conditions.append(TenantServiceArea.zone_id == zone_id)
            if zone_name:
                zone_conditions.append(func.lower(TenantServiceArea.zone_name) == zone_name.lower())
            conditions.append(or_(*zone_conditions))
        else:
            conditions.append(func.lower(TenantServiceArea.city) == city.lower())
            conditions.append(TenantServiceArea.zipcode == zipcode)
        if exclude_id is not None:
            conditions.append(TenantServiceArea.id != exclude_id)

        dup = (await self.db.execute(
            select(TenantServiceArea).where(*conditions)
        )).scalar_one_or_none()
        if dup:
            raise ServiceOSException(ERR_DUPLICATE_AREA,
                "An active service area with this coverage already exists.", status_code=409)

    async def create_service_area(self, tenant_id: uuid.UUID, payload: dict) -> dict:
        self._assert_owns_tenant(tenant_id)
        coverage_type = payload["coverage_type"]
        city = payload.get("city")
        zipcode = payload.get("zipcode")
        zone_id = uuid.UUID(payload["zone_id"]) if payload.get("zone_id") else None
        zone_name = payload.get("zone_name")
        self._validate_coverage(coverage_type, city, payload.get("state"), zipcode,
                                 zone_id, zone_name, payload.get("latitude"),
                                 payload.get("longitude"), payload.get("radius_km"))

        if coverage_type == CoverageType.CITY:
            zipcode = None

        await self._check_duplicate_area(tenant_id, coverage_type, city, zipcode, zone_id, zone_name)

        limits = await self.get_service_area_limits(tenant_id)
        if limits["remaining_service_areas"] <= 0:
            raise ServiceOSException(ERR_LIMIT_REACHED,
                f"Your plan allows a maximum of {limits['max_service_areas']} service areas.",
                status_code=422, context={"max_service_areas": limits["max_service_areas"]})

        make_primary = bool(payload.get("is_primary", False))
        if make_primary:
            others = (await self.db.execute(
                select(TenantServiceArea).where(
                    TenantServiceArea.tenant_id == tenant_id,
                    TenantServiceArea.is_primary.is_(True),
                )
            )).scalars().all()
            for other in others:
                other.is_primary = False

        area = TenantServiceArea(
            tenant_id=tenant_id, coverage_type=coverage_type,
            country=payload.get("country", "India"), state=payload["state"],
            district=payload.get("district"), city=city, zipcode=zipcode,
            zone_id=zone_id, zone_name=zone_name,
            latitude=payload.get("latitude"), longitude=payload.get("longitude"),
            radius_km=payload.get("radius_km"), priority=payload.get("priority", 100),
            is_active=payload.get("is_active", True), is_primary=make_primary,
        )
        self.db.add(area)
        await self.db.commit()
        await self.db.refresh(area)
        logger.info("service_area.created", tenant_id=str(tenant_id), area_id=str(area.id))
        return area.to_dict()

    async def get_service_area(self, area_id: uuid.UUID) -> TenantServiceArea:
        area = await self.db.get(TenantServiceArea, area_id)
        if not area or not area.is_active:
            raise ServiceOSException(ERR_AREA_NOT_FOUND,
                                      f"Service area '{area_id}' not found.", status_code=404)
        self._assert_owns_tenant(area.tenant_id)
        return area

    async def get_service_area_dict(self, area_id: uuid.UUID) -> dict:
        return (await self.get_service_area(area_id)).to_dict()

    async def update_service_area(self, area_id: uuid.UUID, payload: dict) -> dict:
        area = await self.get_service_area(area_id)
        coverage_type = payload.get("coverage_type", area.coverage_type)
        city = payload.get("city", area.city)
        state = payload.get("state", area.state)
        zipcode = payload.get("zipcode", area.zipcode)
        zone_id = (uuid.UUID(payload["zone_id"]) if payload.get("zone_id")
                   else (None if "zone_id" in payload else area.zone_id))
        zone_name = payload.get("zone_name", area.zone_name)
        latitude = payload.get("latitude", area.latitude)
        longitude = payload.get("longitude", area.longitude)
        radius_km = payload.get("radius_km", area.radius_km)
        changed_coverage = any(k in payload for k in
            ("coverage_type", "city", "state", "zipcode", "zone_id", "zone_name",
             "latitude", "longitude", "radius_km"))
        if changed_coverage:
            self._validate_coverage(coverage_type, city, state, zipcode, zone_id,
                                     zone_name, latitude, longitude, radius_km)
            if coverage_type == CoverageType.CITY:
                zipcode = None
                payload["zipcode"] = None
            await self._check_duplicate_area(area.tenant_id, coverage_type, city, zipcode,
                                              zone_id, zone_name, exclude_id=area.id)
        if "zone_id" in payload:
            payload["zone_id"] = zone_id
        if payload.get("is_primary") is True:
            others = (await self.db.execute(
                select(TenantServiceArea).where(
                    TenantServiceArea.tenant_id == area.tenant_id,
                    TenantServiceArea.is_primary.is_(True),
                    TenantServiceArea.id != area.id,
                )
            )).scalars().all()
            for other in others:
                other.is_primary = False
        for k, v in payload.items():
            if v is not None and hasattr(area, k):
                setattr(area, k, v)
        await self.db.commit()
        await self.db.refresh(area)
        return area.to_dict()

    async def deactivate_service_area(self, area_id: uuid.UUID) -> dict:
        area = await self.get_service_area(area_id)
        area.is_active = False
        mappings = (await self.db.execute(
            select(TenantServiceAreaService).where(
                TenantServiceAreaService.tenant_service_area_id == area.id,
                TenantServiceAreaService.is_available.is_(True),
            )
        )).scalars().all()
        for m in mappings:
            m.is_available = False
        await self.db.commit()
        return {"area_id": str(area_id), "deactivated": True}

    # ── Coverage console: limits, primary, validation preview ──────────────────

    async def get_service_area_limits(self, tenant_id: uuid.UUID) -> dict:
        self._assert_owns_tenant(tenant_id)
        limits = (await self.db.execute(
            select(TenantLimits).where(TenantLimits.tenant_id == tenant_id)
        )).scalar_one_or_none()
        max_areas = limits.max_service_areas if limits else 5
        used = (await self.db.execute(
            select(func.count()).select_from(TenantServiceArea)
            .where(TenantServiceArea.tenant_id == tenant_id, TenantServiceArea.is_active.is_(True))
        )).scalar_one()
        return {
            "max_service_areas": max_areas,
            "used_service_areas": used,
            "remaining_service_areas": max(max_areas - used, 0),
        }

    async def set_primary_service_area(self, area_id: uuid.UUID) -> dict:
        area = await self.get_service_area(area_id)
        if not area.is_active:
            raise ServiceOSException(ERR_AREA_NOT_FOUND,
                "Only an active service area can be set as primary.", status_code=422)
        others = (await self.db.execute(
            select(TenantServiceArea).where(
                TenantServiceArea.tenant_id == area.tenant_id,
                TenantServiceArea.is_primary.is_(True),
                TenantServiceArea.id != area.id,
            )
        )).scalars().all()
        for other in others:
            other.is_primary = False
        area.is_primary = True
        await self.db.commit()
        await self.db.refresh(area)
        logger.info("service_area.set_primary", tenant_id=str(area.tenant_id), area_id=str(area.id))
        return area.to_dict()

    async def validate_service_area(self, tenant_id: uuid.UUID, payload: dict) -> dict:
        self._assert_owns_tenant(tenant_id)
        coverage_type = payload.get("coverage_type", CoverageType.ZIPCODE)
        city = payload.get("city")
        state = payload.get("state")
        district = payload.get("district")
        zipcode = payload.get("zipcode")
        zone_id = uuid.UUID(payload["zone_id"]) if payload.get("zone_id") else None
        zone_name = payload.get("zone_name")

        resolved_tier = "tier_2"
        resolved_city, resolved_district, resolved_state = city, district, state
        if zipcode:
            prefix = str(zipcode)[:3]
            match = PINCODE_PREFIX_LOOKUP.get(prefix)
            if match:
                resolved_city = match["city"]
                resolved_district = match["district"]
                resolved_state = match["state"]
                resolved_tier = match["tier"]

        coverage_valid = True
        coverage_error = None
        try:
            self._validate_coverage(coverage_type, resolved_city or city, resolved_state or state,
                                     zipcode, zone_id, zone_name,
                                     payload.get("latitude"), payload.get("longitude"),
                                     payload.get("radius_km"))
        except ServiceOSException as exc:
            coverage_valid = False
            coverage_error = exc.detail

        is_duplicate = False
        if coverage_valid:
            try:
                await self._check_duplicate_area(
                    tenant_id, coverage_type, resolved_city or city, zipcode, zone_id, zone_name,
                )
            except ServiceOSException:
                is_duplicate = True

        limits = await self.get_service_area_limits(tenant_id)
        package_limit_ok = limits["remaining_service_areas"] > 0

        serviceable = coverage_valid and not is_duplicate and package_limit_ok
        return {
            "resolved_city": resolved_city,
            "resolved_district": resolved_district,
            "resolved_state": resolved_state,
            "resolved_zone_tier": resolved_tier,
            "coverage_valid": coverage_valid,
            "coverage_error": coverage_error,
            "is_duplicate": is_duplicate,
            "package_limit_ok": package_limit_ok,
            "max_service_areas": limits["max_service_areas"],
            "remaining_service_areas": limits["remaining_service_areas"],
            "serviceable": serviceable,
            "bookability_impact": (
                "This area can receive Home Services bookings."
                if serviceable else
                "This area cannot be added yet — resolve the issue above before saving."
            ),
        }

    # ── Service mappings ──────────────────────────────────────────────────────

    def _validate_mapping_fields(self, job_type: str | None, sla_minutes, base_price,
                                  min_price, max_price) -> None:
        if job_type is not None and job_type not in JOB_TYPES:
            raise ServiceOSException(ERR_INVALID_JOB_TYPE,
                f"job_type must be one of {JOB_TYPES}.", status_code=422)
        if sla_minutes is not None and sla_minutes <= 0:
            raise ServiceOSException(ERR_INVALID_SLA,
                "sla_minutes must be a positive integer.", status_code=422)
        for label, price in (("base_price", base_price), ("min_price", min_price),
                              ("max_price", max_price)):
            if price is not None and price < 0:
                raise ServiceOSException(ERR_INVALID_PRICE_RANGE,
                    f"{label} cannot be negative.", status_code=422)
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ServiceOSException(ERR_INVALID_PRICE_RANGE,
                "min_price cannot be greater than max_price.", status_code=422)

    async def _assert_service_active(self, service_id: uuid.UUID) -> None:
        service = await self.db.get(ServiceCatalogItem, service_id)
        if not service:
            raise ServiceOSException(ERR_SERVICE_NOT_FOUND,
                f"Service '{service_id}' not found.", status_code=404)
        if not service.is_active:
            raise ServiceOSException(ERR_SERVICE_NOT_ACTIVE,
                f"Service '{service_id}' is not active.", status_code=422)

    async def add_service_mapping(self, area_id: uuid.UUID, payload: dict) -> dict:
        area = await self.get_service_area(area_id)
        service_id = uuid.UUID(payload["service_id"])
        job_type = payload["job_type"]
        sla_minutes = payload.get("sla_minutes")
        base_price = payload.get("base_price")
        min_price = payload.get("min_price")
        max_price = payload.get("max_price")
        self._validate_mapping_fields(job_type, sla_minutes, base_price, min_price, max_price)
        await self._assert_service_active(service_id)

        dup = (await self.db.execute(
            select(TenantServiceAreaService).where(
                TenantServiceAreaService.tenant_service_area_id == area.id,
                TenantServiceAreaService.service_id == service_id,
                TenantServiceAreaService.job_type == job_type,
                TenantServiceAreaService.is_available.is_(True),
            )
        )).scalar_one_or_none()
        if dup:
            raise ServiceOSException(ERR_DUPLICATE_MAPPING,
                "An active mapping for this service and job_type already exists in this area.",
                status_code=409)

        mapping = TenantServiceAreaService(
            tenant_service_area_id=area.id, tenant_id=area.tenant_id,
            service_id=service_id, job_type=job_type,
            is_available=payload.get("is_available", True),
            sla_minutes=sla_minutes,
            base_price=base_price, min_price=min_price, max_price=max_price,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping.to_dict()

    async def list_service_mappings(self, area_id: uuid.UUID) -> dict:
        area = await self.get_service_area(area_id)
        rows = (await self.db.execute(
            select(TenantServiceAreaService)
            .where(TenantServiceAreaService.tenant_service_area_id == area.id)
            .order_by(TenantServiceAreaService.created_at.desc())
        )).scalars().all()
        return {"mappings": [m.to_dict() for m in rows], "total": len(rows)}

    async def _get_mapping(self, area_id: uuid.UUID, mapping_id: uuid.UUID) -> TenantServiceAreaService:
        area = await self.get_service_area(area_id)
        mapping = await self.db.get(TenantServiceAreaService, mapping_id)
        if not mapping or mapping.tenant_service_area_id != area.id:
            raise ServiceOSException(ERR_MAPPING_NOT_FOUND,
                                      f"Service mapping '{mapping_id}' not found.", status_code=404)
        return mapping

    async def update_service_mapping(self, area_id: uuid.UUID, mapping_id: uuid.UUID,
                                      payload: dict) -> dict:
        mapping = await self._get_mapping(area_id, mapping_id)
        job_type = payload.get("job_type", mapping.job_type)
        sla_minutes = payload.get("sla_minutes", mapping.sla_minutes)
        base_price = payload.get("base_price", mapping.base_price)
        min_price = payload.get("min_price", mapping.min_price)
        max_price = payload.get("max_price", mapping.max_price)
        self._validate_mapping_fields(job_type, sla_minutes, base_price, min_price, max_price)
        for k, v in payload.items():
            if v is not None and hasattr(mapping, k):
                setattr(mapping, k, v)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping.to_dict()

    async def delete_service_mapping(self, area_id: uuid.UUID, mapping_id: uuid.UUID) -> dict:
        mapping = await self._get_mapping(area_id, mapping_id)
        mapping.is_available = False
        await self.db.commit()
        return {"mapping_id": str(mapping_id), "deleted": True}

    # ══════════════════════════════════════════════════════════════════════════
    # Matching engine (Step 3)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _norm(s: str | None) -> str:
        return (s or "").strip().lower()

    @staticmethod
    def _strip_zip(s: str | None) -> str:
        return (s or "").strip()

    @staticmethod
    def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        import math
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))

    async def _resolve_service_type_id(self, service_id: str) -> tuple[str, str, str]:
        """Resolve catalog item UUID → (service_type_id, service_name, category)."""
        try:
            svc_uuid = uuid.UUID(service_id)
        except (ValueError, AttributeError):
            raise ServiceOSException(ERR_SERVICE_NOT_FOUND,
                f"Invalid service_id format: '{service_id}'.", status_code=404)
        item = await self.db.get(ServiceCatalogItem, svc_uuid)
        if not item:
            raise ServiceOSException(ERR_SERVICE_NOT_FOUND,
                f"Service '{service_id}' not found.", status_code=404)
        if not item.is_active:
            raise ServiceOSException(ERR_SERVICE_NOT_ACTIVE,
                f"Service '{service_id}' is not active.", status_code=422)
        return item.service_type_id, item.name, item.category

    def _validate_check_request(
        self, address_id: str | None, city: str | None, state: str | None,
        zipcode: str | None, service_id: str | None, job_type: str | None,
    ) -> None:
        if not service_id:
            raise ServiceOSException(ERR_SERVICE_ID_REQUIRED,
                "service_id is required.", status_code=422)
        if not job_type:
            raise ServiceOSException(ERR_INVALID_JOB_TYPE,
                "job_type is required.", status_code=422)
        if job_type not in JOB_TYPES:
            raise ServiceOSException(ERR_INVALID_JOB_TYPE,
                f"job_type must be one of {JOB_TYPES}.", status_code=422)
        if not address_id:
            if not city:
                raise ServiceOSException(ERR_CHECK_CITY_REQUIRED,
                    "city is required when address_id is not provided.", status_code=422)
            if not state:
                raise ServiceOSException(ERR_CHECK_STATE_REQUIRED,
                    "state is required when address_id is not provided.", status_code=422)

    async def _resolve_location_full(
        self, address_id: str | None, city: str | None, state: str | None,
        zipcode: str | None, latitude: float | None, longitude: float | None,
    ) -> tuple[str, str | None, str | None, float | None, float | None, uuid.UUID | None]:
        """Returns (city, state, zipcode, latitude, longitude, address_uuid)."""
        if address_id:
            addr = await self.get_address(uuid.UUID(address_id))
            return addr.city, addr.state, addr.zipcode, addr.latitude, addr.longitude, addr.id
        return city, state, zipcode, latitude, longitude, None

    async def match_tenants_for_location(
        self,
        city: str, state: str | None, zipcode: str | None,
        latitude: float | None, longitude: float | None,
        service_type_id: str, job_type: str,
        filter_tenant_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Core matching engine. Returns deterministically ranked tenant list."""
        from app.engines.geo.models import ServiceZone
        from app.engines.review.models import ReviewAggregate

        norm_city = self._norm(city)
        strip_zip = self._strip_zip(zipcode) if zipcode else None

        # ── 1. Fetch all candidate rows ──────────────────────────────────────
        base_where: list = [
            Tenant.status == "active",
            TenantServiceArea.is_active.is_(True),
            TenantServiceAreaService.is_available.is_(True),
            ServiceCatalogItem.service_type_id == service_type_id,
            TenantServiceAreaService.job_type == job_type,
        ]
        if filter_tenant_id is not None:
            base_where.append(Tenant.id == filter_tenant_id)

        stmt = (
            select(
                Tenant.id.label("tenant_id"),
                Tenant.tenant_name.label("tenant_name"),
                Tenant.health_score.label("health_score"),
                TenantServiceArea.id.label("area_id"),
                TenantServiceArea.coverage_type.label("coverage_type"),
                TenantServiceArea.city.label("area_city"),
                TenantServiceArea.zipcode.label("area_zipcode"),
                TenantServiceArea.zone_id.label("zone_id"),
                TenantServiceArea.latitude.label("area_lat"),
                TenantServiceArea.longitude.label("area_lng"),
                TenantServiceArea.radius_km.label("radius_km"),
                TenantServiceAreaService.id.label("mapping_id"),
                TenantServiceAreaService.sla_minutes.label("sla_minutes"),
                TenantServiceAreaService.base_price.label("base_price"),
                TenantServiceAreaService.min_price.label("min_price"),
                TenantServiceAreaService.max_price.label("max_price"),
                ServiceCatalogItem.name.label("service_name"),
                ServiceCatalogItem.category.label("category"),
            )
            .join(TenantServiceArea, TenantServiceArea.tenant_id == Tenant.id)
            .join(TenantServiceAreaService,
                  TenantServiceAreaService.tenant_service_area_id == TenantServiceArea.id)
            .join(ServiceCatalogItem,
                  ServiceCatalogItem.id == TenantServiceAreaService.service_id)
            .where(*base_where)
        )
        rows = (await self.db.execute(stmt)).all()

        # ── 2. Batch-load ServiceZones for zone-type areas ───────────────────
        zone_ids = {row.zone_id for row in rows
                    if row.coverage_type == CoverageType.ZONE and row.zone_id}
        zone_map: dict = {}
        if zone_ids:
            sz_rows = (await self.db.execute(
                select(ServiceZone).where(ServiceZone.id.in_(zone_ids),
                                          ServiceZone.is_active.is_(True))
            )).scalars().all()
            zone_map = {z.id: z for z in sz_rows}

        # ── 3. Filter and classify by location ───────────────────────────────
        matches_by_tenant: dict[str, dict] = {}

        for row in rows:
            ct = row.coverage_type
            match_level: str | None = None
            distance_km: float | None = None
            match_reason = ""

            if ct == CoverageType.CITY:
                if self._norm(row.area_city) == norm_city:
                    match_level = MatchLevel.CITY
                    match_reason = f"city: {row.area_city}"

            elif ct == CoverageType.ZIPCODE:
                if (self._norm(row.area_city) == norm_city and strip_zip and
                        self._strip_zip(row.area_zipcode) == strip_zip):
                    match_level = MatchLevel.ZIPCODE
                    match_reason = f"zipcode: {row.area_zipcode}"

            elif ct == CoverageType.ZONE and row.zone_id and row.zone_id in zone_map:
                zone = zone_map[row.zone_id]
                ids = zone.identifiers or []
                if zone.zone_type == "pincode" and strip_zip:
                    if strip_zip in [self._strip_zip(i) for i in ids]:
                        match_level = MatchLevel.ZONE
                        match_reason = f"zone: {zone.zone_name} (pincode)"
                elif zone.zone_type == "area_name":
                    if norm_city in [self._norm(i) for i in ids]:
                        match_level = MatchLevel.ZONE
                        match_reason = f"zone: {zone.zone_name} (area_name)"

            elif ct == CoverageType.RADIUS:
                if (latitude is not None and longitude is not None and
                        row.area_lat is not None and row.area_lng is not None):
                    distance_km = self._haversine_km(
                        latitude, longitude, row.area_lat, row.area_lng)
                    if row.radius_km is not None and distance_km <= row.radius_km:
                        match_level = MatchLevel.RADIUS
                        match_reason = f"radius: {row.radius_km}km from center"

            if match_level is None:
                continue

            tid = str(row.tenant_id)
            rank = MATCH_LEVEL_PRIORITY[match_level]
            candidate = {
                "tenant_id": tid,
                "tenant_name": row.tenant_name,
                "coverage_match_level": match_level,
                "coverage_rank": rank,
                "matched_area_id": str(row.area_id),
                "service_area_service_id": str(row.mapping_id),
                "health_score": float(row.health_score) if row.health_score is not None else None,
                "rating": None,
                "staff_capacity": 0,
                "estimated_sla_minutes": row.sla_minutes,
                "base_price": float(row.base_price) if row.base_price is not None else None,
                "min_price": float(row.min_price) if row.min_price is not None else None,
                "max_price": float(row.max_price) if row.max_price is not None else None,
                "distance_km": round(distance_km, 3) if distance_km is not None else None,
                "match_reason": match_reason,
            }
            existing = matches_by_tenant.get(tid)
            if existing is None or rank < existing["coverage_rank"]:
                matches_by_tenant[tid] = candidate

        if not matches_by_tenant:
            return []

        # ── 4. Batch enrich: rating + staff_capacity ─────────────────────────
        tenant_ids_str = list(matches_by_tenant.keys())
        tenant_uuids = [uuid.UUID(t) for t in tenant_ids_str]

        agg_rows = (await self.db.execute(
            select(ReviewAggregate.entity_id, ReviewAggregate.avg_composite)
            .where(ReviewAggregate.entity_type == "tenant",
                   ReviewAggregate.entity_id.in_(tenant_ids_str))
        )).all()
        ratings = {r.entity_id: r.avg_composite for r in agg_rows}

        staff_rows = (await self.db.execute(
            select(User.tenant_id, func.count(User.id).label("cnt"))
            .where(User.tenant_id.in_(tenant_uuids),
                   User.role == "staff",
                   User.is_active.is_(True))
            .group_by(User.tenant_id)
        )).all()
        staff_counts = {str(r.tenant_id): r.cnt for r in staff_rows}

        for m in matches_by_tenant.values():
            m["rating"] = ratings.get(m["tenant_id"])
            m["staff_capacity"] = staff_counts.get(m["tenant_id"], 0)

        # ── 5. Sort by ranking chain ──────────────────────────────────────────
        def _sort_key(m: dict) -> tuple:
            return (
                m["coverage_rank"],
                -(m["health_score"] or 0),
                -(m["rating"] or 0),
                -m["staff_capacity"],
                m["distance_km"] if m["distance_km"] is not None else float("inf"),
                m["estimated_sla_minutes"] if m["estimated_sla_minutes"] is not None else float("inf"),
                m["base_price"] if m["base_price"] is not None else float("inf"),
            )

        return sorted(matches_by_tenant.values(), key=_sort_key)

    async def check_serviceability(
        self, address_id: str | None, city: str | None, state: str | None,
        zipcode: str | None, latitude: float | None, longitude: float | None,
        service_id: str | None, job_type: str | None,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        self._validate_check_request(address_id, city, state, zipcode, service_id, job_type)
        resolved_city, resolved_state, resolved_zip, resolved_lat, resolved_lng, resolved_addr_id = (
            await self._resolve_location_full(address_id, city, state, zipcode, latitude, longitude)
        )
        service_type_id, service_name, _ = await self._resolve_service_type_id(service_id)
        svc_uuid = uuid.UUID(service_id)

        matches = await self.match_tenants_for_location(
            resolved_city, resolved_state, resolved_zip,
            resolved_lat, resolved_lng, service_type_id, job_type,
        )

        available = len(matches) > 0
        best_level = matches[0]["coverage_match_level"] if matches else None
        response = {
            "service_available": available,
            "city": resolved_city,
            "zipcode": resolved_zip,
            "service_id": service_id,
            "service_type_id": service_type_id,
            "service_name": service_name,
            "job_type": job_type,
            "matched_tenants_count": len(matches),
            "best_match_level": best_level,
            "matches": {
                "zipcode_level": sum(1 for m in matches if m["coverage_match_level"] == MatchLevel.ZIPCODE),
                "zone_level":    sum(1 for m in matches if m["coverage_match_level"] == MatchLevel.ZONE),
                "city_level":    sum(1 for m in matches if m["coverage_match_level"] == MatchLevel.CITY),
                "radius_level":  sum(1 for m in matches if m["coverage_match_level"] == MatchLevel.RADIUS),
            },
            "message": ("Service is available in your area" if available
                        else "This service is not available in your area yet"),
        }

        self.db.add(ServiceabilityAuditLog(
            customer_id=customer_id, address_id=resolved_addr_id, service_id=svc_uuid,
            job_type=job_type, city=resolved_city, zipcode=resolved_zip,
            result="available" if available else "unavailable",
            matched_tenants_count=len(matches), best_match_level=best_level,
            request_payload={"address_id": address_id, "city": city, "state": state,
                              "zipcode": zipcode, "service_id": service_id, "job_type": job_type},
            response_payload=response,
        ))
        await self.db.commit()
        return response

    async def get_matching_tenants(
        self, address_id: str | None, city: str | None, state: str | None,
        zipcode: str | None, latitude: float | None, longitude: float | None,
        service_id: str | None, job_type: str | None,
    ) -> dict:
        self._validate_check_request(address_id, city, state, zipcode, service_id, job_type)
        resolved_city, resolved_state, resolved_zip, resolved_lat, resolved_lng, _ = (
            await self._resolve_location_full(address_id, city, state, zipcode, latitude, longitude)
        )
        service_type_id, service_name, category = await self._resolve_service_type_id(service_id)

        # tenant_owner sees only their own tenant
        filter_tenant = self.actor_tenant_id if self.actor_role == "tenant_owner" else None

        matches = await self.match_tenants_for_location(
            resolved_city, resolved_state, resolved_zip,
            resolved_lat, resolved_lng, service_type_id, job_type,
            filter_tenant_id=filter_tenant,
        )
        return {
            "service_type_id": service_type_id,
            "service_name": service_name,
            "category": category,
            "job_type": job_type,
            "total_matched": len(matches),
            "matched_tenants": matches,
        }

    async def get_available_services_for_address(
        self, address_id: str | None, city: str | None = None, state: str | None = None,
        zipcode: str | None = None, latitude: float | None = None,
        longitude: float | None = None, customer_id: uuid.UUID | None = None,
    ) -> dict:
        if not address_id and not city:
            raise ServiceOSException(ERR_LOCATION_REQUIRED,
                "Provide address_id or city+state to look up available services.",
                status_code=422)
        if not address_id and not state:
            raise ServiceOSException(ERR_CHECK_STATE_REQUIRED,
                "state is required when address_id is not provided.", status_code=422)

        resolved_city, resolved_state, resolved_zip, resolved_lat, resolved_lng, _ = (
            await self._resolve_location_full(address_id, city, state, zipcode, latitude, longitude)
        )
        norm_city = self._norm(resolved_city)
        strip_zip = self._strip_zip(resolved_zip) if resolved_zip else None

        from app.engines.geo.models import ServiceZone

        stmt = (
            select(
                ServiceCatalogItem.service_type_id.label("service_type_id"),
                ServiceCatalogItem.name.label("service_name"),
                ServiceCatalogItem.category.label("category"),
                TenantServiceArea.coverage_type.label("coverage_type"),
                TenantServiceArea.city.label("area_city"),
                TenantServiceArea.zipcode.label("area_zipcode"),
                TenantServiceArea.zone_id.label("zone_id"),
                TenantServiceArea.latitude.label("area_lat"),
                TenantServiceArea.longitude.label("area_lng"),
                TenantServiceArea.radius_km.label("radius_km"),
                TenantServiceAreaService.job_type.label("job_type"),
                TenantServiceAreaService.sla_minutes.label("sla_minutes"),
                TenantServiceAreaService.base_price.label("base_price"),
                Tenant.id.label("tenant_id"),
            )
            .join(TenantServiceAreaService,
                  TenantServiceAreaService.service_id == ServiceCatalogItem.id)
            .join(TenantServiceArea,
                  TenantServiceArea.id == TenantServiceAreaService.tenant_service_area_id)
            .join(Tenant, Tenant.id == TenantServiceArea.tenant_id)
            .where(
                Tenant.status == "active",
                ServiceCatalogItem.is_active.is_(True),
                TenantServiceArea.is_active.is_(True),
                TenantServiceAreaService.is_available.is_(True),
            )
        )
        rows = (await self.db.execute(stmt)).all()

        zone_ids = {row.zone_id for row in rows
                    if row.coverage_type == CoverageType.ZONE and row.zone_id}
        zone_map: dict = {}
        if zone_ids:
            sz_rows = (await self.db.execute(
                select(ServiceZone).where(ServiceZone.id.in_(zone_ids),
                                          ServiceZone.is_active.is_(True))
            )).scalars().all()
            zone_map = {z.id: z for z in sz_rows}

        by_stype: dict[str, dict] = {}
        for row in rows:
            ct = row.coverage_type
            match_level: str | None = None

            if ct == CoverageType.CITY:
                if self._norm(row.area_city) == norm_city:
                    match_level = MatchLevel.CITY
            elif ct == CoverageType.ZIPCODE:
                if (self._norm(row.area_city) == norm_city and strip_zip and
                        self._strip_zip(row.area_zipcode) == strip_zip):
                    match_level = MatchLevel.ZIPCODE
            elif ct == CoverageType.ZONE and row.zone_id and row.zone_id in zone_map:
                zone = zone_map[row.zone_id]
                ids = zone.identifiers or []
                if zone.zone_type == "pincode" and strip_zip:
                    if strip_zip in [self._strip_zip(i) for i in ids]:
                        match_level = MatchLevel.ZONE
                elif zone.zone_type == "area_name":
                    if norm_city in [self._norm(i) for i in ids]:
                        match_level = MatchLevel.ZONE
            elif ct == CoverageType.RADIUS:
                if (resolved_lat is not None and resolved_lng is not None and
                        row.area_lat is not None and row.area_lng is not None):
                    dist = self._haversine_km(resolved_lat, resolved_lng, row.area_lat, row.area_lng)
                    if row.radius_km is not None and dist <= row.radius_km:
                        match_level = MatchLevel.RADIUS

            if match_level is None:
                continue

            rank = MATCH_LEVEL_PRIORITY[match_level]
            stype = row.service_type_id
            entry = by_stype.setdefault(stype, {
                "service_type_id": stype,
                "service_name": row.service_name,
                "category": row.category,
                "job_types": set(),
                "tenant_ids": set(),
                "best_match_level": match_level,
                "best_rank": rank,
                "starting_price": None,
                "estimated_sla_minutes": None,
            })
            entry["job_types"].add(row.job_type)
            entry["tenant_ids"].add(str(row.tenant_id))
            if rank < entry["best_rank"]:
                entry["best_match_level"] = match_level
                entry["best_rank"] = rank
            if row.base_price is not None:
                price = float(row.base_price)
                if entry["starting_price"] is None or price < entry["starting_price"]:
                    entry["starting_price"] = price
            if row.sla_minutes is not None:
                if entry["estimated_sla_minutes"] is None or row.sla_minutes < entry["estimated_sla_minutes"]:
                    entry["estimated_sla_minutes"] = row.sla_minutes

        categories: dict[str, dict] = {}
        for entry in by_stype.values():
            cat = entry["category"]
            cat_entry = categories.setdefault(cat, {
                "category_id": cat,
                "category_name": cat.replace("_", " ").title(),
                "services": [],
            })
            cat_entry["services"].append({
                "service_type_id": entry["service_type_id"],
                "service_name": entry["service_name"],
                "job_types": sorted(entry["job_types"]),
                "available_tenants": len(entry["tenant_ids"]),
                "best_match_level": entry["best_match_level"],
                "starting_price": entry["starting_price"],
                "estimated_sla_minutes": entry["estimated_sla_minutes"],
            })

        for cat in categories.values():
            cat["services"].sort(key=lambda s: MATCH_LEVEL_PRIORITY[s["best_match_level"]])

        return {
            "address_id": address_id,
            "city": resolved_city, "state": resolved_state, "zipcode": resolved_zip,
            "categories": list(categories.values()),
            "total_services": len(by_stype),
        }

    async def admin_serviceability_test(
        self, city: str, state: str | None, zipcode: str | None,
        latitude: float | None, longitude: float | None,
        service_id: str, job_type: str,
    ) -> dict:
        """Debug endpoint: matched tenants + categorized non-match reasons."""
        if job_type not in JOB_TYPES:
            raise ServiceOSException(ERR_INVALID_JOB_TYPE,
                f"job_type must be one of {JOB_TYPES}.", status_code=422)

        service_type_id, service_name, category = await self._resolve_service_type_id(service_id)

        matches = await self.match_tenants_for_location(
            city, state, zipcode, latitude, longitude, service_type_id, job_type,
        )
        matched_ids = {m["tenant_id"] for m in matches}

        # Fetch all active tenants
        all_tenants = (await self.db.execute(
            select(Tenant.id, Tenant.tenant_name).where(Tenant.status == "active")
        )).all()

        # For non-matched tenants: find which have an active mapping (coverage mismatch)
        non_matched_uuids = [t.id for t in all_tenants if str(t.id) not in matched_ids]
        non_matched_names = {str(t.id): t.tenant_name for t in all_tenants
                             if str(t.id) not in matched_ids}

        has_active_mapping: set[str] = set()
        if non_matched_uuids:
            raw_rows = (await self.db.execute(
                select(Tenant.id.label("tid"))
                .join(TenantServiceArea, TenantServiceArea.tenant_id == Tenant.id)
                .join(TenantServiceAreaService,
                      TenantServiceAreaService.tenant_service_area_id == TenantServiceArea.id)
                .join(ServiceCatalogItem,
                      ServiceCatalogItem.id == TenantServiceAreaService.service_id)
                .where(
                    Tenant.id.in_(non_matched_uuids),
                    Tenant.status == "active",
                    TenantServiceArea.is_active.is_(True),
                    TenantServiceAreaService.is_available.is_(True),
                    ServiceCatalogItem.service_type_id == service_type_id,
                    TenantServiceAreaService.job_type == job_type,
                )
                .distinct()
            )).all()
            has_active_mapping = {str(r.tid) for r in raw_rows}

        non_matching_debug = []
        for t in all_tenants:
            tid = str(t.id)
            if tid in matched_ids:
                continue
            if tid in has_active_mapping:
                reason = "coverage_mismatch"
                detail = "Active mapping exists but no service area covers this location"
            else:
                reason = "service_not_mapped"
                detail = "Tenant does not have an active mapping for this service + job_type"
            non_matching_debug.append({
                "tenant_id": tid,
                "tenant_name": non_matched_names[tid],
                "reason": reason,
                "detail": detail,
            })

        return {
            "query": {
                "city": city, "state": state, "zipcode": zipcode,
                "service_id": service_id, "service_type_id": service_type_id,
                "service_name": service_name, "category": category,
                "job_type": job_type, "latitude": latitude, "longitude": longitude,
            },
            "matched_tenants": matches,
            "total_matched": len(matches),
            "non_matching_debug": non_matching_debug,
            "total_non_matching": len(non_matching_debug),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Booking preflight
    # ══════════════════════════════════════════════════════════════════════════

    async def run_booking_preflight(
        self, customer_id: str, address_id: str, service_id: str,
        job_type: str, scheduled_at: str | None = None,
        preferred_tenant_id: str | None = None,
    ) -> dict:
        # 1. Address exists and has city
        addr = await self.get_address(uuid.UUID(address_id))
        if not addr.city:
            return {"can_book": False, "reason_code": ERR_INVALID_CITY,
                    "message": "Saved address is missing city."}

        # 2. job_type valid
        if job_type not in JOB_TYPES:
            return {"can_book": False, "reason_code": ERR_INVALID_JOB_TYPE,
                    "message": f"job_type must be one of {JOB_TYPES}."}

        # 3. Service exists and is active
        svc_uuid = uuid.UUID(service_id)
        service = await self.db.get(ServiceCatalogItem, svc_uuid)
        if not service:
            return {"can_book": False, "reason_code": ERR_SERVICE_NOT_FOUND,
                    "message": "Requested service does not exist."}
        if not service.is_active:
            return {"can_book": False, "reason_code": ERR_SERVICE_NOT_ACTIVE,
                    "message": "Requested service is not currently active."}

        # 4. Match via cross-tenant service_type_id resolution
        matches = await self.match_tenants_for_location(
            city=addr.city, state=addr.state, zipcode=addr.zipcode,
            latitude=addr.latitude, longitude=addr.longitude,
            service_type_id=service.service_type_id, job_type=job_type,
        )
        if preferred_tenant_id:
            pref = [m for m in matches if m["tenant_id"] == preferred_tenant_id]
            if pref:
                matches = pref

        if not matches:
            return {"can_book": False, "reason_code": ERR_NOT_AVAILABLE,
                    "message": "This service is not available in your area yet."}

        best = matches[0]
        tenant_uuid = uuid.UUID(best["tenant_id"])

        # 5. Staff capacity check
        staff_count = (await self.db.execute(
            select(func.count()).select_from(User).where(
                User.tenant_id == tenant_uuid, User.role == "staff", User.is_active.is_(True),
            )
        )).scalar_one()
        if staff_count == 0:
            return {"can_book": False, "reason_code": ERR_NO_STAFF,
                    "message": "Matched provider currently has no available staff capacity."}

        return {
            "can_book": True,
            "matched_tenant_id": best["tenant_id"],
            "matched_service_area_id": best["matched_area_id"],
            "coverage_match_level": best["coverage_match_level"],
            "estimated_price": best["base_price"],
            "sla_minutes": best["estimated_sla_minutes"],
            "available_slots": [],
        }
