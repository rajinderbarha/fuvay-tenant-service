"""Service Catalog Engine — ServiceCatalogService."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.service_catalog.constants import SERVICE_TYPES, PRICING_MODELS
from app.engines.service_catalog.models import ServiceCatalogItem
from app.exceptions import ServiceOSException, NotFoundException
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("service_catalog.service")


class ServiceCatalogService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role

    def _dict(self, item: ServiceCatalogItem) -> dict:
        return {
            "item_id": str(item.id), "tenant_id": str(item.tenant_id),
            "service_type_id": item.service_type_id, "name": item.name,
            "service_type": item.service_type, "category": item.category,
            "description": item.description, "pricing_model": item.pricing_model,
            "base_price": float(item.base_price) if item.base_price is not None else None,
            "max_price": float(item.max_price) if item.max_price is not None else None,
            "visit_fee": float(item.visit_fee) if item.visit_fee is not None else None,
            "pre_approval_limit": float(item.pre_approval_limit) if item.pre_approval_limit is not None else None,
            "estimated_duration_minutes": item.estimated_duration_minutes,
            "checklist_required": item.checklist_required,
            "checklist_template": item.checklist_template, "is_active": item.is_active,
            "created_at": item.created_at.isoformat(),
        }

    def _validate(self, service_type: str, pricing_model: str,
                   base_price: Decimal | None, max_price: Decimal | None,
                   checklist_required: bool = False, checklist_template: list | None = None) -> None:
        if service_type not in SERVICE_TYPES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"service_type must be one of: {', '.join(SERVICE_TYPES)}",
                context={"provided": service_type})
        if pricing_model not in PRICING_MODELS:
            raise ServiceOSException("VALIDATION_ERROR",
                f"pricing_model must be one of: {', '.join(PRICING_MODELS)}",
                context={"provided": pricing_model})
        if base_price is not None and max_price is not None and max_price < base_price:
            raise ServiceOSException("VALIDATION_ERROR",
                "max_price cannot be less than base_price.",
                context={"base_price": float(base_price), "max_price": float(max_price)})
        if checklist_required and not (checklist_template or []):
            raise ServiceOSException("VALIDATION_ERROR",
                "checklist_required is set but checklist_template is empty — "
                "define at least one checklist step.")

    async def create_item(self, tenant_id: uuid.UUID, data: dict) -> dict:
        self._validate(data["service_type"], data["pricing_model"],
                        Decimal(str(data["base_price"])) if data.get("base_price") is not None else None,
                        Decimal(str(data["max_price"])) if data.get("max_price") is not None else None,
                        data.get("checklist_required", False), data.get("checklist_template", []))

        existing = await self.db.execute(select(ServiceCatalogItem).where(
            ServiceCatalogItem.tenant_id == tenant_id,
            ServiceCatalogItem.service_type_id == data["service_type_id"]))
        if existing.scalar_one_or_none():
            raise ServiceOSException("CONFLICT",
                f"A service with service_type_id '{data['service_type_id']}' already exists for this tenant.")

        item = ServiceCatalogItem(
            tenant_id=tenant_id, service_type_id=data["service_type_id"], name=data["name"],
            service_type=data["service_type"], category=data.get("category", "general"),
            description=data.get("description"), pricing_model=data["pricing_model"],
            base_price=Decimal(str(data["base_price"])) if data.get("base_price") is not None else None,
            max_price=Decimal(str(data["max_price"])) if data.get("max_price") is not None else None,
            visit_fee=Decimal(str(data["visit_fee"])) if data.get("visit_fee") is not None else None,
            pre_approval_limit=Decimal(str(data["pre_approval_limit"]))
                if data.get("pre_approval_limit") is not None else None,
            estimated_duration_minutes=data.get("estimated_duration_minutes"),
            checklist_required=data.get("checklist_required", False),
            checklist_template=data.get("checklist_template", []),
            is_active=data.get("is_active", True),
        )
        self.db.add(item)
        await self.db.flush()
        logger.info("catalog.item_created", tenant_id=str(tenant_id), service_type_id=item.service_type_id)
        return self._dict(item)

    async def get_item(self, item_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item: raise NotFoundException("ServiceCatalogItem", str(item_id))
        return self._dict(item)

    async def get_by_service_type_id(self, tenant_id: uuid.UUID, service_type_id: str) -> ServiceCatalogItem | None:
        """Internal lookup used by the booking engine — returns the ORM row, not a dict."""
        r = await self.db.execute(select(ServiceCatalogItem).where(
            ServiceCatalogItem.tenant_id == tenant_id,
            ServiceCatalogItem.service_type_id == service_type_id))
        return r.scalar_one_or_none()

    async def list_items(self, tenant_id: uuid.UUID, service_type: str | None,
                          is_active: bool | None, limit: int, cursor: str | None) -> dict:
        q = select(ServiceCatalogItem).where(ServiceCatalogItem.tenant_id == tenant_id) \
            .order_by(ServiceCatalogItem.created_at.desc())
        if service_type: q = q.where(ServiceCatalogItem.service_type == service_type)
        if is_active is not None: q = q.where(ServiceCatalogItem.is_active == is_active)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(ServiceCatalogItem.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"items": [self._dict(i) for i in items], "has_next": has_next, "next_cursor": nc}

    async def update_item(self, item_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item: raise NotFoundException("ServiceCatalogItem", str(item_id))

        new_service_type = data.get("service_type", item.service_type)
        new_pricing_model = data.get("pricing_model", item.pricing_model)
        new_base = Decimal(str(data["base_price"])) if "base_price" in data and data["base_price"] is not None else item.base_price
        new_max = Decimal(str(data["max_price"])) if "max_price" in data and data["max_price"] is not None else item.max_price
        new_checklist_required = data.get("checklist_required", item.checklist_required)
        new_checklist_template = data.get("checklist_template", item.checklist_template)
        self._validate(new_service_type, new_pricing_model, new_base, new_max,
                        new_checklist_required, new_checklist_template)

        for field in ("name", "category", "description", "estimated_duration_minutes",
                      "checklist_required", "checklist_template", "is_active"):
            if field in data:
                setattr(item, field, data[field])
        for field in ("base_price", "max_price", "visit_fee", "pre_approval_limit"):
            if field in data:
                setattr(item, field, Decimal(str(data[field])) if data[field] is not None else None)
        if "service_type" in data: item.service_type = data["service_type"]
        if "pricing_model" in data: item.pricing_model = data["pricing_model"]
        return self._dict(item)

    async def deactivate_item(self, item_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item: raise NotFoundException("ServiceCatalogItem", str(item_id))
        item.is_active = False
        return self._dict(item)
