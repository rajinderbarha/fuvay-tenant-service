"""Field Ops Engine — Step 8: Service Checklist Template CRUD.
Tenant-owned templates (per catalog service) + their line items. Separate from
FieldOpsService since this is catalog-style management, not job execution."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.field_ops.models import ServiceChecklistTemplate, ServiceChecklistItem
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)


class ChecklistTemplateService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None, actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.actor_id = actor_id; self.actor_role = actor_role; self.actor_tenant_id = actor_tenant_id

    def _template_dict(self, t: ServiceChecklistTemplate) -> dict:
        return {
            "template_id": str(t.id), "tenant_id": str(t.tenant_id), "service_id": str(t.service_id),
            "name": t.name, "description": t.description, "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    def _item_dict(self, i: ServiceChecklistItem) -> dict:
        return {
            "item_id": str(i.id), "template_id": str(i.template_id), "title": i.title,
            "description": i.description, "sort_order": i.sort_order,
            "is_required": i.is_required, "requires_photo": i.requires_photo,
            "requires_note": i.requires_note, "is_active": i.is_active,
        }

    async def _get_template_for_tenant(self, template_id: uuid.UUID) -> ServiceChecklistTemplate:
        r = await self.db.execute(select(ServiceChecklistTemplate).where(
            ServiceChecklistTemplate.id == template_id))
        t = r.scalar_one_or_none()
        if not t or t.deleted_at is not None:
            raise ServiceOSException("CHECKLIST_TEMPLATE_NOT_FOUND",
                f"Checklist template '{template_id}' not found.", status_code=404)
        # Slice 2F-13: the tenant-ownership check previously fired ONLY when
        # actor_role == "tenant_owner". FIELD_OPS_CHECKLIST_MANAGE is
        # tenant_owner-only by default role grant, but a `staff` member can be
        # granted it via a StaffPermission override -- in which case the old
        # condition skipped the tenant filter entirely, letting that staff
        # member read/update/delete ANY tenant's template by ID (cross-tenant
        # IDOR). Fixed to enforce tenant ownership for every tenant-scoped
        # actor (i.e. anyone except super_admin, who is the intentional
        # platform-wide exemption). Same fail-closed NOT_FOUND response, so no
        # foreign-record existence is leaked.
        if (self.actor_role != "super_admin" and self.actor_tenant_id is not None
                and t.tenant_id != self.actor_tenant_id):
            raise ServiceOSException("CHECKLIST_TEMPLATE_NOT_FOUND",
                f"Checklist template '{template_id}' not found.", status_code=404)
        return t

    # ── Templates ──────────────────────────────────────────────────────────────
    async def create_template(self, tenant_id: uuid.UUID, data: dict) -> dict:
        if not data.get("service_id"):
            raise ServiceOSException("VALIDATION_ERROR", "service_id is required.", status_code=422)
        if not data.get("name") or not data["name"].strip():
            raise ServiceOSException("VALIDATION_ERROR", "name is required.", status_code=422)

        existing = await self.db.execute(select(ServiceChecklistTemplate).where(
            ServiceChecklistTemplate.tenant_id == tenant_id,
            ServiceChecklistTemplate.service_id == uuid.UUID(str(data["service_id"])),
            ServiceChecklistTemplate.name == data["name"].strip(),
            ServiceChecklistTemplate.is_active.is_(True),
            ServiceChecklistTemplate.deleted_at.is_(None)))
        if existing.scalar_one_or_none():
            raise ServiceOSException("CONFLICT",
                "An active template with this name already exists for this service.", status_code=409)

        t = ServiceChecklistTemplate(
            tenant_id=tenant_id, service_id=uuid.UUID(str(data["service_id"])),
            name=data["name"].strip(), description=data.get("description"),
            is_active=data.get("is_active", True),
        )
        self.db.add(t)
        await self.db.flush()
        return self._template_dict(t)

    async def list_templates(self, tenant_id: uuid.UUID, service_id: uuid.UUID | None = None) -> dict:
        q = select(ServiceChecklistTemplate).where(
            ServiceChecklistTemplate.tenant_id == tenant_id,
            ServiceChecklistTemplate.deleted_at.is_(None)).order_by(
            ServiceChecklistTemplate.created_at.desc())
        if service_id:
            q = q.where(ServiceChecklistTemplate.service_id == service_id)
        r = await self.db.execute(q)
        templates = r.scalars().all()
        return {"templates": [self._template_dict(t) for t in templates]}

    async def get_template(self, template_id: uuid.UUID) -> dict:
        t = await self._get_template_for_tenant(template_id)
        items = await self._list_items_unchecked(template_id)  # ownership already verified above
        return {**self._template_dict(t), "items": items["items"]}

    async def update_template(self, template_id: uuid.UUID, data: dict) -> dict:
        t = await self._get_template_for_tenant(template_id)
        if "name" in data and data["name"]:
            t.name = data["name"].strip()
        if "description" in data:
            t.description = data["description"]
        if "is_active" in data:
            t.is_active = bool(data["is_active"])
        return self._template_dict(t)

    async def delete_template(self, template_id: uuid.UUID) -> dict:
        """Soft delete — historical job_checklist_items are never touched."""
        t = await self._get_template_for_tenant(template_id)
        t.is_active = False
        t.deleted_at = utcnow()
        return {"template_id": str(t.id), "deleted": True}

    # ── Items ──────────────────────────────────────────────────────────────────
    async def list_items(self, template_id: uuid.UUID) -> dict:
        # Slice 2F-13: the standalone GET /{template_id}/items route reached
        # this method WITHOUT any tenant-ownership check, letting a caller
        # read another tenant's template item titles by supplying a foreign
        # template_id (cross-tenant read IDOR). Enforce ownership here (the
        # route-facing entry point); callers that have already verified
        # ownership use _list_items_unchecked to avoid a redundant fetch.
        await self._get_template_for_tenant(template_id)
        return await self._list_items_unchecked(template_id)

    async def _list_items_unchecked(self, template_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ServiceChecklistItem).where(
            ServiceChecklistItem.template_id == template_id,
            ServiceChecklistItem.deleted_at.is_(None)).order_by(ServiceChecklistItem.sort_order))
        items = r.scalars().all()
        return {"template_id": str(template_id), "items": [self._item_dict(i) for i in items]}

    async def add_item(self, template_id: uuid.UUID, data: dict) -> dict:
        await self._get_template_for_tenant(template_id)
        if not data.get("title") or not data["title"].strip():
            raise ServiceOSException("VALIDATION_ERROR", "title is required.", status_code=422)
        item = ServiceChecklistItem(
            template_id=template_id, title=data["title"].strip(),
            description=data.get("description"), sort_order=data.get("sort_order", 0),
            is_required=data.get("is_required", True),
            requires_photo=data.get("requires_photo", False),
            requires_note=data.get("requires_note", False),
            is_active=data.get("is_active", True),
        )
        self.db.add(item)
        await self.db.flush()
        return self._item_dict(item)

    async def _get_item_for_template(self, template_id: uuid.UUID, item_id: uuid.UUID) -> ServiceChecklistItem:
        await self._get_template_for_tenant(template_id)
        r = await self.db.execute(select(ServiceChecklistItem).where(ServiceChecklistItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item or item.template_id != template_id or item.deleted_at is not None:
            raise ServiceOSException("CHECKLIST_ITEM_NOT_FOUND",
                f"Checklist item '{item_id}' not found.", status_code=404)
        return item

    async def update_item(self, template_id: uuid.UUID, item_id: uuid.UUID, data: dict) -> dict:
        item = await self._get_item_for_template(template_id, item_id)
        for field in ("title", "description", "sort_order", "is_required",
                      "requires_photo", "requires_note", "is_active"):
            if field in data and data[field] is not None:
                setattr(item, field, data[field].strip() if field == "title" else data[field])
        return self._item_dict(item)

    async def delete_item(self, template_id: uuid.UUID, item_id: uuid.UUID) -> dict:
        item = await self._get_item_for_template(template_id, item_id)
        item.is_active = False
        item.deleted_at = utcnow()
        return {"item_id": str(item.id), "deleted": True}
