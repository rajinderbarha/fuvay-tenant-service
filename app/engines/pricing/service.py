"""Pricing Engine — PricingService. All business logic. No router code."""
from __future__ import annotations
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.pricing.constants import (
    MAX_BRAND_ADJUSTMENT_PCT, MAX_ZONE_SURCHARGE_PCT,
    MAX_DYNAMIC_SURGE_PCT, MAX_DYNAMIC_DISCOUNT_PCT,
    REDIS_PRICE_CACHE, REDIS_CITY_TIER, SNAPSHOT_IDEMPOTENCY_TTL_SECONDS,
)
from app.engines.pricing.models import (
    CityTierConfig, ServiceTypePrice, BrandAdjustment,
    ZoneSurcharge, DynamicPricingRule, PriceSnapshot,
)
from app.engines.pricing.pipeline import compute_price
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_set, cache_get, cache_delete
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("pricing.service")
utcnow = lambda: datetime.now(timezone.utc)


class PricingService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        """Slice 2F-37: set_tenant_price/set_brand_adjustment/create_zone/
        create_rule accepted a client-supplied tenant_id with no comparison
        to the caller's own tenant. super_admin is exempt (platform-wide)."""
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="pricing_mutation_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's pricing.",
                blocking_rule="pricing_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict) -> None:
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="pricing",
                tenant_id=tenant_id, entity_type="pricing", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("pricing.event_failed", error=str(e))

    async def _invalidate_tenant_cache(self, tenant_id: str) -> None:
        try:
            pattern = f"serviceos:pricing:*:{tenant_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception:
            pass

    def _ctc_dict(self, c: CityTierConfig) -> dict:
        return {
            "config_id": str(c.id), "city_name": c.city_name, "tier": c.tier,
            "service_category": c.service_category, "service_name": c.service_name or "",
            "floor_price": float(c.floor_price),
            "min_price": float(c.min_price) if c.min_price is not None else None,
            "max_price": float(c.max_price) if c.max_price is not None else None,
            "default_estimate": float(c.default_estimate) if c.default_estimate is not None else None,
            "visit_fee": float(c.visit_fee) if c.visit_fee is not None else None,
            "bargain_floor": float(c.bargain_floor) if c.bargain_floor is not None else None,
            "provider_override_allowed": c.provider_override_allowed,
            "currency": c.currency, "is_active": c.is_active, "notes": c.notes,
            "created_at": c.created_at.isoformat(),
        }

    def _stp_dict(self, s: ServiceTypePrice) -> dict:
        return {"price_id": str(s.id), "tenant_id": str(s.tenant_id),
                "service_type_id": s.service_type_id, "service_category": s.service_category,
                "city_name": s.city_name, "base_price": float(s.base_price), "unit": s.unit,
                "valid_from": s.valid_from.isoformat(),
                "valid_until": s.valid_until.isoformat() if s.valid_until else None,
                "previous_price": float(s.previous_price) if s.previous_price else None,
                "change_reason": s.change_reason}

    def _zone_dict(self, z: ZoneSurcharge) -> dict:
        return {"zone_id": str(z.id), "zone_name": z.zone_name, "zone_type": z.zone_type,
                "zone_identifiers": z.zone_identifiers, "surcharge_pct": float(z.surcharge_pct),
                "is_active": z.is_active, "notes": z.notes, "created_at": z.created_at.isoformat()}

    def _rule_dict(self, r: DynamicPricingRule) -> dict:
        return {"rule_id": str(r.id), "rule_name": r.rule_name, "rule_type": r.rule_type,
                "adjustment_pct": float(r.adjustment_pct), "conditions": r.conditions,
                "applies_to": r.applies_to, "priority": r.priority, "is_active": r.is_active,
                "active_from": r.active_from.isoformat() if r.active_from else None,
                "active_until": r.active_until.isoformat() if r.active_until else None,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None}

    def _snapshot_dict(self, s: PriceSnapshot) -> dict:
        return {"snapshot_id": str(s.id), "tenant_id": str(s.tenant_id),
                "booking_id": s.booking_id, "service_type_id": s.service_type_id,
                "city_name": s.city_name, "final_price": float(s.final_price),
                "currency": s.currency, "steps_summary": s.step_city_floor,
                "pipeline_inputs": s.pipeline_inputs,
                "step_city_floor": s.step_city_floor,
                "step_tenant_price": s.step_tenant_price,
                "step_brand_adj": s.step_brand_adj,
                "step_zone_surge": s.step_zone_surge,
                "step_dynamic_rule": s.step_dynamic_rule,
                "requested_at": s.requested_at.isoformat(),
                "created_at": s.created_at.isoformat()}

    # ── City Tier Config (5 methods) ──────────────────────────────────────────
    async def list_city_tier_configs(self, tier: str | None, category: str | None,
                                      limit: int, cursor: str | None) -> dict:
        q = select(CityTierConfig).order_by(CityTierConfig.tier, CityTierConfig.city_name)
        if tier:
            q = q.where(CityTierConfig.tier == tier)
        if category:
            q = q.where(CityTierConfig.service_category == category)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(CityTierConfig.city_name > c["city_name"])
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"city_name": items[-1].city_name}) if has_next and items else None
        return {"configs": [self._ctc_dict(c) for c in items], "has_next": has_next, "next_cursor": nc}

    async def get_city_tier_config(self, config_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(CityTierConfig).where(CityTierConfig.id == config_id))
        c = r.scalar_one_or_none()
        if not c: raise NotFoundException("CityTierConfig", str(config_id))
        return self._ctc_dict(c)

    async def create_city_tier_config(self, data: dict) -> dict:
        service_name = data.get("service_name") or ""
        # Check for duplicate (city + category + service_name must be unique)
        ex = await self.db.execute(select(CityTierConfig).where(
            CityTierConfig.city_name == data["city_name"],
            CityTierConfig.service_category == data["service_category"],
            CityTierConfig.service_name == service_name,
            CityTierConfig.is_active == True))
        if ex.scalar_one_or_none():
            scope = f"{data['city_name']} × {data['service_category']}"
            if service_name:
                scope += f" × {service_name}"
            raise ServiceOSException("CONFLICT",
                f"Active config already exists for {scope}. Use PUT to update.")

        def _d(key: str) -> Decimal | None:
            v = data.get(key)
            return Decimal(str(v)) if v is not None else None

        c = CityTierConfig(
            city_name=data["city_name"], tier=data["tier"],
            service_category=data["service_category"],
            service_name=service_name,
            floor_price=Decimal(str(data["floor_price"])),
            min_price=_d("min_price"), max_price=_d("max_price"),
            default_estimate=_d("default_estimate"), visit_fee=_d("visit_fee"),
            bargain_floor=_d("bargain_floor"),
            provider_override_allowed=data.get("provider_override_allowed", True),
            notes=data.get("notes"), set_by=self.actor_id,
        )
        self.db.add(c); await self.db.flush()
        try:
            await cache_delete(REDIS_CITY_TIER.format(city=data["city_name"]))
        except Exception: pass
        await self._publish("pricing.city_tier_created", "platform", str(c.id),
                            {"city": c.city_name, "category": c.service_category,
                             "service": service_name})
        return self._ctc_dict(c)

    async def update_city_tier_config(self, config_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(select(CityTierConfig).where(CityTierConfig.id == config_id))
        c = r.scalar_one_or_none()
        if not c: raise NotFoundException("CityTierConfig", str(config_id))
        if "floor_price" in data and data["floor_price"]:
            c.floor_price = Decimal(str(data["floor_price"]))
        for field in ("min_price", "max_price", "default_estimate", "visit_fee", "bargain_floor"):
            if field in data:
                setattr(c, field, Decimal(str(data[field])) if data[field] is not None else None)
        if "provider_override_allowed" in data and data["provider_override_allowed"] is not None:
            c.provider_override_allowed = data["provider_override_allowed"]
        if "is_active" in data and data["is_active"] is not None:
            c.is_active = data["is_active"]
        if "notes" in data:
            c.notes = data["notes"]
        try:
            await cache_delete(REDIS_CITY_TIER.format(city=c.city_name))
        except Exception: pass
        await self._publish("pricing.city_tier_updated", "platform", str(c.id),
                            {"city": c.city_name, "floor_price": float(c.floor_price)})
        return self._ctc_dict(c)

    async def delete_city_tier_config(self, config_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(CityTierConfig).where(CityTierConfig.id == config_id))
        c = r.scalar_one_or_none()
        if not c: raise NotFoundException("CityTierConfig", str(config_id))
        c.is_active = False
        return {"config_id": str(config_id), "deactivated": True}

    # ── Service Type Prices (4 methods) ────────────────────────────────────────
    async def list_tenant_prices(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(ServiceTypePrice).where(
            ServiceTypePrice.tenant_id == tenant_id,
            ServiceTypePrice.valid_until == None,
        ).order_by(ServiceTypePrice.service_type_id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(ServiceTypePrice.service_type_id > c["service_type_id"])
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"service_type_id": items[-1].service_type_id}) if has_next and items else None
        return {"prices": [self._stp_dict(s) for s in items], "has_next": has_next, "next_cursor": nc}

    async def get_tenant_price(self, tenant_id: uuid.UUID, service_type_id: str) -> dict:
        r = await self.db.execute(select(ServiceTypePrice).where(
            ServiceTypePrice.tenant_id == tenant_id,
            ServiceTypePrice.service_type_id == service_type_id,
            ServiceTypePrice.valid_until == None))
        s = r.scalar_one_or_none()
        if not s: raise NotFoundException("ServiceTypePrice", service_type_id)
        return self._stp_dict(s)

    async def set_tenant_price(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        service_type_id = data["service_type_id"]
        new_price = Decimal(str(data["base_price"]))

        # Validate against city floor
        floor_r = await self.db.execute(select(CityTierConfig).where(
            CityTierConfig.city_name == data["city_name"],
            CityTierConfig.service_category == data["service_category"],
            CityTierConfig.is_active == True))
        floor = floor_r.scalar_one_or_none()
        if floor and new_price < floor.floor_price:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Price ₹{new_price} is below the city floor ₹{floor.floor_price} for {data['city_name']}.",
                resolution=f"Set a price ≥ ₹{floor.floor_price}.",
                context={"minimum_price": float(floor.floor_price), "your_price": float(new_price)})

        # Supersede existing active price
        existing_r = await self.db.execute(select(ServiceTypePrice).where(
            ServiceTypePrice.tenant_id == tenant_id,
            ServiceTypePrice.service_type_id == service_type_id,
            ServiceTypePrice.valid_until == None))
        existing = existing_r.scalar_one_or_none()
        prev_price = None
        if existing:
            prev_price = existing.base_price
            existing.valid_until = utcnow()

        new = ServiceTypePrice(tenant_id=tenant_id, service_type_id=service_type_id,
            service_category=data["service_category"], city_name=data["city_name"],
            base_price=new_price, unit=data.get("unit","per_visit"),
            set_by=self.actor_id, change_reason=data.get("change_reason"),
            previous_price=prev_price)
        self.db.add(new); await self.db.flush()

        await self._invalidate_tenant_cache(str(tenant_id))
        await self._publish("pricing.service_price_set", str(tenant_id), str(new.id),
                            {"service_type_id": service_type_id, "new_price": float(new_price),
                             "prev_price": float(prev_price) if prev_price else None})
        return self._stp_dict(new)

    async def get_tenant_price_history(self, tenant_id: uuid.UUID, service_type_id: str,
                                        limit: int, cursor: str | None) -> dict:
        q = select(ServiceTypePrice).where(
            ServiceTypePrice.tenant_id == tenant_id,
            ServiceTypePrice.service_type_id == service_type_id,
        ).order_by(ServiceTypePrice.valid_from.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(ServiceTypePrice.valid_from < datetime.fromisoformat(c["valid_from"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"valid_from": items[-1].valid_from.isoformat()}) if has_next and items else None
        return {"history": [self._stp_dict(s) for s in items], "has_next": has_next, "next_cursor": nc}

    # ── Brand Adjustment (2 methods) ──────────────────────────────────────────
    async def get_brand_adjustment(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(BrandAdjustment).where(
            BrandAdjustment.tenant_id == tenant_id,
            BrandAdjustment.valid_until == None))
        b = r.scalar_one_or_none()
        if not b:
            return {"tenant_id": str(tenant_id), "adjustment_pct": 0.0, "label": None,
                    "message": "No brand adjustment set. Default: 0% (neutral)."}
        return {"tenant_id": str(tenant_id), "adjustment_pct": float(b.adjustment_pct),
                "label": b.label, "valid_from": b.valid_from.isoformat(),
                "price_id": str(b.id)}

    async def set_brand_adjustment(self, tenant_id: uuid.UUID, adjustment_pct: Decimal,
                                    label: str | None, reason: str | None) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        if abs(adjustment_pct) > MAX_BRAND_ADJUSTMENT_PCT:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Brand adjustment cannot exceed ±{MAX_BRAND_ADJUSTMENT_PCT}%.",
                context={"max_allowed": float(MAX_BRAND_ADJUSTMENT_PCT), "requested": float(adjustment_pct)})
        existing_r = await self.db.execute(select(BrandAdjustment).where(
            BrandAdjustment.tenant_id == tenant_id, BrandAdjustment.valid_until == None))
        existing = existing_r.scalar_one_or_none()
        if existing:
            existing.valid_until = utcnow()
        new = BrandAdjustment(tenant_id=tenant_id, adjustment_pct=adjustment_pct,
            label=label, set_by=self.actor_id, reason=reason)
        self.db.add(new); await self.db.flush()
        await self._invalidate_tenant_cache(str(tenant_id))
        await self._publish("pricing.brand_adjustment_set", str(tenant_id), str(new.id),
                            {"pct": float(adjustment_pct), "label": label})
        return {"tenant_id": str(tenant_id), "adjustment_pct": float(adjustment_pct),
                "label": label, "valid_from": new.valid_from.isoformat()}

    # ── Zone Surcharges (5 methods) ───────────────────────────────────────────
    async def list_zones(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ZoneSurcharge).where(
            ZoneSurcharge.tenant_id == tenant_id).order_by(ZoneSurcharge.zone_name))
        zones = r.scalars().all()
        return {"zones": [self._zone_dict(z) for z in zones], "total": len(zones)}

    async def create_zone(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        if Decimal(str(data["surcharge_pct"])) > MAX_ZONE_SURCHARGE_PCT:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Zone surcharge cannot exceed {MAX_ZONE_SURCHARGE_PCT}%.")
        z = ZoneSurcharge(tenant_id=tenant_id, zone_name=data["zone_name"],
            zone_type=data.get("zone_type","pincode"),
            zone_identifiers=data["zone_identifiers"],
            surcharge_pct=Decimal(str(data["surcharge_pct"])),
            notes=data.get("notes"), set_by=self.actor_id)
        self.db.add(z); await self.db.flush()
        await self._invalidate_tenant_cache(str(tenant_id))
        return self._zone_dict(z)

    async def get_zone(self, zone_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ZoneSurcharge).where(ZoneSurcharge.id == zone_id))
        z = r.scalar_one_or_none()
        if not z: raise NotFoundException("ZoneSurcharge", str(zone_id))
        return self._zone_dict(z)

    async def update_zone(self, zone_id: uuid.UUID, data: dict, tenant_id: uuid.UUID | None = None) -> dict:
        if tenant_id is not None:
            tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(ZoneSurcharge).where(ZoneSurcharge.id == zone_id))
        z = r.scalar_one_or_none()
        if not z: raise NotFoundException("ZoneSurcharge", str(zone_id))
        if tenant_id is not None and z.tenant_id != tenant_id:
            raise NotFoundException("ZoneSurcharge", str(zone_id))
        if "zone_name" in data and data["zone_name"]: z.zone_name = data["zone_name"]
        if "zone_identifiers" in data and data["zone_identifiers"]: z.zone_identifiers = data["zone_identifiers"]
        if "surcharge_pct" in data and data["surcharge_pct"]:
            if Decimal(str(data["surcharge_pct"])) > MAX_ZONE_SURCHARGE_PCT:
                raise ServiceOSException("VALIDATION_ERROR", f"Zone surcharge cannot exceed {MAX_ZONE_SURCHARGE_PCT}%.")
            z.surcharge_pct = Decimal(str(data["surcharge_pct"]))
        if "is_active" in data and data["is_active"] is not None: z.is_active = data["is_active"]
        if "notes" in data: z.notes = data["notes"]
        await self._invalidate_tenant_cache(str(z.tenant_id))
        return self._zone_dict(z)

    async def delete_zone(self, zone_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> dict:
        if tenant_id is not None:
            tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(ZoneSurcharge).where(ZoneSurcharge.id == zone_id))
        z = r.scalar_one_or_none()
        if not z: raise NotFoundException("ZoneSurcharge", str(zone_id))
        if tenant_id is not None and z.tenant_id != tenant_id:
            raise NotFoundException("ZoneSurcharge", str(zone_id))
        await self.db.delete(z)
        await self._invalidate_tenant_cache(str(z.tenant_id))
        return {"zone_id": str(zone_id), "deleted": True}

    # ── Dynamic Rules (6 methods) ─────────────────────────────────────────────
    async def list_rules(self, tenant_id: uuid.UUID, active_only: bool) -> dict:
        q = select(DynamicPricingRule).where(DynamicPricingRule.tenant_id == tenant_id)
        if active_only: q = q.where(DynamicPricingRule.is_active == True)
        q = q.order_by(DynamicPricingRule.priority)
        r = await self.db.execute(q)
        rules = r.scalars().all()
        return {"rules": [self._rule_dict(rule) for rule in rules], "total": len(rules)}

    async def create_rule(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        adj = Decimal(str(data["adjustment_pct"]))
        if adj > MAX_DYNAMIC_SURGE_PCT:
            raise ServiceOSException("VALIDATION_ERROR", f"Surge cannot exceed +{MAX_DYNAMIC_SURGE_PCT}%.")
        if adj < -MAX_DYNAMIC_DISCOUNT_PCT:
            raise ServiceOSException("VALIDATION_ERROR", f"Discount cannot exceed -{MAX_DYNAMIC_DISCOUNT_PCT}%.")
        active_from = datetime.fromisoformat(data["active_from"]) if data.get("active_from") else None
        active_until = datetime.fromisoformat(data["active_until"]) if data.get("active_until") else None
        rule = DynamicPricingRule(tenant_id=tenant_id, rule_name=data["rule_name"],
            rule_type=data["rule_type"], adjustment_pct=adj,
            conditions=data.get("conditions",{}), applies_to=data.get("applies_to",[]),
            priority=data.get("priority",10), set_by=self.actor_id,
            active_from=active_from, active_until=active_until,
            is_active=not bool(active_from))  # auto-activate if no schedule
        self.db.add(rule); await self.db.flush()
        await self._invalidate_tenant_cache(str(tenant_id))
        return self._rule_dict(rule)

    async def get_rule(self, rule_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DynamicPricingRule).where(DynamicPricingRule.id == rule_id))
        rule = r.scalar_one_or_none()
        if not rule: raise NotFoundException("DynamicPricingRule", str(rule_id))
        return self._rule_dict(rule)

    async def update_rule(self, rule_id: uuid.UUID, data: dict, tenant_id: uuid.UUID | None = None) -> dict:
        if tenant_id is not None:
            tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(DynamicPricingRule).where(DynamicPricingRule.id == rule_id))
        rule = r.scalar_one_or_none()
        if not rule: raise NotFoundException("DynamicPricingRule", str(rule_id))
        if tenant_id is not None and rule.tenant_id != tenant_id:
            raise NotFoundException("DynamicPricingRule", str(rule_id))
        for f in ("rule_name","conditions","applies_to","priority"):
            if f in data and data[f] is not None: setattr(rule, f, data[f])
        if "adjustment_pct" in data and data["adjustment_pct"] is not None:
            rule.adjustment_pct = Decimal(str(data["adjustment_pct"]))
        if "active_from" in data and data["active_from"]:
            rule.active_from = datetime.fromisoformat(data["active_from"])
        if "active_until" in data and data["active_until"]:
            rule.active_until = datetime.fromisoformat(data["active_until"])
        await self._invalidate_tenant_cache(str(rule.tenant_id))
        return self._rule_dict(rule)

    async def activate_rule(self, rule_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DynamicPricingRule).where(DynamicPricingRule.id == rule_id))
        rule = r.scalar_one_or_none()
        if not rule: raise NotFoundException("DynamicPricingRule", str(rule_id))
        if rule.is_active: raise ServiceOSException("CONFLICT", "Rule is already active.")
        rule.is_active = True
        await self._invalidate_tenant_cache(str(rule.tenant_id))
        await self._publish("pricing.rule_activated", str(rule.tenant_id), str(rule_id),
                            {"rule_name": rule.rule_name})
        return self._rule_dict(rule)

    async def deactivate_rule(self, rule_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DynamicPricingRule).where(DynamicPricingRule.id == rule_id))
        rule = r.scalar_one_or_none()
        if not rule: raise NotFoundException("DynamicPricingRule", str(rule_id))
        rule.is_active = False
        await self._invalidate_tenant_cache(str(rule.tenant_id))
        return self._rule_dict(rule)

    async def delete_rule(self, rule_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> dict:
        if tenant_id is not None:
            tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(DynamicPricingRule).where(DynamicPricingRule.id == rule_id))
        rule = r.scalar_one_or_none()
        if not rule: raise NotFoundException("DynamicPricingRule", str(rule_id))
        if tenant_id is not None and rule.tenant_id != tenant_id:
            raise NotFoundException("DynamicPricingRule", str(rule_id))
        if rule.is_active: raise ServiceOSException("CONFLICT",
            "Deactivate the rule before deleting.", resolution="POST /rules/{id}/deactivate first.")
        await self.db.delete(rule)
        return {"rule_id": str(rule_id), "deleted": True}

    # ── Price Computation (3 methods) ─────────────────────────────────────────
    async def compute_and_snapshot(self, tenant_id: uuid.UUID, service_type_id: str,
                                    service_category: str, city_name: str,
                                    pincode: str | None, booking_id: str | None,
                                    requested_at_str: str | None) -> dict:
        requested_at = datetime.fromisoformat(requested_at_str) if requested_at_str else utcnow()

        # Idempotency key — same booking+service within TTL window returns same price
        idem_raw = f"{tenant_id}:{service_type_id}:{city_name}:{booking_id or ''}:{requested_at.strftime('%Y%m%d%H%M')}"
        idem_key = hashlib.sha256(idem_raw.encode()).hexdigest()[:64]

        # Check existing snapshot
        ex = await self.db.execute(select(PriceSnapshot).where(
            PriceSnapshot.idempotency_key == idem_key))
        existing = ex.scalar_one_or_none()
        if existing:
            return {**self._snapshot_dict(existing), "idempotent": True}

        # Run pipeline
        result = await compute_price(self.db, str(tenant_id), service_type_id,
                                      service_category, city_name, pincode, requested_at)

        # Store immutable snapshot
        snap = PriceSnapshot(tenant_id=tenant_id, booking_id=booking_id,
            service_type_id=service_type_id, service_category=service_category,
            city_name=city_name, pincode=pincode, requested_at=requested_at,
            pipeline_inputs=result["pipeline_inputs"],
            step_city_floor=result["step_city_floor"],
            step_tenant_price=result["step_tenant_price"],
            step_brand_adj=result["step_brand_adj"],
            step_zone_surge=result["step_zone_surge"],
            step_dynamic_rule=result["step_dynamic_rule"],
            final_price=result["final_price"], idempotency_key=idem_key,
            requested_by=self.actor_id)
        self.db.add(snap); await self.db.flush()

        if matched := result["step_dynamic_rule"].get("rule_matched"):
            await self.db.execute(update(DynamicPricingRule)
                .where(DynamicPricingRule.tenant_id == tenant_id,
                       DynamicPricingRule.rule_name == matched)
                .values(last_triggered_at=utcnow()))

        return {**self._snapshot_dict(snap), "steps_summary": result["steps_summary"],
                "idempotent": False}

    async def preview_price(self, tenant_id: uuid.UUID, service_type_id: str,
                             service_category: str, city_name: str, pincode: str | None) -> dict:
        """Read-only pipeline run. No snapshot stored."""
        result = await compute_price(self.db, str(tenant_id), service_type_id,
                                      service_category, city_name, pincode)
        return {**result, "preview": True, "note": "Price not locked. Call /compute to lock."}

    async def replay_snapshot(self, snapshot_id: uuid.UUID) -> dict:
        """Replay the exact inputs from a historical snapshot for dispute resolution."""
        r = await self.db.execute(select(PriceSnapshot).where(PriceSnapshot.id == snapshot_id))
        snap = r.scalar_one_or_none()
        if not snap: raise NotFoundException("PriceSnapshot", str(snapshot_id))
        inputs = snap.pipeline_inputs
        result = await compute_price(self.db, inputs["tenant_id"], inputs["service_type_id"],
                                      inputs["service_category"], inputs["city_name"],
                                      inputs.get("pincode"),
                                      datetime.fromisoformat(inputs["requested_at"]))
        price_matches = abs(result["final_price"] - snap.final_price) < Decimal("0.01")
        return {"original_snapshot": self._snapshot_dict(snap), "replayed_result": result,
                "price_matches": price_matches,
                "note": "If price_matches=false, pricing rules changed after this snapshot was taken."}

    # ── Snapshot History (2 methods) ──────────────────────────────────────────
    async def list_snapshots(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(PriceSnapshot).where(PriceSnapshot.tenant_id == tenant_id)            .order_by(PriceSnapshot.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(PriceSnapshot.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"snapshots": [{"snapshot_id": str(s.id), "service_type_id": s.service_type_id,
                "booking_id": s.booking_id, "final_price": float(s.final_price),
                "city_name": s.city_name, "created_at": s.created_at.isoformat()}
               for s in items], "has_next": has_next, "next_cursor": nc}

    async def get_snapshot(self, snapshot_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(PriceSnapshot).where(PriceSnapshot.id == snapshot_id))
        s = r.scalar_one_or_none()
        if not s: raise NotFoundException("PriceSnapshot", str(snapshot_id))
        return self._snapshot_dict(s)

    # ── Cache Management (2 methods) ──────────────────────────────────────────
    async def invalidate_tenant_cache(self, tenant_id: uuid.UUID) -> dict:
        await self._invalidate_tenant_cache(str(tenant_id))
        return {"tenant_id": str(tenant_id), "cache_invalidated": True}

    async def get_cache_status(self, tenant_id: uuid.UUID) -> dict:
        try:
            keys = await self.redis.keys(f"serviceos:pricing:*:{tenant_id}:*")
            return {"tenant_id": str(tenant_id), "cached_keys": len(keys),
                    "keys": [k.decode() if isinstance(k, bytes) else k for k in keys]}
        except Exception:
            return {"tenant_id": str(tenant_id), "cached_keys": 0, "error": "Redis unavailable"}
