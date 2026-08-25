"""Inventory Engine — InventoryService. Proven Level 5.
SELECT FOR UPDATE on StockBalance. Append-only StockTransaction ledger.
Reconciliation on every balance read. Celery TTL on reservations.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.inventory.constants import (
    StockTxnType, ReservationStatus, RESERVATION_TTL_HOURS,
    REDIS_STOCK_BALANCE,
)
from app.engines.inventory.models import (
    InventoryItem, StockLocation, StockBalance, StockTransaction, StockReservation,
)
from app.engines.admin_catalog.models import ServiceGroup
from app.engines.entitlement.models import TenantCategoryEntitlement
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("inventory.service")
utcnow = lambda: datetime.now(timezone.utc)


class InventoryService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        """Slice 2F-36: every held inventory mutation accepted a client-
        supplied tenant_id (path or body) with no comparison to the
        caller's own tenant, letting any tenant-side principal create
        items/receive stock/reserve stock against another tenant by
        supplying that tenant's id. super_admin is exempt (platform-wide,
        matches every other _require_trusted_tenant in this program)."""
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="inventory_mutation_requires_trusted_tenant_context", status_code=403)
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's inventory.",
                blocking_rule="inventory_mutation_cross_tenant_denied", status_code=403)
        return self.actor_tenant_id

    async def _require_item(self, item_id: uuid.UUID, tenant_id: uuid.UUID | None = None,
                            *, active_only: bool = False) -> InventoryItem:
        effective_tenant = tenant_id or self.actor_tenant_id
        q = select(InventoryItem).where(InventoryItem.id == item_id)
        if self.actor_role != "super_admin":
            if effective_tenant is None:
                raise ServiceOSException("PERMISSION_DENIED", "No tenant context.", status_code=403)
            q = q.where(InventoryItem.tenant_id == effective_tenant)
        elif tenant_id is not None:
            q = q.where(InventoryItem.tenant_id == tenant_id)
        if active_only:
            q = q.where(InventoryItem.is_active == True, InventoryItem.status == "published")
        item = (await self.db.execute(q)).scalar_one_or_none()
        if not item:
            raise NotFoundException("InventoryItem", str(item_id))
        return item

    async def _require_location(self, location_id: uuid.UUID, tenant_id: uuid.UUID,
                                *, active_only: bool = True) -> StockLocation:
        q = select(StockLocation).where(
            StockLocation.id == location_id,
            StockLocation.tenant_id == tenant_id,
        )
        if active_only:
            q = q.where(StockLocation.is_active == True)
        location = (await self.db.execute(q)).scalar_one_or_none()
        if not location:
            raise NotFoundException("StockLocation", str(location_id))
        return location

    async def _resolve_service_group(self, tenant_id: uuid.UUID, data: dict) -> tuple[uuid.UUID | None, str | None]:
        """Resolve an inventory category only through the tenant's active setup entitlement."""
        raw_id = data.get("service_group_id")
        raw_label = (data.get("category") or "").strip()
        if not raw_id and not raw_label:
            return None, None
        q = (
            select(ServiceGroup)
            .join(TenantCategoryEntitlement, TenantCategoryEntitlement.category_id == ServiceGroup.id)
            .where(
                TenantCategoryEntitlement.tenant_id == tenant_id,
                TenantCategoryEntitlement.status == "ACTIVE",
                ServiceGroup.status == "active",
                ServiceGroup.deleted_at.is_(None),
            )
        )
        if raw_id:
            try:
                q = q.where(ServiceGroup.id == uuid.UUID(str(raw_id)))
            except ValueError:
                raise ServiceOSException("VALIDATION_ERROR", "Invalid service category identifier.")
        else:
            q = q.where(or_(func.lower(ServiceGroup.name) == raw_label.lower(),
                            func.lower(ServiceGroup.slug) == raw_label.lower()))
        group = (await self.db.execute(q)).scalar_one_or_none()
        if not group:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "Select a service category enabled for this provider in setup.",
                blocking_rule="inventory_category_requires_active_tenant_entitlement",
            )
        return group.id, group.name

    @staticmethod
    def _validate_item_data(data: dict, *, partial: bool = False) -> None:
        if not partial or "name" in data:
            if not str(data.get("name") or "").strip():
                raise ServiceOSException("VALIDATION_ERROR", "Item name is required.")
        if not partial or "sku" in data:
            if not str(data.get("sku") or "").strip():
                raise ServiceOSException("VALIDATION_ERROR", "SKU is required.")
        for field in ("unit_cost", "selling_price"):
            if field in data and data[field] not in (None, "") and Decimal(str(data[field])) < 0:
                raise ServiceOSException("VALIDATION_ERROR", f"{field.replace('_', ' ').title()} cannot be negative.")
        if "min_quantity" in data and data["min_quantity"] is not None and int(data["min_quantity"]) < 0:
            raise ServiceOSException("VALIDATION_ERROR", "Reorder level cannot be negative.")
        if "gst" in data and data["gst"] not in (None, ""):
            gst = Decimal(str(data["gst"]))
            if gst < 0 or gst > 100:
                raise ServiceOSException("VALIDATION_ERROR", "GST must be between 0 and 100 percent.")

    @staticmethod
    def _item_dict(item: InventoryItem, quantity: int = 0, reserved: int = 0) -> dict:
        available = quantity - reserved
        sell = item.selling_price if item.selling_price is not None else item.unit_cost
        return {
            "item_id": str(item.id), "name": item.name, "sku": item.sku,
            "category": item.category,
            "service_group_id": str(item.service_group_id) if item.service_group_id else None,
            "unit": item.unit, "unit_cost": float(item.unit_cost),
            "selling_price": float(sell), "min_quantity": item.min_quantity,
            "gst": float(item.gst) if item.gst is not None else None,
            "warranty": item.warranty, "is_active": item.is_active,
            "status": item.status, "quantity": int(quantity),
            "reserved_qty": int(reserved), "available_qty": int(available),
            "below_minimum": available < item.min_quantity,
            "inventory_value": float(item.unit_cost * quantity),
            "retail_value": float(sell * available),
            "margin": float(sell - item.unit_cost),
        }

    # PROVEN LEVEL 5: SELECT FOR UPDATE on balance row
    async def _get_balance_locked(self, item_id: uuid.UUID,
                                   location_id: uuid.UUID) -> StockBalance:
        try:
            r = await self.db.execute(
                select(StockBalance).where(
                    StockBalance.item_id == item_id,
                    StockBalance.location_id == location_id,
                ).with_for_update(nowait=True)
            )
            bal = r.scalar_one_or_none()
            if not bal:
                item = await self.db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
                it = item.scalar_one_or_none()
                if not it: raise NotFoundException("InventoryItem", str(item_id))
                bal = StockBalance(item_id=item_id, location_id=location_id,
                                    tenant_id=it.tenant_id)
                self.db.add(bal); await self.db.flush()
            return bal
        except ServiceOSException: raise
        except Exception as e:
            if "lock" in str(e).lower():
                raise ServiceOSException("CONFLICT",
                    "Stock is being updated by another transaction. Retry in 1 second.",
                    context={"retry_after_seconds": 1})
            raise

    # PROVEN LEVEL 5: reconcile on every read
    async def _reconcile(self, item_id: uuid.UUID, location_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(func.sum(StockTransaction.quantity)).where(
                StockTransaction.item_id == item_id,
                StockTransaction.location_id == location_id,
            ))
        ledger_sum = r.scalar_one_or_none() or 0
        bal_r = await self.db.execute(select(StockBalance).where(
            StockBalance.item_id == item_id, StockBalance.location_id == location_id))
        bal = bal_r.scalar_one_or_none()
        cached = bal.quantity if bal else 0
        mismatch = ledger_sum != cached
        if mismatch:
            logger.critical("inventory.reconciliation_error",
                            item_id=str(item_id), location_id=str(location_id),
                            ledger=ledger_sum, cached=cached)
        return {"matches": not mismatch, "ledger_sum": ledger_sum, "cached": cached}

    async def _write_txn(self, item_id: uuid.UUID, location_id: uuid.UUID, tenant_id: uuid.UUID,
                          txn_type: str, quantity: int, bal: StockBalance,
                          job_id: str | None, reference_id: str | None,
                          idempotency_key: str | None, notes: str | None) -> StockTransaction:
        if idempotency_key:
            ex = await self.db.execute(select(StockTransaction).where(
                StockTransaction.idempotency_key == idempotency_key))
            existing = ex.scalar_one_or_none()
            if existing:
                return existing

        balance_before = bal.quantity
        bal.quantity += quantity
        bal.last_txn_at = utcnow()

        txn = StockTransaction(
            item_id=item_id, location_id=location_id, tenant_id=tenant_id,
            txn_type=txn_type, quantity=quantity,
            balance_before=balance_before, balance_after=bal.quantity,
            job_id=job_id, reference_id=reference_id,
            idempotency_key=idempotency_key, notes=notes, actor_id=self.actor_id,
        )
        self.db.add(txn)
        return txn

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="inventory",
                tenant_id=tenant_id, entity_type="inventory", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception: pass

    # Item CRUD
    async def create_item(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        self._validate_item_data(data)
        duplicate = (await self.db.execute(select(InventoryItem.id).where(
            InventoryItem.tenant_id == tenant_id,
            func.lower(InventoryItem.sku) == str(data["sku"]).strip().lower(),
        ))).scalar_one_or_none()
        if duplicate:
            raise ServiceOSException("CONFLICT", "This SKU already exists. Restore the archived item or use a unique SKU.")
        service_group_id, category = await self._resolve_service_group(tenant_id, data)
        item = InventoryItem(tenant_id=tenant_id, name=data["name"].strip(), sku=data["sku"].strip(),
            category=category, service_group_id=service_group_id, unit=data.get("unit","unit"),
            unit_cost=Decimal(str(data.get("unit_cost","0"))),
            selling_price=Decimal(str(data.get("selling_price", data.get("unit_cost", "0")))),
            min_quantity=data.get("min_quantity",5),
            gst=Decimal(str(data["gst"])) if data.get("gst") not in (None, "") else None,
            warranty=data.get("warranty"))
        self.db.add(item); await self.db.flush()
        return self._item_dict(item)

    async def get_item(self, item_id: uuid.UUID) -> dict:
        item = await self._require_item(item_id)
        totals = (await self.db.execute(select(
            func.coalesce(func.sum(StockBalance.quantity), 0),
            func.coalesce(func.sum(StockBalance.reserved_qty), 0),
        ).where(StockBalance.item_id == item_id, StockBalance.tenant_id == item.tenant_id))).one()
        return self._item_dict(item, int(totals[0]), int(totals[1]))

    async def update_item(self, item_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.tenant_id == tenant_id))
        item = r.scalar_one_or_none()
        if not item: raise NotFoundException("InventoryItem", str(item_id))
        self._validate_item_data(data, partial=True)
        if data.get("sku"):
            duplicate = (await self.db.execute(select(InventoryItem.id).where(
                InventoryItem.tenant_id == tenant_id,
                InventoryItem.id != item_id,
                func.lower(InventoryItem.sku) == str(data["sku"]).strip().lower(),
            ))).scalar_one_or_none()
            if duplicate:
                raise ServiceOSException("CONFLICT", "This SKU is already used by another item.")
        for field in ("name", "sku", "category", "unit"):
            if field in data and data[field] is not None:
                setattr(item, field, data[field])
        if "unit_cost" in data and data["unit_cost"] is not None:
            item.unit_cost = Decimal(str(data["unit_cost"]))
        if "selling_price" in data and data["selling_price"] is not None:
            item.selling_price = Decimal(str(data["selling_price"]))
        if "min_quantity" in data and data["min_quantity"] is not None:
            item.min_quantity = data["min_quantity"]
        if "gst" in data:
            item.gst = Decimal(str(data["gst"])) if data["gst"] not in (None, "") else None
        if "warranty" in data:
            item.warranty = data["warranty"]
        if "is_active" in data:
            item.is_active = bool(data["is_active"])
        if "service_group_id" in data or "category" in data:
            item.service_group_id, item.category = await self._resolve_service_group(tenant_id, data)
        await self.db.flush()
        return self._item_dict(item)

    async def delete_item(self, item_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.tenant_id == tenant_id))
        item = r.scalar_one_or_none()
        if not item: raise NotFoundException("InventoryItem", str(item_id))
        item.is_active = False
        await self.db.flush()
        return {"item_id": str(item.id), "deleted": True}

    async def list_items(self, tenant_id: uuid.UUID, limit: int, cursor: str | None,
                         search: str | None = None, category_id: uuid.UUID | None = None,
                         stock_status: str = "all", sort: str = "name_asc",
                         offset: int = 0, include_archived: bool = False) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        stock = select(
            StockBalance.item_id.label("item_id"),
            func.coalesce(func.sum(StockBalance.quantity), 0).label("quantity"),
            func.coalesce(func.sum(StockBalance.reserved_qty), 0).label("reserved"),
        ).where(StockBalance.tenant_id == tenant_id).group_by(StockBalance.item_id).subquery()
        quantity = func.coalesce(stock.c.quantity, 0)
        reserved = func.coalesce(stock.c.reserved, 0)
        available = quantity - reserved
        filters = [InventoryItem.tenant_id == tenant_id, InventoryItem.status == "published"]
        filters.append(InventoryItem.is_active == (False if include_archived else True))
        if search:
            term = f"%{search.strip()}%"
            filters.append(or_(InventoryItem.name.ilike(term), InventoryItem.sku.ilike(term),
                               InventoryItem.category.ilike(term)))
        if category_id:
            filters.append(InventoryItem.service_group_id == category_id)
        if stock_status == "low":
            filters.append(available < InventoryItem.min_quantity)
        elif stock_status == "out":
            filters.append(available <= 0)
        elif stock_status == "healthy":
            filters.append(available >= InventoryItem.min_quantity)
        q = select(InventoryItem, quantity, reserved).outerjoin(
            stock, stock.c.item_id == InventoryItem.id).where(*filters)
        order = {
            "name_desc": desc(InventoryItem.name),
            "stock_asc": asc(available), "stock_desc": desc(available),
            "value_desc": desc(InventoryItem.unit_cost * quantity),
        }.get(sort, asc(InventoryItem.name))
        q = q.order_by(order, InventoryItem.id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(InventoryItem.name > c["name"])
            except Exception: pass
        total = int((await self.db.execute(select(func.count()).select_from(
            select(InventoryItem.id).outerjoin(stock, stock.c.item_id == InventoryItem.id)
            .where(*filters).subquery()))).scalar_one())
        q = q.offset(offset).limit(limit + 1)
        r = await self.db.execute(q)
        rows = r.all()
        items = rows
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"name": items[-1][0].name}) if has_next and items else None
        return {"items": [self._item_dict(i, int(qty), int(res)) for i, qty, res in items],
                "total": total, "offset": offset, "limit": limit,
                "has_next": has_next, "next_cursor": nc}

    async def workspace_summary(self, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        stock = select(
            StockBalance.item_id,
            func.coalesce(func.sum(StockBalance.quantity), 0).label("quantity"),
            func.coalesce(func.sum(StockBalance.reserved_qty), 0).label("reserved"),
        ).where(StockBalance.tenant_id == tenant_id).group_by(StockBalance.item_id).subquery()
        rows = (await self.db.execute(select(
            InventoryItem.unit_cost, InventoryItem.selling_price, InventoryItem.min_quantity,
            func.coalesce(stock.c.quantity, 0), func.coalesce(stock.c.reserved, 0),
        ).outerjoin(stock, stock.c.item_id == InventoryItem.id).where(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active == True,
            InventoryItem.status == "published",
        ))).all()
        on_hand = sum(int(r[3]) for r in rows)
        reserved = sum(int(r[4]) for r in rows)
        low = sum(1 for r in rows if int(r[3]) - int(r[4]) < int(r[2]))
        cost_value = sum(Decimal(r[0]) * int(r[3]) for r in rows)
        retail_value = sum(Decimal(r[1] if r[1] is not None else r[0]) * max(0, int(r[3]) - int(r[4])) for r in rows)
        locations = int((await self.db.execute(select(func.count(StockLocation.id)).where(
            StockLocation.tenant_id == tenant_id, StockLocation.is_active == True))).scalar_one())
        return {"total_items": len(rows), "on_hand_units": on_hand, "reserved_units": reserved,
                "available_units": on_hand - reserved, "low_stock_items": low,
                "inventory_value": float(cost_value), "retail_value": float(retail_value),
                "active_locations": locations}

    async def list_locations(self, tenant_id: uuid.UUID, include_archived: bool = False) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        q = select(StockLocation).where(StockLocation.tenant_id == tenant_id)
        if not include_archived:
            q = q.where(StockLocation.is_active == True)
        locations = (await self.db.execute(q.order_by(StockLocation.location_name))).scalars().all()
        return {"locations": [{"location_id": str(x.id), "location_name": x.location_name,
                 "location_type": x.location_type, "staff_id": str(x.staff_id) if x.staff_id else None,
                 "is_active": x.is_active} for x in locations], "total": len(locations)}

    async def create_location(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        name = str(data.get("location_name") or "").strip()
        kind = str(data.get("location_type") or "warehouse").strip().lower()
        if not name or kind not in {"warehouse", "store", "van", "technician"}:
            raise ServiceOSException("VALIDATION_ERROR", "Enter a location name and valid location type.")
        duplicate = (await self.db.execute(select(StockLocation.id).where(
            StockLocation.tenant_id == tenant_id,
            func.lower(StockLocation.location_name) == name.lower(),
            StockLocation.location_type == kind,
        ))).scalar_one_or_none()
        if duplicate:
            raise ServiceOSException("CONFLICT", "A stock location with this name and type already exists.")
        staff_id = uuid.UUID(str(data["staff_id"])) if data.get("staff_id") else None
        location = StockLocation(tenant_id=tenant_id, location_name=name,
                                 location_type=kind, staff_id=staff_id)
        self.db.add(location); await self.db.flush()
        return {"location_id": str(location.id), "location_name": name,
                "location_type": kind, "staff_id": str(staff_id) if staff_id else None,
                "is_active": True}

    async def update_location(self, tenant_id: uuid.UUID, location_id: uuid.UUID, data: dict) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        location = await self._require_location(location_id, tenant_id, active_only=False)
        if "location_name" in data:
            if not str(data["location_name"] or "").strip():
                raise ServiceOSException("VALIDATION_ERROR", "Location name is required.")
            location.location_name = str(data["location_name"]).strip()
        if "is_active" in data:
            location.is_active = bool(data["is_active"])
        await self.db.flush()
        return {"location_id": str(location.id), "location_name": location.location_name,
                "location_type": location.location_type, "is_active": location.is_active}

    # Stock operations
    async def receive_stock(self, item_id: uuid.UUID, location_id: uuid.UUID,
                             tenant_id: uuid.UUID, quantity: int,
                             unit_cost: Decimal | None, reference_id: str | None,
                             notes: str | None) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        if quantity <= 0:
            raise ServiceOSException("VALIDATION_ERROR", "Quantity must be positive for receipt.")
        await self._require_item(item_id, tenant_id, active_only=True)
        await self._require_location(location_id, tenant_id)
        bal = await self._get_balance_locked(item_id, location_id)
        txn = await self._write_txn(item_id, location_id, tenant_id,
                                     StockTxnType.RECEIPT, quantity, bal,
                                     None, reference_id, None, notes)
        await self.db.flush()
        return {"item_id": str(item_id), "quantity_received": quantity,
                "new_balance": bal.quantity, "txn_id": str(txn.id)}

    async def count_stock(self, item_id: uuid.UUID, location_id: uuid.UUID,
                          tenant_id: uuid.UUID, counted_quantity: int,
                          reason: str, idempotency_key: str | None = None) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        if counted_quantity < 0 or not str(reason or "").strip():
            raise ServiceOSException("VALIDATION_ERROR", "Enter a non-negative count and a reason.")
        await self._require_item(item_id, tenant_id, active_only=True)
        await self._require_location(location_id, tenant_id)
        bal = await self._get_balance_locked(item_id, location_id)
        if counted_quantity < bal.reserved_qty:
            raise ServiceOSException(
                "CONFLICT",
                f"Count cannot be below {bal.reserved_qty} units reserved for active jobs.",
                context={"reserved_qty": bal.reserved_qty, "counted_quantity": counted_quantity},
            )
        delta = counted_quantity - bal.quantity
        txn = await self._write_txn(item_id, location_id, tenant_id,
            StockTxnType.ADJUSTMENT, delta, bal, None, None, idempotency_key,
            f"Cycle count: {reason.strip()}")
        await self.db.flush()
        return {"item_id": str(item_id), "location_id": str(location_id),
                "previous_quantity": counted_quantity - delta,
                "counted_quantity": counted_quantity, "adjustment": delta,
                "txn_id": str(txn.id)}

    async def transfer_stock(self, item_id: uuid.UUID, from_location_id: uuid.UUID,
                             to_location_id: uuid.UUID, tenant_id: uuid.UUID,
                             quantity: int, reason: str,
                             idempotency_key: str | None = None) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        if from_location_id == to_location_id:
            raise ServiceOSException("VALIDATION_ERROR", "Source and destination must be different.")
        if quantity <= 0 or not str(reason or "").strip():
            raise ServiceOSException("VALIDATION_ERROR", "Enter a positive transfer quantity and a reason.")
        await self._require_item(item_id, tenant_id, active_only=True)
        await self._require_location(from_location_id, tenant_id)
        await self._require_location(to_location_id, tenant_id)
        # Always lock in UUID order so simultaneous opposite transfers cannot
        # deadlock each other.
        locked: dict[uuid.UUID, StockBalance] = {}
        for location_id in sorted((from_location_id, to_location_id), key=str):
            locked[location_id] = await self._get_balance_locked(item_id, location_id)
        source, destination = locked[from_location_id], locked[to_location_id]
        if idempotency_key:
            prior = (await self.db.execute(select(StockTransaction).where(
                StockTransaction.idempotency_key.in_((f"{idempotency_key}:out", f"{idempotency_key}:in"))
            ))).scalars().all()
            if len(prior) == 2:
                return {"item_id": str(item_id), "quantity": quantity,
                        "from_location_id": str(from_location_id), "to_location_id": str(to_location_id),
                        "source_balance": source.quantity, "destination_balance": destination.quantity,
                        "transaction_ids": [str(t.id) for t in prior], "idempotent": True}
            if prior:
                raise ServiceOSException("DATA_INTEGRITY_ERROR",
                    "A partial transfer ledger entry was detected. Contact support before retrying.")
        available = source.quantity - source.reserved_qty
        if available < quantity:
            raise ServiceOSException("CONFLICT",
                f"Insufficient available stock. Available: {available}, requested: {quantity}.",
                context={"available": available, "requested": quantity})
        reference = f"transfer:{from_location_id}:{to_location_id}"
        debit = await self._write_txn(item_id, from_location_id, tenant_id,
            StockTxnType.TRANSFER, -quantity, source, None, reference,
            f"{idempotency_key}:out" if idempotency_key else None,
            f"Transfer out: {reason.strip()}")
        credit = await self._write_txn(item_id, to_location_id, tenant_id,
            StockTxnType.TRANSFER, quantity, destination, None, reference,
            f"{idempotency_key}:in" if idempotency_key else None,
            f"Transfer in: {reason.strip()}")
        await self.db.flush()
        return {"item_id": str(item_id), "quantity": quantity,
                "from_location_id": str(from_location_id), "to_location_id": str(to_location_id),
                "source_balance": source.quantity, "destination_balance": destination.quantity,
                "transaction_ids": [str(debit.id), str(credit.id)]}

    async def get_stock_level(self, item_id: uuid.UUID, location_id: uuid.UUID) -> dict:
        item = await self._require_item(item_id, active_only=True)
        await self._require_location(location_id, item.tenant_id)
        rec = await self._reconcile(item_id, location_id)
        bal_r = await self.db.execute(select(StockBalance).where(
            StockBalance.item_id == item_id, StockBalance.location_id == location_id))
        bal = bal_r.scalar_one_or_none()
        quantity = bal.quantity if bal else 0
        min_qty = item.min_quantity
        return {"item_id": str(item_id), "location_id": str(location_id),
                "quantity": quantity, "reserved_qty": bal.reserved_qty if bal else 0,
                "available_qty": quantity - (bal.reserved_qty if bal else 0),
                "min_quantity": min_qty,
                "below_minimum": quantity < min_qty,
                "reconciliation_ok": rec["matches"]}

    async def list_stock_transactions(self, item_id: uuid.UUID, location_id: uuid.UUID,
                                       limit: int, cursor: str | None) -> dict:
        item = await self._require_item(item_id)
        await self._require_location(location_id, item.tenant_id, active_only=False)
        q = select(StockTransaction).where(
            StockTransaction.item_id == item_id,
            StockTransaction.location_id == location_id,
        ).order_by(StockTransaction.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(StockTransaction.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        txns = r.scalars().all()
        has_next = len(txns) > limit; txns = txns[:limit]
        nc = encode_cursor({"created_at": txns[-1].created_at.isoformat()}) if has_next and txns else None
        return {"transactions": [{"txn_id": str(t.id), "txn_type": t.txn_type,
                "quantity": t.quantity, "balance_before": t.balance_before,
                "balance_after": t.balance_after, "job_id": t.job_id,
                "notes": t.notes, "created_at": t.created_at.isoformat()} for t in txns],
                "has_next": has_next, "next_cursor": nc}

    # Reservations
    async def create_reservation(self, job_id: str, item_id: uuid.UUID, location_id: uuid.UUID,
                                  tenant_id: uuid.UUID, quantity: int) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        if quantity <= 0:
            raise ServiceOSException("VALIDATION_ERROR", "Reservation quantity must be positive.")
        await self._require_item(item_id, tenant_id, active_only=True)
        await self._require_location(location_id, tenant_id)
        existing = (await self.db.execute(select(StockReservation).where(
            StockReservation.job_id == job_id, StockReservation.item_id == item_id,
            StockReservation.location_id == location_id))).scalar_one_or_none()
        if existing:
            return {"reservation_id": str(existing.id), "job_id": job_id,
                    "quantity": existing.quantity, "status": existing.status,
                    "expires_at": existing.expires_at.isoformat()}
        bal = await self._get_balance_locked(item_id, location_id)
        available = bal.quantity - bal.reserved_qty
        if available < quantity:
            raise ServiceOSException("CONFLICT",
                f"Insufficient stock. Available: {available}, Requested: {quantity}",
                context={"available": available, "requested": quantity})
        bal.reserved_qty += quantity
        expires_at = utcnow() + timedelta(hours=RESERVATION_TTL_HOURS)
        res = StockReservation(job_id=job_id, item_id=item_id, location_id=location_id,
            tenant_id=tenant_id, quantity=quantity, expires_at=expires_at)
        self.db.add(res)
        # A reservation is a hold, not a physical stock movement.  Keeping the
        # ledger quantity at zero makes SUM(ledger) equal on-hand stock while
        # reserved_qty drives availability.
        await self._write_txn(item_id, location_id, tenant_id,
                               StockTxnType.RESERVATION, 0, bal, job_id, None,
                               f"reserve:{job_id}:{item_id}", f"Reserved for job {job_id}")
        await self.db.flush()
        return {"reservation_id": str(res.id), "job_id": job_id,
                "quantity": quantity, "expires_at": expires_at.isoformat()}

    async def confirm_reservation(self, job_id: str, item_id: uuid.UUID,
                                   location_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(StockReservation).where(
            StockReservation.job_id == job_id, StockReservation.item_id == item_id,
            StockReservation.location_id == location_id,
            StockReservation.tenant_id == tenant_id,
            StockReservation.status == ReservationStatus.ACTIVE))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("StockReservation", f"{job_id}:{item_id}")
        bal = await self._get_balance_locked(item_id, location_id)
        bal.reserved_qty = max(0, bal.reserved_qty - res.quantity)
        await self._write_txn(item_id, location_id, tenant_id,
                              StockTxnType.CONFIRMATION, -res.quantity, bal, job_id, None,
                              f"confirm:{job_id}:{item_id}", f"Consumed by job {job_id}")
        res.status = ReservationStatus.CONFIRMED; res.resolved_at = utcnow()
        await self.db.flush()
        return {"confirmed": True, "quantity": res.quantity, "job_id": job_id}

    async def release_reservation(self, job_id: str, item_id: uuid.UUID,
                                   location_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(StockReservation).where(
            StockReservation.job_id == job_id, StockReservation.item_id == item_id,
            StockReservation.location_id == location_id,
            StockReservation.tenant_id == tenant_id,
            StockReservation.status == ReservationStatus.ACTIVE))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("StockReservation", f"{job_id}:{item_id}")
        bal = await self._get_balance_locked(item_id, location_id)
        bal.reserved_qty = max(0, bal.reserved_qty - res.quantity)
        res.status = ReservationStatus.RELEASED; res.resolved_at = utcnow()
        await self._write_txn(item_id, location_id, tenant_id,
                               StockTxnType.RETURN, 0, bal, job_id, None,
                               f"release:{job_id}:{item_id}", f"Released for job {job_id}")
        await self.db.flush()
        return {"released": True, "quantity": res.quantity}

    async def list_below_minimum(self, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        stock = select(StockBalance.item_id,
            func.coalesce(func.sum(StockBalance.quantity), 0).label("quantity"),
            func.coalesce(func.sum(StockBalance.reserved_qty), 0).label("reserved"),
        ).where(StockBalance.tenant_id == tenant_id).group_by(StockBalance.item_id).subquery()
        available = func.coalesce(stock.c.quantity, 0) - func.coalesce(stock.c.reserved, 0)
        rows = (await self.db.execute(select(InventoryItem, available).outerjoin(
            stock, stock.c.item_id == InventoryItem.id).where(
            InventoryItem.tenant_id == tenant_id, InventoryItem.is_active == True,
            InventoryItem.status == "published", available < InventoryItem.min_quantity,
        ).order_by(available, InventoryItem.name))).all()
        return {"items": [{"item_id": str(item.id), "name": item.name,
                "current_qty": int(qty), "min_quantity": item.min_quantity,
                "deficit": item.min_quantity - int(qty)} for item, qty in rows],
                "total": len(rows)}

    async def request_replenishment(self, tenant_id: uuid.UUID, item_id: uuid.UUID,
                                     quantity: int) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        await self._publish("inventory.replenishment_requested", str(tenant_id), str(item_id),
                            {"quantity": quantity, "item_id": str(item_id)})
        return {"item_id": str(item_id), "quantity_requested": quantity,
                "status": "pending", "message": "Replenishment request logged."}
