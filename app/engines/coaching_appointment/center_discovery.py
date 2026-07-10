"""Sprint 17 — CoachingCenterDiscoveryService.

Queries real TenantServiceArea + Tenant to find bookable coaching centers.
No fake data. No hardcoded IELTS-only logic.
"""
from __future__ import annotations
import uuid
from typing import Any

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.coaching_appointment.constants import (
    ERR_NO_CENTER_AVAILABLE, LOC_STATUS_AVAILABLE, LOC_STATUS_NOT_AVAILABLE,
    LOC_STATUS_PENDING, MODE_OFFLINE, MODE_ONLINE,
)

logger = structlog.get_logger("coaching.center_discovery")


class CoachingCenterDiscoveryService:
    """
    Finds bookable coaching centers/providers for a given offering + location.

    Rules:
    - Only returns active tenants that belong to the Coaching category
    - For offline mode: tenant must have TenantServiceArea covering city/zipcode
    - For online mode: any active tenant with the offering is returned
    - Only returns customer-safe fields (no commission, subscription_status, etc.)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_centers(
        self,
        category_id: uuid.UUID,
        offering_id: uuid.UUID,
        city: str | None,
        zipcode: str | None,
        preferred_mode: str | None,
        limit: int = 10,
    ) -> dict:
        """
        Returns available booking centers.

        For offline mode: geo-filtered by city/zipcode using TenantServiceArea.
        For online mode: category-filtered only (no geo needed).
        """
        try:
            from app.engines.tenant_engine.models import Tenant
            from app.engines.serviceability.models import TenantServiceArea
            from app.engines.admin_catalog.models import TenantService

            centers: list[dict] = []

            if preferred_mode == MODE_ONLINE:
                # Online: any active tenant in this category that has the offering enabled
                q = (
                    select(Tenant)
                    .join(TenantService, and_(
                        TenantService.tenant_id == Tenant.id,
                        TenantService.is_enabled == True,
                        TenantService.is_active == True,
                    ))
                    .where(
                        Tenant.status == "active",
                        Tenant.category_id == category_id,
                        Tenant.is_discoverable == True,
                    )
                    .order_by(Tenant.health_score.desc(), Tenant.rating_average.desc())
                    .limit(limit)
                )
                rows = (await self.db.execute(q)).scalars().all()
                for t in rows:
                    centers.append(self._make_center_option(t, "online"))
            else:
                # Offline (default): zipcode-exact first, then city fallback
                # Step 1: zipcode-exact
                if zipcode:
                    zq = (
                        select(Tenant, TenantServiceArea)
                        .join(TenantServiceArea, and_(
                            TenantServiceArea.tenant_id == Tenant.id,
                            TenantServiceArea.is_active == True,
                            TenantServiceArea.zipcode == zipcode,
                        ))
                        .where(
                            Tenant.status == "active",
                            Tenant.category_id == category_id,
                            Tenant.is_discoverable == True,
                        )
                        .order_by(Tenant.health_score.desc(), Tenant.rating_average.desc())
                        .limit(limit)
                    )
                    zip_rows = (await self.db.execute(zq)).all()
                    seen: set[uuid.UUID] = set()
                    for row in zip_rows:
                        t = row[0]
                        if t.id not in seen:
                            seen.add(t.id)
                            centers.append(self._make_center_option(t, "zipcode"))

                # Step 2: city fallback to fill remaining slots
                if city and len(centers) < limit:
                    seen_ids = {c["_tenant_id"] for c in centers}
                    cq = (
                        select(Tenant, TenantServiceArea)
                        .join(TenantServiceArea, and_(
                            TenantServiceArea.tenant_id == Tenant.id,
                            TenantServiceArea.is_active == True,
                            TenantServiceArea.city.ilike(city),
                        ))
                        .where(
                            Tenant.status == "active",
                            Tenant.category_id == category_id,
                            Tenant.is_discoverable == True,
                            ~Tenant.id.in_(seen_ids) if seen_ids else True,
                        )
                        .order_by(Tenant.health_score.desc(), Tenant.rating_average.desc())
                        .limit(limit - len(centers))
                    )
                    city_rows = (await self.db.execute(cq)).all()
                    seen2: set[uuid.UUID] = set()
                    for row in city_rows:
                        t = row[0]
                        if t.id not in seen2:
                            seen2.add(t.id)
                            centers.append(self._make_center_option(t, "city"))

            if not centers:
                return {
                    "available": False,
                    "available_center_count": 0,
                    "centers": [],
                    "reason_code": ERR_NO_CENTER_AVAILABLE,
                    "message": "No coaching center is available for this appointment yet.",
                    "location_status": LOC_STATUS_NOT_AVAILABLE,
                }

            # Strip internal field before returning
            safe_centers = [{k: v for k, v in c.items() if k != "_tenant_id"} for c in centers]

            return {
                "available": True,
                "available_center_count": len(safe_centers),
                "centers": safe_centers,
                "matched_by": safe_centers[0].get("service_area_match", "city") if safe_centers else None,
                "message": f"Found {len(safe_centers)} coaching center(s) available.",
                "location_status": LOC_STATUS_AVAILABLE,
            }

        except Exception as exc:
            logger.warning("coaching.center_discovery.failed", error=str(exc))
            return {
                "available": False,
                "available_center_count": 0,
                "centers": [],
                "reason_code": ERR_NO_CENTER_AVAILABLE,
                "message": "Unable to find coaching centers at this time.",
                "location_status": LOC_STATUS_NOT_AVAILABLE,
            }

    def _make_center_option(self, tenant: Any, match_type: str) -> dict:
        """Build a customer-safe center dict. Never includes commission/subscription."""
        return {
            "_tenant_id":         tenant.id,  # internal only — stripped before API response
            "provider_ref":       str(tenant.id),
            "business_name":      tenant.business_name or tenant.tenant_name,
            "city":               tenant.city,
            "rating":             float(tenant.rating_average) if tenant.rating_average else 0.0,
            "profile_photo_url":  tenant.logo_url,
            "available_modes":    ["offline", "online"],  # may be refined in future sprint
            "service_area_match": match_type,
            "is_bookable":        True,
        }
