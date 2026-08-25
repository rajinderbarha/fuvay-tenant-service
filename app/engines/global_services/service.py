from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.global_services.models import GlobalServiceLead, LEAD_STATUSES, PlatformGlobalService
from app.exceptions import NotFoundException, ServiceOSException


class GlobalServicesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_services(self, *, include_inactive: bool = True) -> list[dict]:
        query = select(PlatformGlobalService)
        if not include_inactive:
            query = query.where(PlatformGlobalService.is_active.is_(True))
        rows = (await self.db.execute(
            query.order_by(PlatformGlobalService.display_order, PlatformGlobalService.name)
        )).scalars().all()
        return [row.to_dict() for row in rows]

    async def create_service(self, data: dict, *, actor_id: uuid.UUID | None) -> dict:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("GLOBAL_SERVICE_NAME_REQUIRED", "Name is required.", status_code=422)
        service = PlatformGlobalService(
            name=name,
            tagline=data.get("tagline"),
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            display_order=int(data.get("display_order", 0) or 0),
            is_active=bool(data.get("is_active", True)),
            created_by_user_id=actor_id,
        )
        self.db.add(service)
        await self.db.flush()
        return service.to_dict()

    async def update_service(self, service_id: uuid.UUID, data: dict) -> dict:
        service = await self.db.get(PlatformGlobalService, service_id)
        if not service:
            raise NotFoundException("PlatformGlobalService", str(service_id))
        for field in ("name", "tagline", "description", "icon_url", "display_order", "is_active"):
            if field in data:
                setattr(service, field, data[field])
        await self.db.flush()
        return service.to_dict()

    async def deactivate_service(self, service_id: uuid.UUID) -> dict:
        service = await self.db.get(PlatformGlobalService, service_id)
        if not service:
            raise NotFoundException("PlatformGlobalService", str(service_id))
        service.is_active = False
        await self.db.flush()
        return {"id": str(service_id), "is_active": False}

    async def create_lead(self, data: dict, *, customer_id: uuid.UUID | None) -> dict:
        try:
            service_id = uuid.UUID(str(data.get("global_service_id")))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ServiceOSException(
                "GLOBAL_SERVICE_ID_REQUIRED", "A valid global_service_id is required.", status_code=422
            ) from exc
        service = await self.db.get(PlatformGlobalService, service_id)
        if not service or not service.is_active:
            raise NotFoundException("PlatformGlobalService", str(service_id))

        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        if not name or not phone:
            raise ServiceOSException(
                "GLOBAL_SERVICE_LEAD_FIELDS_REQUIRED", "Name and phone are required.", status_code=422
            )
        lead = GlobalServiceLead(
            global_service_id=service_id,
            customer_id=customer_id,
            name=name,
            phone=phone,
            email=(str(data.get("email") or "").strip() or None),
            zipcode=(str(data.get("zipcode") or "").strip() or None),
            message=(str(data.get("message") or "").strip() or None),
            status="new",
        )
        self.db.add(lead)
        await self.db.flush()
        return lead.to_dict()

    async def list_leads(
        self,
        *,
        status: str | None = None,
        global_service_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        page_size = min(max(page_size, 1), 100)
        query = select(GlobalServiceLead)
        if status:
            if status not in LEAD_STATUSES:
                raise ServiceOSException("INVALID_LEAD_STATUS", "Invalid lead status.", status_code=422)
            query = query.where(GlobalServiceLead.status == status)
        if global_service_id:
            query = query.where(GlobalServiceLead.global_service_id == global_service_id)
        total = (await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await self.db.execute(
            query.order_by(GlobalServiceLead.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).scalars().all()
        service_ids = {row.global_service_id for row in rows}
        names: dict[uuid.UUID, str] = {}
        if service_ids:
            names = dict((await self.db.execute(
                select(PlatformGlobalService.id, PlatformGlobalService.name)
                .where(PlatformGlobalService.id.in_(service_ids))
            )).all())
        items = []
        for row in rows:
            item = row.to_dict()
            item["global_service_name"] = names.get(row.global_service_id, "Unavailable service")
            items.append(item)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_lead(self, lead_id: uuid.UUID, data: dict, *, actor_id: uuid.UUID | None) -> dict:
        lead = await self.db.get(GlobalServiceLead, lead_id)
        if not lead:
            raise NotFoundException("GlobalServiceLead", str(lead_id))
        if "status" in data:
            status = str(data["status"])
            if status not in LEAD_STATUSES:
                raise ServiceOSException("INVALID_LEAD_STATUS", "Invalid lead status.", status_code=422)
            lead.status = status
            now = datetime.now(timezone.utc)
            if status == "contacted" and lead.contacted_at is None:
                lead.contacted_at = now
                lead.assigned_admin_id = actor_id
            if status == "closed":
                lead.closed_at = now
        if "admin_notes" in data:
            lead.admin_notes = data["admin_notes"]
        await self.db.flush()
        return lead.to_dict()

    async def summary(self) -> dict:
        rows = (await self.db.execute(
            select(GlobalServiceLead.status, func.count()).group_by(GlobalServiceLead.status)
        )).all()
        counts = {status: int(count) for status, count in rows}
        return {
            "new": counts.get("new", 0),
            "contacted": counts.get("contacted", 0),
            "converted": counts.get("converted", 0),
            "closed": counts.get("closed", 0),
            "total": sum(counts.values()),
        }
