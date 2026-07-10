"""Geo Engine — GeoService."""
from __future__ import annotations
import math, uuid
from datetime import datetime, timezone, timedelta
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.geo.constants import (
    EARTH_RADIUS_KM, ROAD_FACTOR, DEFAULT_RADIUS_KM, MAX_RADIUS_KM,
    REDIS_STAFF_LOC, REDIS_ZONE_PINS, REDIS_TENANT_ZONES, StaffStatus,
)
from app.engines.geo.models import ServiceZone, StaffLocation, ZoneAnalyticSnapshot
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("geo.service")
utcnow = lambda: datetime.now(timezone.utc)


class GeoService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id; self.actor_id = actor_id; self.actor_role = actor_role

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        r = EARTH_RADIUS_KM
        d_lat = math.radians(lat2 - lat1); d_lng = math.radians(lng2 - lng1)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng/2)**2
        return r * 2 * math.asin(math.sqrt(a))

    def _zone_dict(self, z: ServiceZone) -> dict:
        return {"zone_id": str(z.id), "zone_name": z.zone_name, "zone_type": z.zone_type,
                "identifiers": z.identifiers, "center_lat": z.center_lat, "center_lng": z.center_lng,
                "radius_km": z.radius_km, "surcharge_pct": z.surcharge_pct,
                "is_active": z.is_active, "valid_from": z.valid_from.isoformat(),
                "valid_until": z.valid_until.isoformat() if z.valid_until else None}

    def _loc_dict(self, l: StaffLocation) -> dict:
        return {"staff_id": str(l.staff_id), "tenant_id": str(l.tenant_id),
                "latitude": l.latitude, "longitude": l.longitude,
                "status": l.status, "active_job_count": l.active_job_count,
                "last_ping_at": l.last_ping_at.isoformat()}

    # ── Zone CRUD (5 methods) ─────────────────────────────────────────────────
    async def create_zone(self, tenant_id: uuid.UUID, data: dict) -> dict:
        z = ServiceZone(tenant_id=tenant_id, zone_name=data["zone_name"],
            zone_type=data["zone_type"], identifiers=data.get("identifiers", []),
            center_lat=data.get("center_lat"), center_lng=data.get("center_lng"),
            radius_km=data.get("radius_km"), surcharge_pct=data.get("surcharge_pct", 0.0),
            set_by=self.actor_id)
        self.db.add(z); await self.db.flush()
        # Cache pincodes in Redis Set for O(1) lookup
        if data["zone_type"] == "pincode" and data.get("identifiers"):
            try:
                key = REDIS_ZONE_PINS.format(zone_id=z.id)
                await self.redis.sadd(key, *data["identifiers"])
                await self.redis.expire(key, 86400)
            except Exception:
                pass
        return self._zone_dict(z)

    async def get_zone(self, zone_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ServiceZone).where(ServiceZone.id == zone_id))
        z = r.scalar_one_or_none()
        if not z: raise NotFoundException("ServiceZone", str(zone_id))
        return self._zone_dict(z)

    async def list_tenant_zones(self, tenant_id: uuid.UUID, active_only: bool) -> dict:
        q = select(ServiceZone).where(ServiceZone.tenant_id == tenant_id)
        if active_only: q = q.where(ServiceZone.is_active == True)
        r = await self.db.execute(q.order_by(ServiceZone.zone_name))
        zones = r.scalars().all()
        return {"tenant_id": str(tenant_id), "zones": [self._zone_dict(z) for z in zones]}

    async def update_zone(self, zone_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(select(ServiceZone).where(ServiceZone.id == zone_id))
        z = r.scalar_one_or_none()
        if not z: raise NotFoundException("ServiceZone", str(zone_id))
        for f in ("zone_name","identifiers","surcharge_pct","is_active","radius_km"):
            if f in data and data[f] is not None: setattr(z, f, data[f])
        if data.get("identifiers") and z.zone_type == "pincode":
            try:
                key = REDIS_ZONE_PINS.format(zone_id=zone_id)
                await self.redis.delete(key)
                await self.redis.sadd(key, *data["identifiers"])
                await self.redis.expire(key, 86400)
            except Exception:
                pass
        return self._zone_dict(z)

    async def delete_zone(self, zone_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ServiceZone).where(ServiceZone.id == zone_id))
        z = r.scalar_one_or_none()
        if not z: raise NotFoundException("ServiceZone", str(zone_id))
        z.is_active = False; z.valid_until = utcnow()
        try:
            await self.redis.delete(REDIS_ZONE_PINS.format(zone_id=zone_id))
        except Exception:
            pass
        return {"zone_id": str(zone_id), "deactivated": True}

    # ── Zone membership check ─────────────────────────────────────────────────
    async def check_pincode_in_zone(self, tenant_id: uuid.UUID, pincode: str) -> dict:
        """O(1) Redis lookup first, DB fallback."""
        r = await self.db.execute(select(ServiceZone).where(
            ServiceZone.tenant_id == tenant_id, ServiceZone.is_active == True))
        zones = r.scalars().all()
        matched = []
        for z in zones:
            if z.zone_type == "pincode":
                # Try Redis first
                try:
                    key = REDIS_ZONE_PINS.format(zone_id=z.id)
                    in_zone = await self.redis.sismember(key, pincode)
                except Exception:
                    in_zone = pincode in (z.identifiers or [])
                if in_zone:
                    matched.append({"zone_id": str(z.id), "zone_name": z.zone_name,
                                    "surcharge_pct": z.surcharge_pct})
        return {"pincode": pincode, "tenant_id": str(tenant_id),
                "in_service_area": len(matched) > 0, "matched_zones": matched}

    # ── Staff Location (3 methods) ────────────────────────────────────────────
    async def update_staff_location(self, staff_id: uuid.UUID, tenant_id: uuid.UUID,
                                     lat: float, lng: float, accuracy_m: float | None,
                                     status: str | None) -> dict:
        r = await self.db.execute(select(StaffLocation).where(
            StaffLocation.staff_id == staff_id, StaffLocation.tenant_id == tenant_id))
        loc = r.scalar_one_or_none()
        if loc:
            loc.latitude = lat; loc.longitude = lng
            loc.accuracy_m = accuracy_m; loc.last_ping_at = utcnow()
            if status: loc.status = status
        else:
            loc = StaffLocation(staff_id=staff_id, tenant_id=tenant_id,
                latitude=lat, longitude=lng, accuracy_m=accuracy_m,
                status=status or StaffStatus.AVAILABLE)
            self.db.add(loc)
        # Push to Redis geo index
        try:
            key = REDIS_STAFF_LOC.format(tenant_id=tenant_id)
            await self.redis.geoadd(key, (lng, lat, str(staff_id)))
            await self.redis.expire(key, 3600)
        except Exception:
            pass
        return self._loc_dict(loc)

    async def get_staff_location(self, staff_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(StaffLocation).where(
            StaffLocation.staff_id == staff_id, StaffLocation.tenant_id == tenant_id))
        loc = r.scalar_one_or_none()
        if not loc: raise NotFoundException("StaffLocation", str(staff_id))
        stale = (utcnow() - loc.last_ping_at).seconds > 600
        return {**self._loc_dict(loc), "is_stale": stale}

    async def get_staff_in_radius(self, tenant_id: uuid.UUID, lat: float, lng: float,
                                   radius_km: float, status_filter: str | None) -> dict:
        if radius_km > MAX_RADIUS_KM:
            raise ServiceOSException("VALIDATION_ERROR", f"Radius cannot exceed {MAX_RADIUS_KM}km.")
        r = await self.db.execute(select(StaffLocation).where(
            StaffLocation.tenant_id == tenant_id))
        all_staff = r.scalars().all()
        results = []
        cutoff = utcnow() - timedelta(minutes=10)
        for s in all_staff:
            if status_filter and s.status != status_filter:
                continue
            if s.last_ping_at < cutoff:
                continue  # skip stale locations
            dist = self._haversine(lat, lng, s.latitude, s.longitude)
            road_dist = round(dist * ROAD_FACTOR, 2)
            if dist <= radius_km:
                results.append({
                    "staff_id": str(s.staff_id), "distance_km": round(dist, 2),
                    "road_distance_km": road_dist, "status": s.status,
                    "active_job_count": s.active_job_count,
                    "eta_minutes": round(road_dist / 0.5, 0),  # 30km/h avg
                })
        results.sort(key=lambda x: x["distance_km"])
        return {"tenant_id": str(tenant_id), "center": {"lat": lat, "lng": lng},
                "radius_km": radius_km, "staff_found": len(results), "staff": results}

    async def get_coverage_map(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ServiceZone).where(
            ServiceZone.tenant_id == tenant_id, ServiceZone.is_active == True))
        zones = r.scalars().all()
        pincode_count = sum(len(z.identifiers) for z in zones if z.zone_type == "pincode")
        return {"tenant_id": str(tenant_id), "active_zones": len(zones),
                "total_pincodes_covered": pincode_count,
                "zones": [{"zone_id": str(z.id), "zone_name": z.zone_name,
                            "type": z.zone_type, "count": len(z.identifiers)}
                           for z in zones]}
