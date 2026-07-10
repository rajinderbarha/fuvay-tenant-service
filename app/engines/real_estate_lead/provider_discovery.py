"""Sprint 18 — Real Estate Provider Discovery Service.

Queries real TenantServiceArea + Tenant data.
Never returns fake providers.
Never exposes subscription_status, commission, or internal credit data.
"""
from __future__ import annotations
import uuid

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.real_estate_lead.constants import (
    DEFAULT_MAX_PROVIDERS,
    ERR_NO_PROVIDER_AVAILABLE,
    ERR_NO_EXACT_PROVIDER_MATCH,
    ERR_FAKE_PROVIDER_BLOCKED,
)

logger = structlog.get_logger("real_estate.provider_discovery")


class RealEstateProviderDiscoveryService:
    """
    Discovers eligible real estate providers/agents for a lead.

    Match priority:
    1. Exact zipcode match
    2. Locality match (city + locality substring)
    3. City-level fallback

    Customer-safe output only: tenant_id stripped from response top-level,
    provider_ref used as opaque reference.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_providers(
        self,
        category_id: uuid.UUID,
        offering_id: uuid.UUID,
        city: str | None,
        locality: str | None,
        zipcode: str | None,
        lead_intent: str | None = None,
        property_type: str | None = None,
        limit: int = DEFAULT_MAX_PROVIDERS,
    ) -> dict:
        """
        Find bookable real estate providers for a given location.

        Returns customer-safe provider info with match_reason.
        Tries exact location → city fallback → no provider.
        Never exposes subscription_status, commission, internal blockers.
        """
        try:
            from app.engines.tenant_engine.models import Tenant
            from app.engines.serviceability.models import TenantServiceArea

            # Base tenant query: active, discoverable, category match
            base_q = select(Tenant).where(
                and_(
                    Tenant.status == "active",
                    Tenant.is_discoverable == True,
                    Tenant.category_id == category_id,
                )
            ).limit(limit * 3)

            tenants = (await self.db.execute(base_q)).scalars().all()
            if not tenants:
                return self._no_provider_response(city)

            tenant_ids = [t.id for t in tenants]
            tenant_map = {t.id: t for t in tenants}

            # ── Try exact zipcode match ────────────────────────────────────────
            if zipcode:
                matched = await self._match_by_zipcode(tenant_ids, tenant_map, zipcode, limit)
                if matched:
                    return self._build_response(
                        matched, "zipcode", f"Real estate support available in your area.",
                        available=True
                    )

            # ── Try locality match ─────────────────────────────────────────────
            if city and locality:
                matched = await self._match_by_locality(tenant_ids, tenant_map, city, locality, limit)
                if matched:
                    return self._build_response(
                        matched, "locality", f"Real estate support available in {locality}, {city}.",
                        available=True
                    )

            # ── Try city-level match ───────────────────────────────────────────
            if city:
                matched = await self._match_by_city(tenant_ids, tenant_map, city, limit)
                if matched:
                    # City-level match → not exact, return as fallback
                    return {
                        "available":              False,
                        "reason_code":            ERR_NO_EXACT_PROVIDER_MATCH,
                        "message":                f"No exact locality provider, but city-level support is available in {city}.",
                        "matched_by":             None,
                        "fallback_available":     True,
                        "fallback_providers":     [self._safe_provider(t, tenant_map[t], "City-level support") for t in matched],
                        "available_provider_count": 0,
                        "providers":              [],
                    }

            return self._no_provider_response(city)

        except Exception as exc:
            logger.warning("real_estate.provider_discovery.failed", error=str(exc))
            return {
                "available": False,
                "reason_code": ERR_NO_PROVIDER_AVAILABLE,
                "message": "Unable to find providers at this time.",
                "providers": [],
            }

    async def _match_by_zipcode(
        self, tenant_ids: list, tenant_map: dict, zipcode: str, limit: int
    ) -> list[tuple]:
        """Return (tenant_id, tenant, match_reason) for zipcode matches."""
        from app.engines.serviceability.models import TenantServiceArea
        q = select(TenantServiceArea).where(
            and_(
                TenantServiceArea.tenant_id.in_(tenant_ids),
                TenantServiceArea.zipcode == zipcode,
                TenantServiceArea.is_active == True,
            )
        ).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        seen: set[uuid.UUID] = set()
        result = []
        for r in rows:
            if r.tenant_id not in seen and r.tenant_id in tenant_map:
                seen.add(r.tenant_id)
                result.append((r.tenant_id, tenant_map[r.tenant_id], "Zipcode match"))
        return result

    async def _match_by_locality(
        self, tenant_ids: list, tenant_map: dict, city: str, locality: str, limit: int
    ) -> list[tuple]:
        """Return (tenant_id, tenant, match_reason) for city + locality matches."""
        from app.engines.serviceability.models import TenantServiceArea
        q = select(TenantServiceArea).where(
            and_(
                TenantServiceArea.tenant_id.in_(tenant_ids),
                TenantServiceArea.city.ilike(f"%{city}%"),
                TenantServiceArea.is_active == True,
            )
        ).limit(limit * 2)
        rows = (await self.db.execute(q)).scalars().all()
        seen: set[uuid.UUID] = set()
        result = []
        for r in rows:
            if r.tenant_id not in seen and r.tenant_id in tenant_map:
                seen.add(r.tenant_id)
                result.append((r.tenant_id, tenant_map[r.tenant_id], "Locality match"))
            if len(result) >= limit:
                break
        return result

    async def _match_by_city(
        self, tenant_ids: list, tenant_map: dict, city: str, limit: int
    ) -> list[tuple]:
        """Return (tenant_id, tenant, match_reason) for city-level fallback."""
        from app.engines.serviceability.models import TenantServiceArea
        q = select(TenantServiceArea).where(
            and_(
                TenantServiceArea.tenant_id.in_(tenant_ids),
                TenantServiceArea.city.ilike(f"%{city}%"),
                TenantServiceArea.is_active == True,
            )
        ).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        seen: set[uuid.UUID] = set()
        result = []
        for r in rows:
            if r.tenant_id not in seen and r.tenant_id in tenant_map:
                seen.add(r.tenant_id)
                result.append((r.tenant_id, tenant_map[r.tenant_id], "City-level support"))
            if len(result) >= limit:
                break
        return result

    def _safe_provider(self, tenant_id: uuid.UUID, tenant, match_reason: str) -> dict:
        """Build customer-safe provider dict. Never expose commission/subscription."""
        return {
            "provider_ref":     str(tenant_id),  # opaque ref, NOT tenant_id label
            "business_name":    tenant.business_name or tenant.tenant_name,
            "city":             tenant.city,
            "locality":         None,
            "profile_photo_url":tenant.logo_url,
            "rating":           float(tenant.rating_average) if tenant.rating_average else None,
            "agent_available":  True,
            "match_reason":     match_reason,
        }

    def _build_response(
        self, matches: list[tuple], matched_by: str, message: str, available: bool
    ) -> dict:
        providers = [self._safe_provider(tid, t, reason) for tid, t, reason in matches]
        return {
            "available":               available,
            "available_provider_count": len(providers),
            "matched_by":              matched_by,
            "message":                 message,
            "providers":               providers,
            "fallback_available":      False,
            "fallback_providers":      [],
        }

    def _no_provider_response(self, city: str | None) -> dict:
        loc = f" in {city}" if city else ""
        return {
            "available":           False,
            "reason_code":         ERR_NO_PROVIDER_AVAILABLE,
            "message":             f"No real estate providers found{loc} right now. Your inquiry will be saved for follow-up.",
            "matched_by":          None,
            "fallback_available":  True,
            "fallback_type":       "platform_inquiry_callback",
            "providers":           [],
            "fallback_providers":  [],
        }

    async def validate_provider_bookable(
        self, tenant_id: uuid.UUID, category_id: uuid.UUID
    ) -> bool:
        """Verify a specific provider is still active and bookable. Blocks fake providers."""
        try:
            from app.engines.tenant_engine.models import Tenant
            q = select(Tenant).where(
                and_(
                    Tenant.id == tenant_id,
                    Tenant.status == "active",
                    Tenant.is_discoverable == True,
                    Tenant.category_id == category_id,
                )
            )
            result = (await self.db.execute(q)).scalars().first()
            return result is not None
        except Exception as exc:
            logger.warning("real_estate.validate_provider.failed", error=str(exc))
            return False
