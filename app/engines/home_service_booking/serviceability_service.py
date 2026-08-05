"""Sprint 16 — HomeServiceServiceabilityService.

Checks whether a Home Service offering is available in a given city/zipcode
by querying real provider service areas. Backend is source of truth.
DeepSeek never decides serviceability.
"""
from __future__ import annotations
import uuid

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_booking.constants import (
    ERR_NO_PROVIDER_IN_ZIPCODE, ERR_NO_PROVIDER_IN_CITY,
    ERR_CATEGORY_INVALID, ERR_OFFERING_INVALID,
)

logger = structlog.get_logger("home_service.serviceability")


class HomeServiceServiceabilityService:
    """
    Answers: "Is this Home Service offering available at city/zipcode?"

    Uses TenantServiceArea + Tenant tables from the serviceability engine.
    Does not use the complex service_type_id mapping — matches by category
    and geographic coverage. No fake data. No hardcoded providers.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check(
        self,
        category_id: uuid.UUID,
        offering_id: uuid.UUID,
        city: str,
        zipcode: str | None = None,
        offering_type_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Returns:
          {
            "serviceable": bool,
            "available_provider_count": int,
            "matched_by": "zipcode"|"city"|None,
            "message": str,
            "reason_code": str | None,
          }
        """
        from app.engines.admin_catalog.models import ServiceCategory, MasterService
        from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService
        from app.engines.tenant_engine.models import Tenant

        # ── Validate category is active ───────────────────────────────────────
        cat = (await self.db.execute(
            select(ServiceCategory).where(
                ServiceCategory.id == category_id,
                ServiceCategory.is_active.is_(True),
            )
        )).scalars().first()
        if not cat:
            return {
                "serviceable": False,
                "available_provider_count": 0,
                "matched_by": None,
                "message": "Service category is not available.",
                "reason_code": ERR_CATEGORY_INVALID,
            }

        # ── Validate offering is active ───────────────────────────────────────
        # HS7 fix: was querying the empty legacy MasterOffering table (see
        # service.py's start_booking_draft for the full explanation).
        offering = (await self.db.execute(
            select(MasterService).where(
                MasterService.id == offering_id,
                MasterService.category_id == category_id,
                MasterService.is_active.is_(True),
            )
        )).scalars().first()
        if not offering:
            return {
                "serviceable": False,
                "available_provider_count": 0,
                "matched_by": None,
                "message": "This service offering is not available.",
                "reason_code": ERR_OFFERING_INVALID,
            }

        norm_city = city.strip().lower()
        strip_zip = zipcode.strip() if zipcode else None

        # HS7 fix: this previously filtered by `Tenant.category_id`, a
        # column that is never populated on the real `tenants` table
        # (confirmed via direct query — every real dev tenant has
        # category_id = NULL). That made serviceability always report
        # "not available" even for zipcodes a provider genuinely covers.
        # Rewritten to join HS6B's canonical coverage table
        # (`tenant_service_area_services`), scoped by the actual offering
        # being booked — the same source of truth the provider-first
        # matching engine's eligibility gate already uses, so a
        # "serviceable" result here is guaranteed to be matchable in Step 4.
        base_filters = [
            TenantServiceArea.is_active.is_(True),
            Tenant.status == "active",
            TenantServiceAreaService.service_id == offering_id,
            TenantServiceAreaService.is_available.is_(True),
        ]

        # ── Try zipcode match first ───────────────────────────────────────────
        # A zipcode already uniquely identifies the coverage area on its own
        # -- requiring the free-text `city` field to ALSO match exactly was a
        # real bug: confirmed live, a tenant's TenantServiceArea.city was
        # stored as "BASSIPATHANA" (no space) while the customer's own
        # address city was "Bassi Pathana" (with space). Both genuinely
        # describe the same 140412 coverage area with an active, available
        # offering mapping, but the case/whitespace mismatch made the AND'd
        # city-equality clause silently fail, so `check_serviceability`
        # reported NO_PROVIDER_IN_ZIPCODE for a zipcode a real tenant does
        # cover -- permanently blocking Booking Review after this point.
        if strip_zip:
            zip_count = (await self.db.execute(
                select(func.count(func.distinct(TenantServiceArea.tenant_id)))
                .select_from(TenantServiceAreaService)
                .join(TenantServiceArea, TenantServiceArea.id == TenantServiceAreaService.tenant_service_area_id)
                .join(Tenant, Tenant.id == TenantServiceArea.tenant_id)
                .where(
                    *base_filters,
                    TenantServiceArea.zipcode == strip_zip,
                )
            )).scalar_one_or_none() or 0

            if zip_count > 0:
                return {
                    "serviceable": True,
                    "available_provider_count": zip_count,
                    "matched_by": "zipcode",
                    "message": f"Service is available in {city} {strip_zip}.",
                    "reason_code": None,
                }

        # ── Fall back to city match ───────────────────────────────────────────
        city_count = (await self.db.execute(
            select(func.count(func.distinct(TenantServiceArea.tenant_id)))
            .select_from(TenantServiceAreaService)
            .join(TenantServiceArea, TenantServiceArea.id == TenantServiceAreaService.tenant_service_area_id)
            .join(Tenant, Tenant.id == TenantServiceArea.tenant_id)
            .where(
                *base_filters,
                func.lower(TenantServiceArea.city) == norm_city,
            )
        )).scalar_one_or_none() or 0

        if city_count > 0:
            reason = ERR_NO_PROVIDER_IN_ZIPCODE if strip_zip else None
            msg = (
                f"Service is available in {city}."
                if not strip_zip
                else f"Service is available in {city} (full {strip_zip} coverage depends on provider)."
            )
            return {
                "serviceable": True,
                "available_provider_count": city_count,
                "matched_by": "city",
                "message": msg,
                "reason_code": reason,
            }

        reason = ERR_NO_PROVIDER_IN_ZIPCODE if strip_zip else ERR_NO_PROVIDER_IN_CITY
        return {
            "serviceable": False,
            "available_provider_count": 0,
            "matched_by": None,
            "message": f"This service is not available in {city} yet. We're expanding soon!",
            "reason_code": reason,
        }
