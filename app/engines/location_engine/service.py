"""Location Engine — Service.

Reads from location master tables. Admin endpoints seed the data.
All list methods paginate and support search.
"""
from __future__ import annotations
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.location_engine.models import (
    LocationState, LocationDistrict, LocationCity, LocationZone,
)
from app.exceptions import ServiceOSException

VALID_CITY_TIERS = {"small", "mid", "large", "metro"}


class LocationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── States ──────────────────────────────────────────────────────────────────

    async def list_states(
        self, country_code: str = "IN", search: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        q = select(LocationState).where(
            LocationState.is_active == True,
            LocationState.country_code == country_code,
        )
        if search:
            q = q.where(LocationState.state_name.ilike(f"%{search}%"))
        q = q.order_by(LocationState.state_name)

        total = await self._count(
            select(func.count()).select_from(LocationState).where(
                LocationState.is_active == True,
                LocationState.country_code == country_code,
            )
        )
        q = q.offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(q)
        states = r.scalars().all()
        return self._paginated(
            items=[{"id": str(s.id), "state_name": s.state_name, "state_code": s.state_code,
                    "country_code": s.country_code} for s in states],
            total=total, page=page, page_size=page_size,
        )

    # ── Districts ───────────────────────────────────────────────────────────────

    async def list_districts(
        self, state_id: uuid.UUID, search: str | None = None,
        page: int = 1, page_size: int = 100,
    ) -> dict:
        state = await self._require_state(state_id)
        q = select(LocationDistrict).where(
            LocationDistrict.state_id == state_id,
            LocationDistrict.is_active == True,
        )
        if search:
            q = q.where(LocationDistrict.district_name.ilike(f"%{search}%"))
        q = q.order_by(LocationDistrict.district_name)
        total = await self._count(
            select(func.count()).select_from(LocationDistrict).where(
                LocationDistrict.state_id == state_id,
                LocationDistrict.is_active == True,
            )
        )
        q = q.offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(q)
        districts = r.scalars().all()
        return self._paginated(
            items=[{"id": str(d.id), "district_name": d.district_name,
                    "district_code": d.district_code, "state_id": str(d.state_id)}
                   for d in districts],
            total=total, page=page, page_size=page_size,
        )

    # ── Cities ──────────────────────────────────────────────────────────────────

    async def list_cities(
        self, district_id: uuid.UUID, search: str | None = None,
        page: int = 1, page_size: int = 100,
    ) -> dict:
        await self._require_district(district_id)
        q = select(LocationCity).where(
            LocationCity.district_id == district_id,
            LocationCity.is_active == True,
        )
        if search:
            q = q.where(LocationCity.city_name.ilike(f"%{search}%"))
        q = q.order_by(LocationCity.city_name)
        total = await self._count(
            select(func.count()).select_from(LocationCity).where(
                LocationCity.district_id == district_id,
                LocationCity.is_active == True,
            )
        )
        q = q.offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(q)
        cities = r.scalars().all()
        return self._paginated(
            items=[{"id": str(c.id), "city_name": c.city_name,
                    "city_tier": c.city_tier, "district_id": str(c.district_id),
                    "state_id": str(c.state_id)} for c in cities],
            total=total, page=page, page_size=page_size,
        )

    # ── Zones ───────────────────────────────────────────────────────────────────

    async def list_zones(
        self, city_id: uuid.UUID, search: str | None = None,
        page: int = 1, page_size: int = 100,
    ) -> dict:
        await self._require_city(city_id)
        q = select(LocationZone).where(
            LocationZone.city_id == city_id,
            LocationZone.is_active == True,
        )
        if search:
            q = q.where(LocationZone.zone_name.ilike(f"%{search}%"))
        q = q.order_by(LocationZone.zone_name)
        total = await self._count(
            select(func.count()).select_from(LocationZone).where(
                LocationZone.city_id == city_id,
                LocationZone.is_active == True,
            )
        )
        q = q.offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(q)
        zones = r.scalars().all()
        return self._paginated(
            items=[{"id": str(z.id), "zone_name": z.zone_name,
                    "pincode": z.pincode, "city_id": str(z.city_id)} for z in zones],
            total=total, page=page, page_size=page_size,
        )

    async def list_city_tiers(self) -> dict:
        return {
            "items": [
                {"value": "metro",  "label": "Metro"},
                {"value": "large",  "label": "Large City"},
                {"value": "mid",    "label": "Mid-Size City"},
                {"value": "small",  "label": "Small Town"},
            ]
        }

    # ── Admin seed methods ──────────────────────────────────────────────────────

    async def create_state(self, data: dict) -> dict:
        s = LocationState(
            country_code=data.get("country_code", "IN"),
            state_name=data["state_name"].strip(),
            state_code=data.get("state_code", "").strip(),
            is_active=data.get("is_active", True),
        )
        self.db.add(s)
        await self.db.flush()
        return {"id": str(s.id), "state_name": s.state_name, "state_code": s.state_code}

    async def create_district(self, state_id: uuid.UUID, data: dict) -> dict:
        await self._require_state(state_id)
        d = LocationDistrict(
            state_id=state_id,
            district_name=data["district_name"].strip(),
            district_code=data.get("district_code"),
            is_active=data.get("is_active", True),
        )
        self.db.add(d)
        await self.db.flush()
        return {"id": str(d.id), "district_name": d.district_name, "state_id": str(state_id)}

    async def create_city(self, district_id: uuid.UUID, data: dict) -> dict:
        district = await self._require_district(district_id)
        tier = data.get("city_tier")
        if tier and tier not in VALID_CITY_TIERS:
            raise ServiceOSException("LOCATION_INVALID_HIERARCHY",
                                     f"city_tier must be one of {VALID_CITY_TIERS}")
        c = LocationCity(
            state_id=district.state_id,
            district_id=district_id,
            city_name=data["city_name"].strip(),
            city_tier=tier,
            is_active=data.get("is_active", True),
        )
        self.db.add(c)
        await self.db.flush()
        return {"id": str(c.id), "city_name": c.city_name, "city_tier": c.city_tier,
                "district_id": str(district_id)}

    async def create_zone(self, city_id: uuid.UUID, data: dict) -> dict:
        city = await self._require_city(city_id)
        z = LocationZone(
            state_id=city.state_id,
            district_id=city.district_id,
            city_id=city_id,
            zone_name=data["zone_name"].strip(),
            pincode=data.get("pincode"),
            is_active=data.get("is_active", True),
        )
        self.db.add(z)
        await self.db.flush()
        return {"id": str(z.id), "zone_name": z.zone_name, "pincode": z.pincode,
                "city_id": str(city_id)}

    # ── Validators ──────────────────────────────────────────────────────────────

    async def _require_state(self, state_id: uuid.UUID) -> LocationState:
        r = await self.db.execute(
            select(LocationState).where(LocationState.id == state_id,
                                        LocationState.is_active == True)
        )
        s = r.scalar_one_or_none()
        if not s:
            raise ServiceOSException("LOCATION_STATE_NOT_FOUND",
                                     f"State {state_id} not found or inactive.")
        return s

    async def _require_district(self, district_id: uuid.UUID) -> LocationDistrict:
        r = await self.db.execute(
            select(LocationDistrict).where(LocationDistrict.id == district_id,
                                           LocationDistrict.is_active == True)
        )
        d = r.scalar_one_or_none()
        if not d:
            raise ServiceOSException("LOCATION_DISTRICT_NOT_FOUND",
                                     f"District {district_id} not found or inactive.")
        return d

    async def _require_city(self, city_id: uuid.UUID) -> LocationCity:
        r = await self.db.execute(
            select(LocationCity).where(LocationCity.id == city_id,
                                       LocationCity.is_active == True)
        )
        c = r.scalar_one_or_none()
        if not c:
            raise ServiceOSException("LOCATION_CITY_NOT_FOUND",
                                     f"City {city_id} not found or inactive.")
        return c

    async def _count(self, q) -> int:
        r = await self.db.execute(q)
        return r.scalar_one() or 0

    def _paginated(self, items: list, total: int, page: int, page_size: int) -> dict:
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": items,
            "pagination": {
                "page": page, "page_size": page_size,
                "total_items": total, "total_pages": total_pages,
                "has_next": page < total_pages, "has_previous": page > 1,
            },
        }
