"""Global Services — service layer.

Two responsibilities, deliberately kept separate from every other engine:
1. Admin CRUD over the promotional service cards.
2. Customer lead capture + admin lead-queue management.

No booking/job/payment machinery anywhere in this file -- a lead is
closed by an admin phone call, never by a status transition that implies
fulfillment happened.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.global_services.models import PlatformGlobalService, GlobalServiceLead, LEAD_STATUSES
from app.exceptions import NotFoundException, ServiceOSException


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


class GlobalServicesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Services (admin CRUD) ────────────────────────────────────────────────

    async def list_services(self, *, include_inactive: bool = True) -> list[dict]:
        q = select(PlatformGlobalService)
        if not include_inactive:
            q = q.where(PlatformGlobalService.is_active.is_(True))
        q = q.order_by(PlatformGlobalService.display_order, PlatformGlobalService.name)
        rows = (await self.db.execute(q)).scalars().all()
        return [r.to_dict() for r in rows]

    async def create_service(self, data: dict, *, actor_id: uuid.UUID | None) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("GLOBAL_SERVICE_NAME_REQUIRED", "Name is required.", status_code=422)
        svc = PlatformGlobalService(
            name=name,
            tagline=data.get("tagline"),
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            display_order=int(data.get("display_order", 0) or 0),
            is_active=bool(data.get("is_active", True)),
            created_by_user_id=actor_id,
        )
        self.db.add(svc)
        await self.db.flush()
        return svc.to_dict()

    async def update_service(self, service_id: uuid.UUID, data: dict) -> dict:
        svc = await self.db.get(PlatformGlobalService, service_id)
        if not svc:
            raise NotFoundException("PlatformGlobalService", str(service_id))
        for field in ("name", "tagline", "description", "icon_url", "display_order", "is_active"):
            if field in data:
                setattr(svc, field, data[field])
        await self.db.flush()
        return svc.to_dict()

    async def delete_service(self, service_id: uuid.UUID) -> dict:
        """Deactivate, never hard-delete -- existing leads keep referring to
        a real (if now-hidden) service."""
        svc = await self.db.get(PlatformGlobalService, service_id)
        if not svc:
            raise NotFoundException("PlatformGlobalService", str(service_id))
        svc.is_active = False
        await self.db.flush()
        return {"id": str(service_id), "is_active": False}

    # ── Leads ─────────────────────────────────────────────────────────────────

    async def create_lead(self, data: dict, *, customer_id: uuid.UUID | None) -> dict:
        service_id_raw = data.get("global_service_id")
        if not service_id_raw:
            raise ServiceOSException("GLOBAL_SERVICE_ID_REQUIRED", "global_service_id is required.", status_code=422)
        service_id = uuid.UUID(str(service_id_raw))
        svc = await self.db.get(PlatformGlobalService, service_id)
        if not svc or not svc.is_active:
            raise NotFoundException("PlatformGlobalService", str(service_id))

        name = (data.get("name") or "").strip()
        phone = (data.get("phone") or "").strip()
        if not name or not phone:
            raise ServiceOSException("GLOBAL_SERVICE_LEAD_FIELDS_REQUIRED",
                                     "name and phone are required.", status_code=422)

        lead = GlobalServiceLead(
            global_service_id=service_id,
            customer_id=customer_id,
            name=name, phone=phone,
            email=data.get("email"),
            zipcode=data.get("zipcode"),
            message=data.get("message"),
            status="new",
        )
        self.db.add(lead)
        await self.db.flush()
        return lead.to_dict()

    async def list_leads(self, *, status: str | None = None, global_service_id: uuid.UUID | None = None,
                         page: int = 1, page_size: int = 25) -> dict:
        page_size = min(page_size, 100)
        offset = (page - 1) * page_size
        q = select(GlobalServiceLead)
        if status:
            q = q.where(GlobalServiceLead.status == status)
        if global_service_id:
            q = q.where(GlobalServiceLead.global_service_id == global_service_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(GlobalServiceLead.created_at.desc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        # Attach the service name so the admin queue doesn't need a second
        # round trip per row.
        service_ids = {r.global_service_id for r in rows}
        names: dict[uuid.UUID, str] = {}
        if service_ids:
            svc_rows = (await self.db.execute(
                select(PlatformGlobalService.id, PlatformGlobalService.name)
                .where(PlatformGlobalService.id.in_(service_ids))
            )).all()
            names = {sid: sname for sid, sname in svc_rows}

        items = []
        for r in rows:
            d = r.to_dict()
            d["global_service_name"] = names.get(r.global_service_id, "—")
            items.append(d)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_lead(self, lead_id: uuid.UUID, data: dict, *, actor_id: uuid.UUID | None) -> dict:
        lead = await self.db.get(GlobalServiceLead, lead_id)
        if not lead:
            raise NotFoundException("GlobalServiceLead", str(lead_id))
        if "status" in data:
            new_status = data["status"]
            if new_status not in LEAD_STATUSES:
                raise ServiceOSException("INVALID_LEAD_STATUS",
                                         f"status must be one of {sorted(LEAD_STATUSES)}.", status_code=422)
            lead.status = new_status
            if new_status == "contacted" and lead.contacted_at is None:
                lead.contacted_at = _now()
                lead.assigned_admin_id = actor_id
            if new_status == "closed":
                lead.closed_at = _now()
        if "admin_notes" in data:
            lead.admin_notes = data["admin_notes"]
        await self.db.flush()
        return lead.to_dict()

    async def summary(self) -> dict:
        rows = (await self.db.execute(
            select(GlobalServiceLead.status, func.count()).group_by(GlobalServiceLead.status)
        )).all()
        counts = {status: count for status, count in rows}
        return {
            "new": counts.get("new", 0),
            "contacted": counts.get("contacted", 0),
            "converted": counts.get("converted", 0),
            "closed": counts.get("closed", 0),
            "total": sum(counts.values()),
        }
