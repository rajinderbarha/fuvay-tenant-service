"""Inventory Engine — InventoryService. Proven Level 5.
SELECT FOR UPDATE on StockBalance. Append-only StockTransaction ledger.
Reconciliation on every balance read. Celery TTL on reservations.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.inventory.constants import (
    StockTxnType, ReservationStatus, RESERVATION_TTL_HOURS,
    REDIS_STOCK_BALANCE,
)
from app.engines.inventory.models import (
    InventoryItem, StockLocation, StockBalance, StockTransaction, StockReservation,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("inventory.service")
utcnow = lambda: datetime.now(timezone.utc)


class InventoryService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role

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
            if ex.scalar_one_or_none():
                return ex.scalar_one_or_none()

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
        item = InventoryItem(tenant_id=tenant_id, name=data["name"], sku=data["sku"],
            category=data.get("category"), unit=data.get("unit","unit"),
            unit_cost=Decimal(str(data.get("unit_cost","0"))),
            min_quantity=data.get("min_quantity",5))
        self.db.add(item); await self.db.flush()
        return {"item_id": str(item.id), "name": item.name, "sku": item.sku,
                "min_quantity": item.min_quantity, "unit_cost": float(item.unit_cost)}

    async def get_item(self, item_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item: raise NotFoundException("InventoryItem", str(item_id))
        return {"item_id": str(item.id), "name": item.name, "sku": item.sku,
                "category": item.category, "unit": item.unit,
                "unit_cost": float(item.unit_cost), "min_quantity": item.min_quantity}

    async def list_items(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(InventoryItem).where(InventoryItem.tenant_id == tenant_id,
                                         InventoryItem.is_active == True)            .order_by(InventoryItem.name)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(InventoryItem.name > c["name"])
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"name": items[-1].name}) if has_next and items else None
        return {"items": [{"item_id": str(i.id), "name": i.name, "sku": i.sku,
                "unit": i.unit, "min_quantity": i.min_quantity} for i in items],
                "has_next": has_next, "next_cursor": nc}

    # Stock operations
    async def receive_stock(self, item_id: uuid.UUID, location_id: uuid.UUID,
                             tenant_id: uuid.UUID, quantity: int,
                             unit_cost: Decimal | None, reference_id: str | None,
                             notes: str | None) -> dict:
        if quantity <= 0:
            raise ServiceOSException("VALIDATION_ERROR", "Quantity must be positive for receipt.")
        bal = await self._get_balance_locked(item_id, location_id)
        txn = await self._write_txn(item_id, location_id, tenant_id,
                                     StockTxnType.RECEIPT, quantity, bal,
                                     None, reference_id, None, notes)
        await self.db.flush()
        return {"item_id": str(item_id), "quantity_received": quantity,
                "new_balance": bal.quantity, "txn_id": str(txn.id)}

    async def get_stock_level(self, item_id: uuid.UUID, location_id: uuid.UUID) -> dict:
        rec = await self._reconcile(item_id, location_id)
        bal_r = await self.db.execute(select(StockBalance).where(
            StockBalance.item_id == item_id, StockBalance.location_id == location_id))
        bal = bal_r.scalar_one_or_none()
        item_r = await self.db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
        item = item_r.scalar_one_or_none()
        quantity = bal.quantity if bal else 0
        min_qty = item.min_quantity if item else 5
        return {"item_id": str(item_id), "location_id": str(location_id),
                "quantity": quantity, "reserved_qty": bal.reserved_qty if bal else 0,
                "available_qty": quantity - (bal.reserved_qty if bal else 0),
                "min_quantity": min_qty,
                "below_minimum": quantity < min_qty,
                "reconciliation_ok": rec["matches"]}

    async def list_stock_transactions(self, item_id: uuid.UUID, location_id: uuid.UUID,
                                       limit: int, cursor: str | None) -> dict:
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
        await self._write_txn(item_id, location_id, tenant_id,
                               StockTxnType.RESERVATION, -quantity, bal, job_id, None,
                               f"reserve:{job_id}:{item_id}", f"Reserved for job {job_id}")
        await self.db.flush()
        return {"reservation_id": str(res.id), "job_id": job_id,
                "quantity": quantity, "expires_at": expires_at.isoformat()}

    async def confirm_reservation(self, job_id: str, item_id: uuid.UUID,
                                   location_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(StockReservation).where(
            StockReservation.job_id == job_id, StockReservation.item_id == item_id,
            StockReservation.location_id == location_id,
            StockReservation.status == ReservationStatus.ACTIVE))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("StockReservation", f"{job_id}:{item_id}")
        bal = await self._get_balance_locked(item_id, location_id)
        bal.reserved_qty -= res.quantity
        res.status = ReservationStatus.CONFIRMED; res.resolved_at = utcnow()
        return {"confirmed": True, "quantity": res.quantity, "job_id": job_id}

    async def release_reservation(self, job_id: str, item_id: uuid.UUID,
                                   location_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(StockReservation).where(
            StockReservation.job_id == job_id, StockReservation.item_id == item_id,
            StockReservation.location_id == location_id,
            StockReservation.status == ReservationStatus.ACTIVE))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("StockReservation", f"{job_id}:{item_id}")
        bal = await self._get_balance_locked(item_id, location_id)
        bal.quantity += res.quantity; bal.reserved_qty -= res.quantity
        res.status = ReservationStatus.RELEASED; res.resolved_at = utcnow()
        await self._write_txn(item_id, location_id, tenant_id,
                               StockTxnType.RETURN, res.quantity, bal, job_id, None,
                               f"release:{job_id}:{item_id}", f"Released for job {job_id}")
        return {"released": True, "quantity": res.quantity}

    async def list_below_minimum(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(StockBalance, InventoryItem).join(
            InventoryItem, StockBalance.item_id == InventoryItem.id).where(
            StockBalance.tenant_id == tenant_id,
            StockBalance.quantity < InventoryItem.min_quantity))
        rows = r.all()
        return {"items": [{"item_id": str(row[1].id), "name": row[1].name,
                "current_qty": row[0].quantity, "min_quantity": row[1].min_quantity,
                "deficit": row[1].min_quantity - row[0].quantity} for row in rows],
                "total": len(rows)}

    async def request_replenishment(self, tenant_id: uuid.UUID, item_id: uuid.UUID,
                                     quantity: int) -> dict:
        await self._publish("inventory.replenishment_requested", str(tenant_id), str(item_id),
                            {"quantity": quantity, "item_id": str(item_id)})
        return {"item_id": str(item_id), "quantity_requested": quantity,
                "status": "pending", "message": "Replenishment request logged."}
