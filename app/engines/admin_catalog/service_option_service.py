"""Sprint 34E — ServiceOptionService.
Manages service option groups, master service options, master issue types,
service↔option mappings, service↔issue mappings, provider supported options,
and customer-facing catalog + diagnostic validation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterIssueType,
    MasterServiceOption,
    MasterService,
    ServiceGroup,
    ServiceCategory,
    ServiceOptionGroup,
    ServiceOptionMapping,
    ServiceIssueMapping,
    TenantSupportedServiceOption,
    MasterDataAuditLog,
    MasterChecklistItem,
    JobTypeDefinition,
)

_VALID_STATUSES = {"active", "inactive", "archived", "deprecated", "pending_review", "rejected"}

# HOME-SERVICES-CATALOG ownership correction (migration 169): admin templates/
# mappings must never carry a monetary value -- pricing is tenant-owned only.
# Any admin-facing create/update payload containing one of these is rejected
# outright rather than silently ignored, so a stale client can't assume it
# worked.
_FORBIDDEN_ADMIN_MONETARY_FIELDS = ("default_price", "min_price", "max_price",
                                     "price", "unit_price", "fixed_price",
                                     "minimum_price", "maximum_price")


def _reject_admin_monetary_fields(body: dict) -> None:
    present = [f for f in _FORBIDDEN_ADMIN_MONETARY_FIELDS if f in body]
    if present:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Admin cannot set monetary fields on a Service Option: {present}. "
            "Price is set by the tenant per Job-Type mapping (Tenant Setup > "
            "Options & Add-ons), not by admin.",
        )


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _issue_payload(issue: MasterIssueType) -> dict:
    """Serialize a booking problem without the retired artwork field."""
    payload = issue.to_dict()
    payload.pop("icon_url", None)
    return payload


class ServiceOptionService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None,
                 actor_role: str | None, request_id: str,
                 tenant_id: uuid.UUID | None = None):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id
        self.tenant_id = tenant_id

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT
    # ─────────────────────────────────────────────────────────────────────────
    async def _audit(self, entity_type: str, entity_id: uuid.UUID,
                     action: str, old: dict | None = None, new: dict | None = None,
                     summary: str = "") -> None:
        log = MasterDataAuditLog(
            entity_type=entity_type, entity_id=entity_id, action=action,
            actor_user_id=self.actor_id, actor_role=self.actor_role,
            old_value=old, new_value=new, change_summary=summary,
            request_id=self.request_id,
        )
        self.db.add(log)

    # ─────────────────────────────────────────────────────────────────────────
    # SERVICE OPTION GROUPS
    # ─────────────────────────────────────────────────────────────────────────
    async def list_option_groups(self, status: str | None = None,
                                 category_id: uuid.UUID | None = None) -> list[dict]:
        q = select(ServiceOptionGroup).where(ServiceOptionGroup.deleted_at.is_(None))
        if status:
            q = q.where(ServiceOptionGroup.status == status)
        if category_id:
            q = q.where(ServiceOptionGroup.category_id == category_id)
        q = q.order_by(ServiceOptionGroup.display_order, ServiceOptionGroup.name)
        rows = (await self.db.scalars(q)).all()
        return [r.to_dict() for r in rows]

    async def create_option_group(self, body: dict) -> dict:
        code = body.get("code", "").strip()
        if not code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "code required")
        existing = await self.db.scalar(
            select(ServiceOptionGroup).where(ServiceOptionGroup.code == code,
                                             ServiceOptionGroup.deleted_at.is_(None)))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Option group code '{code}' already exists")
        grp = ServiceOptionGroup(
            code=code,
            name=body.get("name", code),
            description=body.get("description"),
            category_id=uuid.UUID(body["category_id"]) if body.get("category_id") else None,
            vertical_type=body.get("vertical_type"),
            status=body.get("status", "active"),
            display_order=body.get("display_order", 0),
        )
        self.db.add(grp)
        await self.db.flush()
        await self._audit("service_option_group", grp.id, "created", new=grp.to_dict())
        await self.db.commit()
        return grp.to_dict()

    async def update_option_group(self, group_id: uuid.UUID, body: dict) -> dict:
        grp = await self.db.get(ServiceOptionGroup, group_id)
        if not grp or grp.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Option group not found")
        old = grp.to_dict()
        for field in ("name", "description", "vertical_type", "display_order"):
            if field in body:
                setattr(grp, field, body[field])
        if "status" in body:
            if body["status"] not in _VALID_STATUSES:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid status: {body['status']}")
            grp.status = body["status"]
        await self._audit("service_option_group", grp.id, "updated", old=old, new=grp.to_dict())
        await self.db.commit()
        return grp.to_dict()

    # ─────────────────────────────────────────────────────────────────────────
    # SERVICE OPTIONS
    # ─────────────────────────────────────────────────────────────────────────
    async def list_service_options_summary(self) -> dict:
        mapped_sub = (
            select(ServiceOptionMapping.service_option_id)
            .where(ServiceOptionMapping.status == "active",
                   ServiceOptionMapping.deleted_at.is_(None))
            .distinct()
            .subquery()
        )

        async def _count(*clauses) -> int:
            return await self.db.scalar(
                select(func.count(MasterServiceOption.id)).where(*clauses)
            ) or 0

        total           = await _count()
        active          = await _count(MasterServiceOption.status == "active")
        inactive        = await _count(MasterServiceOption.status == "inactive")
        archived        = await _count(MasterServiceOption.status == "archived")
        cust_selectable = await _count(MasterServiceOption.status == "active",
                                        MasterServiceOption.is_customer_selectable == True)
        mapped          = await _count(MasterServiceOption.status != "archived",
                                        MasterServiceOption.id.in_(select(mapped_sub)))
        unmapped        = await _count(MasterServiceOption.status == "active",
                                        MasterServiceOption.id.notin_(select(mapped_sub)))

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "archived": archived,
            "customer_selectable": cust_selectable,
            "mapped": mapped,
            "unmapped": unmapped,
        }

    async def list_service_options(self, status: str | None = None,
                                   category_id: uuid.UUID | None = None,
                                   master_service_id: uuid.UUID | None = None,
                                   option_group_id: uuid.UUID | None = None,
                                   option_type: str | None = None,
                                   mapped: bool | None = None,
                                   search: str | None = None,
                                   page: int = 1, page_size: int = 50) -> dict:
        q = select(MasterServiceOption)
        if status:
            q = q.where(MasterServiceOption.status == status)
        elif status is None:
            q = q.where(MasterServiceOption.status != "archived")
        if category_id:
            q = q.where(MasterServiceOption.category_id == category_id)
        if master_service_id:
            # Filter by options MAPPED to this service (via service_option_mappings)
            mapped_ids = select(ServiceOptionMapping.service_option_id).where(
                ServiceOptionMapping.master_service_id == master_service_id,
                ServiceOptionMapping.status == "active",
            )
            q = q.where(MasterServiceOption.id.in_(mapped_ids))
        if option_group_id:
            q = q.where(MasterServiceOption.option_group_id == option_group_id)
        if option_type:
            q = q.where(MasterServiceOption.option_type == option_type)
        if mapped is True:
            active_mapped = (
                select(ServiceOptionMapping.service_option_id)
                .where(ServiceOptionMapping.status == "active",
                       ServiceOptionMapping.deleted_at.is_(None))
                .distinct()
            )
            q = q.where(MasterServiceOption.id.in_(active_mapped))
        elif mapped is False:
            active_mapped = (
                select(ServiceOptionMapping.service_option_id)
                .where(ServiceOptionMapping.status == "active",
                       ServiceOptionMapping.deleted_at.is_(None))
                .distinct()
            )
            q = q.where(MasterServiceOption.id.notin_(active_mapped))
        if search:
            q = q.where(
                MasterServiceOption.name.ilike(f"%{search}%") |
                MasterServiceOption.code.ilike(f"%{search}%")
            )
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(MasterServiceOption.display_order, MasterServiceOption.name)
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()

        # Count how many services each option is mapped to
        option_ids = [r.id for r in rows]
        mapping_counts: dict[uuid.UUID, int] = {}
        if option_ids:
            count_q = (
                select(ServiceOptionMapping.service_option_id, func.count().label("cnt"))
                .where(
                    ServiceOptionMapping.service_option_id.in_(option_ids),
                    ServiceOptionMapping.status == "active",
                )
                .group_by(ServiceOptionMapping.service_option_id)
            )
            for row in (await self.db.execute(count_q)).all():
                mapping_counts[row.service_option_id] = row.cnt

        def _to_dict_with_count(r: MasterServiceOption) -> dict:
            d = r.to_dict()
            d["mapped_services_count"] = mapping_counts.get(r.id, 0)
            return d

        return {"items": [_to_dict_with_count(r) for r in rows], "total": total,
                "page": page, "page_size": page_size}

    async def get_service_option(self, option_id: uuid.UUID) -> dict:
        opt = await self.db.get(MasterServiceOption, option_id)
        if not opt:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Service option not found")
        return opt.to_dict()

    async def create_service_option(self, body: dict) -> dict:
        """Create a reusable Service Option TEMPLATE. Admin owns name/code/
        classification/unit/description/icon/status only -- no monetary
        value, no global customer-selectable behavior (migration 169). Those
        are configured per exact Job-Type mapping in Catalog Workspace."""
        _reject_admin_monetary_fields(body)
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "name required")
        slug = body.get("slug") or _slug(name)
        existing = await self.db.scalar(
            select(MasterServiceOption).where(MasterServiceOption.slug == slug))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Option slug '{slug}' already exists")
        opt = MasterServiceOption(
            category_id=uuid.UUID(body["category_id"]) if body.get("category_id") else None,
            master_service_id=uuid.UUID(body["master_service_id"]) if body.get("master_service_id") else None,
            code=body.get("code", slug),
            name=name,
            slug=slug,
            description=body.get("description"),
            option_type=body.get("option_type", "add_on"),
            unit=body.get("unit", "per_unit"),
            # is_customer_selectable intentionally not read from body: global
            # selectability is deprecated, defaults True but is never
            # authoritative -- ServiceOptionMapping.customer_selectable
            # (per exact Job Type) governs real eligibility.
            is_active=True,
            display_order=body.get("display_order", 0),
            option_group_id=uuid.UUID(body["option_group_id"]) if body.get("option_group_id") else None,
            vertical_type=body.get("vertical_type"),
            status=body.get("status", "active"),
            metadata_json=body.get("metadata_json"),
            created_by_user_id=self.actor_id,
        )
        self.db.add(opt)
        await self.db.flush()
        await self._audit("service_option", opt.id, "service_option.created", new=opt.to_dict())
        await self.db.commit()
        return opt.to_dict()

    async def update_service_option(self, option_id: uuid.UUID, body: dict) -> dict:
        _reject_admin_monetary_fields(body)
        opt = await self.db.get(MasterServiceOption, option_id)
        if not opt:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Service option not found")
        old = opt.to_dict()
        # is_customer_selectable deliberately excluded (see create_service_option).
        for field in ("name", "description", "option_type", "unit",
                      "display_order", "vertical_type", "metadata_json"):
            if field in body:
                setattr(opt, field, body[field])
        if "option_group_id" in body:
            opt.option_group_id = uuid.UUID(body["option_group_id"]) if body["option_group_id"] else None
        opt.updated_by_user_id = self.actor_id
        await self._audit("service_option", opt.id, "service_option.updated",
                          old=old, new=opt.to_dict())
        await self.db.commit()
        return opt.to_dict()

    async def _set_option_status(self, option_id: uuid.UUID, new_status: str) -> dict:
        opt = await self.db.get(MasterServiceOption, option_id)
        if not opt:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Service option not found")
        old_status = opt.status
        opt.status = new_status
        opt.is_active = (new_status == "active")
        opt.updated_by_user_id = self.actor_id
        action = f"service_option.{new_status}"
        await self._audit("service_option", opt.id, action,
                          old={"status": old_status}, new={"status": new_status})
        await self.db.commit()
        return opt.to_dict()

    async def activate_service_option(self, option_id: uuid.UUID) -> dict:
        return await self._set_option_status(option_id, "active")

    async def deactivate_service_option(self, option_id: uuid.UUID) -> dict:
        return await self._set_option_status(option_id, "inactive")

    async def archive_service_option(self, option_id: uuid.UUID) -> dict:
        return await self._set_option_status(option_id, "archived")

    # ─────────────────────────────────────────────────────────────────────────
    # ISSUE TYPES
    # ─────────────────────────────────────────────────────────────────────────
    async def list_issue_types(self, status: str | None = None,
                               category_id: uuid.UUID | None = None,
                               master_service_id: uuid.UUID | None = None,
                               search: str | None = None,
                               page: int = 1, page_size: int = 50) -> dict:
        from sqlalchemy import text as _text
        q = select(MasterIssueType)
        if status:
            q = q.where(MasterIssueType.status == status)
        elif status is None:
            q = q.where(MasterIssueType.status != "archived")
        if category_id:
            q = q.where(MasterIssueType.category_id == category_id)
        if master_service_id:
            # Filter to issue types mapped to this service
            q = q.where(MasterIssueType.id.in_(
                select(ServiceIssueMapping.issue_type_id).where(
                    ServiceIssueMapping.master_service_id == master_service_id,
                    ServiceIssueMapping.deleted_at.is_(None),
                )
            ))
        if search:
            q = q.where(MasterIssueType.name.ilike(f"%{search}%") | MasterIssueType.code.ilike(f"%{search}%"))
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(MasterIssueType.display_order, MasterIssueType.name)
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()

        # Fetch mapped_services_count for each issue type in one query
        if rows:
            ids = [r.id for r in rows]
            count_rows = (await self.db.execute(
                select(ServiceIssueMapping.issue_type_id,
                       func.count().label("cnt"))
                .where(ServiceIssueMapping.issue_type_id.in_(ids),
                       ServiceIssueMapping.deleted_at.is_(None),
                       ServiceIssueMapping.status == "active")
                .group_by(ServiceIssueMapping.issue_type_id)
            )).all()
            counts = {str(r.issue_type_id): r.cnt for r in count_rows}
        else:
            counts = {}

        items = []
        for r in rows:
            d = _issue_payload(r)
            d["mapped_services_count"] = counts.get(str(r.id), 0)
            items.append(d)

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_issue_type(self, issue_id: uuid.UUID) -> dict:
        it = await self.db.get(MasterIssueType, issue_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue type not found")
        return _issue_payload(it)

    async def create_issue_type(self, body: dict) -> dict:
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "name required")
        slug = body.get("slug") or _slug(name)
        existing = await self.db.scalar(
            select(MasterIssueType).where(MasterIssueType.slug == slug))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Issue slug '{slug}' already exists")
        it = MasterIssueType(
            category_id=uuid.UUID(body["category_id"]) if body.get("category_id") else None,
            master_service_id=uuid.UUID(body["master_service_id"]) if body.get("master_service_id") else None,
            code=body.get("code", slug),
            name=name,
            slug=slug,
            description=body.get("description"),
            severity=body.get("severity_default", body.get("severity", "medium")),
            is_active=True,
            display_order=body.get("display_order", 0),
            vertical_type=body.get("vertical_type"),
            status=body.get("status", "active"),
            metadata_json=body.get("metadata_json"),
            requires_photo=body.get("requires_photo", False),
            requires_description=body.get("requires_description", False),
            customer_visible=body.get("customer_visible", True),
            created_by_user_id=self.actor_id,
        )
        self.db.add(it)
        await self.db.flush()
        await self._audit("issue_type", it.id, "issue_type.created", new=_issue_payload(it))
        await self.db.commit()
        return _issue_payload(it)

    async def update_issue_type(self, issue_id: uuid.UUID, body: dict) -> dict:
        it = await self.db.get(MasterIssueType, issue_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue type not found")
        old = _issue_payload(it)
        for field in ("name", "description", "vertical_type", "metadata_json",
                      "requires_photo", "requires_description", "customer_visible", "display_order"):
            if field in body:
                setattr(it, field, body[field])
        if "severity_default" in body:
            it.severity = body["severity_default"]
        elif "severity" in body:
            it.severity = body["severity"]
        it.updated_by_user_id = self.actor_id
        await self._audit("issue_type", it.id, "issue_type.updated", old=old, new=_issue_payload(it))
        await self.db.commit()
        return _issue_payload(it)

    async def _set_issue_status(self, issue_id: uuid.UUID, new_status: str) -> dict:
        it = await self.db.get(MasterIssueType, issue_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue type not found")
        old_status = it.status
        it.status = new_status
        it.is_active = (new_status == "active")
        it.updated_by_user_id = self.actor_id
        await self._audit("issue_type", it.id, f"issue_type.{new_status}",
                          old={"status": old_status}, new={"status": new_status})
        await self.db.commit()
        return _issue_payload(it)

    async def activate_issue_type(self, issue_id: uuid.UUID) -> dict:
        return await self._set_issue_status(issue_id, "active")

    async def deactivate_issue_type(self, issue_id: uuid.UUID) -> dict:
        return await self._set_issue_status(issue_id, "inactive")

    async def archive_issue_type(self, issue_id: uuid.UUID) -> dict:
        return await self._set_issue_status(issue_id, "archived")

    # ═════════════════════════════════════════════════════════
    # CHECKLIST ITEMS (Phase 2 — master/admin-catalog-level)
    # ═════════════════════════════════════════════════════════

    async def list_checklist_items(self, status: str | None = None,
                                    category_id: uuid.UUID | None = None,
                                    master_service_id: uuid.UUID | None = None,
                                    search: str | None = None,
                                    page: int = 1, page_size: int = 50) -> dict:
        q = select(MasterChecklistItem)
        if status:
            q = q.where(MasterChecklistItem.status == status)
        elif status is None:
            q = q.where(MasterChecklistItem.status != "archived")
        if category_id:
            q = q.where(MasterChecklistItem.category_id == category_id)
        if master_service_id:
            q = q.where(MasterChecklistItem.master_service_id == master_service_id)
        if search:
            q = q.where(MasterChecklistItem.title.ilike(f"%{search}%") |
                        MasterChecklistItem.code.ilike(f"%{search}%"))
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(MasterChecklistItem.display_order, MasterChecklistItem.title)
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}

    async def get_checklist_item(self, item_id: uuid.UUID) -> dict:
        it = await self.db.get(MasterChecklistItem, item_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
        return it.to_dict()

    async def create_checklist_item(self, body: dict) -> dict:
        title = body.get("title", "").strip()
        if not title:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "title required")
        slug = body.get("slug") or _slug(title)
        existing = await self.db.scalar(
            select(MasterChecklistItem).where(MasterChecklistItem.slug == slug))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Checklist slug '{slug}' already exists")
        it = MasterChecklistItem(
            category_id=uuid.UUID(body["category_id"]) if body.get("category_id") else None,
            master_service_id=uuid.UUID(body["master_service_id"]) if body.get("master_service_id") else None,
            workflow_step_key=body.get("workflow_step_key"),
            code=body.get("code", slug),
            title=title,
            slug=slug,
            description=body.get("description"),
            is_required=body.get("is_required", body.get("required", True)),
            owner_role=body.get("owner_role", "technician"),
            customer_visible=body.get("customer_visible", False),
            staff_visible=body.get("staff_visible", True),
            tenant_visible=body.get("tenant_visible", True),
            is_active=True,
            display_order=body.get("display_order", 0),
            vertical_type=body.get("vertical_type"),
            status=body.get("status", "active"),
            metadata_json=body.get("metadata_json"),
            created_by_user_id=self.actor_id,
        )
        self.db.add(it)
        await self.db.flush()
        await self._audit("checklist", it.id, "checklist.created", new=it.to_dict())
        await self.db.commit()
        return it.to_dict()

    async def update_checklist_item(self, item_id: uuid.UUID, body: dict) -> dict:
        it = await self.db.get(MasterChecklistItem, item_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
        old = it.to_dict()
        for field in ("title", "description", "workflow_step_key", "owner_role",
                      "customer_visible", "staff_visible", "tenant_visible",
                      "display_order", "vertical_type", "metadata_json"):
            if field in body:
                setattr(it, field, body[field])
        if "is_required" in body:
            it.is_required = body["is_required"]
        elif "required" in body:
            it.is_required = body["required"]
        it.updated_by_user_id = self.actor_id
        await self._audit("checklist", it.id, "checklist.updated", old=old, new=it.to_dict())
        await self.db.commit()
        return it.to_dict()

    async def _set_checklist_status(self, item_id: uuid.UUID, new_status: str) -> dict:
        it = await self.db.get(MasterChecklistItem, item_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
        old_status = it.status
        it.status = new_status
        it.is_active = (new_status == "active")
        it.updated_by_user_id = self.actor_id
        await self._audit("checklist", it.id, f"checklist.{new_status}",
                          old={"status": old_status}, new={"status": new_status})
        await self.db.commit()
        return it.to_dict()

    async def activate_checklist_item(self, item_id: uuid.UUID) -> dict:
        return await self._set_checklist_status(item_id, "active")

    async def deactivate_checklist_item(self, item_id: uuid.UUID) -> dict:
        return await self._set_checklist_status(item_id, "inactive")

    async def archive_checklist_item(self, item_id: uuid.UUID) -> dict:
        return await self._set_checklist_status(item_id, "archived")

    async def seed_default_checklists(self) -> dict:
        """One-click seed of the Phase 2 baseline checklist items, linked to
        AC Repair. Idempotent — skips items whose slug already exists.
        Mirrors scripts/seed_checklists.py."""
        cat = await self.db.scalar(
            select(ServiceCategory).where(ServiceCategory.slug == "home_services"))
        ac_repair = await self.db.scalar(
            select(MasterService).where(MasterService.slug == "ac_repair"))
        if not cat or not ac_repair:
            raise HTTPException(status.HTTP_409_CONFLICT,
                "home_services category or ac_repair service not found — "
                "seed base catalog data first.")

        defaults = [
            {"title": "Technician Diagnosis Note", "slug": "technician_diagnosis_note", "code": "DIAGNOSIS_NOTE",
             "customer_visible": False},
            {"title": "Before/After Service Photo", "slug": "before_after_service_photo", "code": "BEFORE_AFTER_PHOTO",
             "customer_visible": True},
            {"title": "Payment Collection Confirmation", "slug": "payment_collection_confirmation", "code": "PAYMENT_CONFIRM",
             "customer_visible": False},
            {"title": "Completion Note", "slug": "completion_note", "code": "COMPLETION_NOTE",
             "customer_visible": False},
        ]

        created, skipped = [], []
        for idx, item in enumerate(defaults):
            existing = await self.db.scalar(
                select(MasterChecklistItem).where(MasterChecklistItem.slug == item["slug"]))
            if existing:
                skipped.append(item["title"])
                continue
            row = MasterChecklistItem(
                category_id=cat.id, master_service_id=ac_repair.id,
                code=item["code"], title=item["title"], slug=item["slug"],
                is_required=True, owner_role="technician",
                customer_visible=item["customer_visible"], staff_visible=True, tenant_visible=True,
                is_active=True, status="active", display_order=idx,
                created_by_user_id=self.actor_id,
            )
            self.db.add(row)
            created.append(item["title"])

        if created:
            await self.db.flush()
            await self._audit("checklist", ac_repair.id, "checklist.seed_defaults",
                              new={"created": created, "skipped": skipped})
        await self.db.commit()
        return {"created": created, "skipped": skipped}

    # ─────────────────────────────────────────────────────────────────────────
    # SERVICE ↔ OPTION MAPPINGS
    # ─────────────────────────────────────────────────────────────────────────
    async def list_service_option_mappings(self, master_service_id: uuid.UUID,
                                           job_type_id: uuid.UUID | None = None) -> list[dict]:
        conditions = [ServiceOptionMapping.master_service_id == master_service_id,
                      ServiceOptionMapping.deleted_at.is_(None)]
        if job_type_id is not None:
            # Exact Job-Type scoping only -- unlike issue mappings, a NULL
            # job_type_id here means "not yet assigned to a Job Type"
            # (legacy/ambiguous), not "applies to every Job Type". Per the
            # non-negotiable rule (no Master-Service-only runtime mapping),
            # we do not fall back to NULL rows for a job-type-scoped query.
            conditions.append(ServiceOptionMapping.job_type_id == job_type_id)
        q = (select(ServiceOptionMapping, MasterServiceOption)
             .join(MasterServiceOption, ServiceOptionMapping.service_option_id == MasterServiceOption.id)
             .where(*conditions)
             .order_by(ServiceOptionMapping.display_order))
        rows = (await self.db.execute(q)).all()
        result = []
        for mapping, opt in rows:
            d = mapping.to_dict()
            d["option"] = opt.to_dict()
            result.append(d)
        return result

    async def add_service_option_mapping(self, master_service_id: uuid.UUID, body: dict) -> dict:
        """Map a Service Option to an EXACT Job-Type Blueprint. job_type_id is
        mandatory (migration 169 non-negotiable rule: no Master-Service-only
        mapping) -- the same option may be required under Installation but
        not offered at all under Repair, so a single Master-Service-level
        mapping is never sufficient."""
        _reject_admin_monetary_fields(body)
        job_type_id_raw = body.get("job_type_id")
        if not job_type_id_raw:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "job_type_id is required — a Service Option must be mapped to an "
                "exact Job-Type Blueprint (e.g. Installation), not to the Master "
                "Service alone. The same option may not apply to every Job Type.",
            )
        job_type_id = uuid.UUID(job_type_id_raw)
        job_type = await self.db.get(JobTypeDefinition, job_type_id)
        if not job_type or not job_type.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Job type not found or inactive")

        service_option_id = uuid.UUID(body["service_option_id"])
        existing = await self.db.scalar(
            select(ServiceOptionMapping).where(
                ServiceOptionMapping.master_service_id == master_service_id,
                ServiceOptionMapping.service_option_id == service_option_id,
                ServiceOptionMapping.job_type_id == job_type_id,
                ServiceOptionMapping.deleted_at.is_(None)))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Option already mapped to this Job Type")
        opt = await self.db.get(MasterServiceOption, service_option_id)
        if not opt:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Service option not found")

        usage = body.get("usage", "OPTIONAL")
        if usage not in ("DISABLED", "OPTIONAL", "REQUIRED"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid usage: {usage}")

        m = ServiceOptionMapping(
            master_service_id=master_service_id,
            service_option_id=service_option_id,
            job_type_id=job_type_id,
            option_group_id=uuid.UUID(body["option_group_id"]) if body.get("option_group_id") else opt.option_group_id,
            status=body.get("status", "active"),
            usage=usage,
            is_required=(usage == "REQUIRED"),
            is_default=body.get("is_default", False),
            customer_selectable=body.get("customer_selectable", True),
            tenant_selectable=body.get("tenant_selectable", True),
            technician_selectable=body.get("technician_selectable", False),
            available_before_booking=body.get("available_before_booking", True),
            available_after_inspection=body.get("available_after_inspection", False),
            affects_estimate=body.get("affects_estimate", True),
            requires_customer_approval=body.get("requires_customer_approval", True),
            quantity_supported=body.get("quantity_supported", False),
            minimum_quantity=body.get("minimum_quantity"),
            maximum_quantity=body.get("maximum_quantity"),
            measurement_unit=body.get("measurement_unit"),
            blueprint_version=body.get("blueprint_version"),
            display_order=body.get("display_order", 0),
            created_by_user_id=self.actor_id,
        )
        self.db.add(m)
        await self.db.flush()
        await self._audit("service_option_mapping", m.id, "service_option.mapped_to_job_type",
                          new={"master_service_id": str(master_service_id),
                               "service_option_id": str(service_option_id),
                               "job_type_id": str(job_type_id)})
        await self.db.commit()
        return m.to_dict()

    async def update_service_option_mapping(self, mapping_id: uuid.UUID, body: dict) -> dict:
        _reject_admin_monetary_fields(body)
        m = await self.db.get(ServiceOptionMapping, mapping_id)
        if not m or m.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mapping not found")
        if "usage" in body:
            if body["usage"] not in ("DISABLED", "OPTIONAL", "REQUIRED"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid usage: {body['usage']}")
            m.usage = body["usage"]
            m.is_required = (body["usage"] == "REQUIRED")
        for field in ("is_default", "display_order", "status",
                      "customer_selectable", "tenant_selectable", "technician_selectable",
                      "available_before_booking", "available_after_inspection",
                      "affects_estimate", "requires_customer_approval",
                      "quantity_supported", "minimum_quantity", "maximum_quantity",
                      "measurement_unit", "blueprint_version"):
            if field in body:
                setattr(m, field, body[field])
        await self.db.commit()
        return m.to_dict()

    async def remove_service_option_mapping(self, mapping_id: uuid.UUID) -> dict:
        m = await self.db.get(ServiceOptionMapping, mapping_id)
        if not m or m.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mapping not found")
        m.deleted_at = datetime.now(timezone.utc)
        await self._audit("service_option_mapping", m.id, "service_option.unmapped_from_service",
                          new={"master_service_id": str(m.master_service_id),
                               "service_option_id": str(m.service_option_id)})
        await self.db.commit()
        return {"deleted": True}

    # ─────────────────────────────────────────────────────────────────────────
    # SERVICE ↔ ISSUE MAPPINGS
    # ─────────────────────────────────────────────────────────────────────────
    async def list_service_issue_mappings(self, master_service_id: uuid.UUID,
                                          job_type_id: uuid.UUID | None = None) -> list[dict]:
        conditions = [ServiceIssueMapping.master_service_id == master_service_id,
                      ServiceIssueMapping.deleted_at.is_(None)]
        if job_type_id is not None:
            # Job-type-scoped tab shows both this job type's own Problems AND
            # the service-wide (NULL) ones -- never hides an unscoped Problem.
            conditions.append(or_(ServiceIssueMapping.job_type_id == job_type_id,
                                  ServiceIssueMapping.job_type_id.is_(None)))
        q = (select(ServiceIssueMapping, MasterIssueType)
             .join(MasterIssueType, ServiceIssueMapping.issue_type_id == MasterIssueType.id)
             .where(*conditions)
             .order_by(ServiceIssueMapping.is_common.desc(), ServiceIssueMapping.display_order))
        rows = (await self.db.execute(q)).all()
        result = []
        for mapping, it in rows:
            d = mapping.to_dict()
            d["issue_type"] = _issue_payload(it)
            d["mapping_id"] = d["id"]
            d["name"] = it.name
            d["code"] = it.code
            result.append(d)
        return result

    async def add_service_issue_mapping(self, master_service_id: uuid.UUID, body: dict) -> dict:
        issue_type_id = uuid.UUID(body["issue_type_id"])
        existing = await self.db.scalar(
            select(ServiceIssueMapping).where(
                ServiceIssueMapping.master_service_id == master_service_id,
                ServiceIssueMapping.issue_type_id == issue_type_id,
                ServiceIssueMapping.deleted_at.is_(None)))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Issue type already mapped to this service")
        it = await self.db.get(MasterIssueType, issue_type_id)
        if not it:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue type not found")
        m = ServiceIssueMapping(
            master_service_id=master_service_id,
            issue_type_id=issue_type_id,
            job_type_id=uuid.UUID(body["job_type_id"]) if body.get("job_type_id") else None,
            status=body.get("status", "active"),
            is_common=body.get("is_common", False),
            is_default=body.get("is_default", False),
            customer_visible=body.get("customer_visible", True),
            requires_photo=body.get("requires_photo", it.requires_photo),
            requires_description=body.get("requires_description", it.requires_description),
            severity_override=body.get("severity_override"),
            display_order=body.get("display_order", 0),
            created_by_user_id=self.actor_id,
        )
        self.db.add(m)
        await self.db.flush()
        await self._audit("service_issue_mapping", m.id, "issue_type.mapped_to_service",
                          new={"master_service_id": str(master_service_id),
                               "issue_type_id": str(issue_type_id)})
        await self.db.commit()
        return m.to_dict()

    async def update_service_issue_mapping(self, mapping_id: uuid.UUID, body: dict) -> dict:
        m = await self.db.get(ServiceIssueMapping, mapping_id)
        if not m or m.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mapping not found")
        for field in ("is_common", "is_default", "customer_visible", "requires_photo",
                      "requires_description", "severity_override", "display_order", "status"):
            if field in body:
                setattr(m, field, body[field])
        if "job_type_id" in body:
            m.job_type_id = uuid.UUID(body["job_type_id"]) if body["job_type_id"] else None
        await self.db.commit()
        return m.to_dict()

    async def remove_service_issue_mapping(self, mapping_id: uuid.UUID) -> dict:
        m = await self.db.get(ServiceIssueMapping, mapping_id)
        if not m or m.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mapping not found")
        m.deleted_at = datetime.now(timezone.utc)
        await self._audit("service_issue_mapping", m.id, "issue_type.unmapped_from_service",
                          new={"master_service_id": str(m.master_service_id),
                               "issue_type_id": str(m.issue_type_id)})
        await self.db.commit()
        return {"deleted": True}

    # ─────────────────────────────────────────────────────────────────────────
    # PROVIDER SUPPORTED OPTIONS
    # ─────────────────────────────────────────────────────────────────────────
    async def _require_tenant(self) -> uuid.UUID:
        if not self.tenant_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "tenant_id required")
        return self.tenant_id

    async def get_available_options_for_service(self, master_service_id: uuid.UUID,
                                                job_type_id: uuid.UUID | None = None) -> list[dict]:
        """Admin-approved options that can be selected for this service, for
        an exact Job Type. Fails closed (returns nothing) for a mapping whose
        job_type_id hasn't been assigned yet, rather than guessing it applies
        everywhere -- see the non-negotiable "no Master-Service-only runtime
        mapping" rule."""
        conditions = [ServiceOptionMapping.master_service_id == master_service_id,
                      ServiceOptionMapping.status == "active",
                      ServiceOptionMapping.usage != "DISABLED",
                      ServiceOptionMapping.deleted_at.is_(None),
                      MasterServiceOption.status == "active"]
        if job_type_id is not None:
            conditions.append(ServiceOptionMapping.job_type_id == job_type_id)
        q = (select(ServiceOptionMapping, MasterServiceOption)
             .join(MasterServiceOption, ServiceOptionMapping.service_option_id == MasterServiceOption.id)
             .where(*conditions)
             .order_by(ServiceOptionMapping.display_order))
        rows = (await self.db.execute(q)).all()
        result = []
        for mapping, opt in rows:
            d = opt.to_dict()
            d["is_required"] = mapping.is_required
            d["is_default"] = mapping.is_default
            d["mapping_id"] = str(mapping.id)
            d["job_type_id"] = str(mapping.job_type_id) if mapping.job_type_id else None
            d["usage"] = mapping.usage
            d["customer_selectable"] = mapping.customer_selectable
            d["tenant_selectable"] = mapping.tenant_selectable
            d["technician_selectable"] = mapping.technician_selectable
            d["quantity_supported"] = mapping.quantity_supported
            d["minimum_quantity"] = mapping.minimum_quantity
            d["maximum_quantity"] = mapping.maximum_quantity
            d["measurement_unit"] = mapping.measurement_unit or opt.unit
            result.append(d)
        return result

    async def get_provider_supported_options(self, master_service_id: uuid.UUID) -> list[dict]:
        tenant_id = await self._require_tenant()
        q = (select(TenantSupportedServiceOption, MasterServiceOption)
             .join(MasterServiceOption,
                   TenantSupportedServiceOption.service_option_id == MasterServiceOption.id)
             .where(TenantSupportedServiceOption.tenant_id == tenant_id,
                    TenantSupportedServiceOption.master_service_id == master_service_id,
                    TenantSupportedServiceOption.deleted_at.is_(None))
             .order_by(MasterServiceOption.display_order))
        rows = (await self.db.execute(q)).all()
        result = []
        for tsso, opt in rows:
            d = tsso.to_dict()
            d["option"] = opt.to_dict()
            result.append(d)
        return result

    async def set_provider_supported_options(
        self, master_service_id: uuid.UUID, body: dict
    ) -> dict:
        tenant_id = await self._require_tenant()
        option_ids = [uuid.UUID(x) for x in body.get("service_option_ids", [])]
        # validate: each option must be mapped to this service
        if option_ids:
            mapped_rows = await self.db.scalars(
                select(ServiceOptionMapping.service_option_id).where(
                    ServiceOptionMapping.master_service_id == master_service_id,
                    ServiceOptionMapping.status == "active",
                    ServiceOptionMapping.deleted_at.is_(None)))
            allowed = set(mapped_rows.all())
            invalid = [str(oid) for oid in option_ids if oid not in allowed]
            if invalid:
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    f"Options not approved for this service: {invalid}")

        # soft-delete existing
        existing = (await self.db.scalars(
            select(TenantSupportedServiceOption).where(
                TenantSupportedServiceOption.tenant_id == tenant_id,
                TenantSupportedServiceOption.master_service_id == master_service_id,
                TenantSupportedServiceOption.deleted_at.is_(None)))).all()
        now = datetime.now(timezone.utc)
        for row in existing:
            if row.service_option_id not in option_ids:
                row.deleted_at = now

        existing_ids = {row.service_option_id for row in existing if not row.deleted_at}
        for oid in option_ids:
            if oid not in existing_ids:
                self.db.add(TenantSupportedServiceOption(
                    tenant_id=tenant_id,
                    master_service_id=master_service_id,
                    service_option_id=oid,
                    status="active",
                    created_by_user_id=self.actor_id,
                ))
        await self._audit("tenant_supported_service_options", tenant_id,
                          "provider_service_option.updated",
                          new={"master_service_id": str(master_service_id),
                               "option_ids": [str(x) for x in option_ids]})
        await self.db.commit()
        return {"set": len(option_ids)}

    # ─────────────────────────────────────────────────────────────────────────
    # TENANT-OWNED OPTION PRICING (migration 169)
    # ─────────────────────────────────────────────────────────────────────────
    _VALID_PRICING_MODELS = {"FIXED", "PER_UNIT", "RANGE"}

    async def set_tenant_option_price(self, mapping_id: uuid.UUID, body: dict) -> dict:
        """Tenant sets its own price for a Service Option, scoped to the exact
        Job-Type mapping. Admin never supplies a fallback -- an enabled,
        estimate-affecting option with no valid tenant price cannot publish
        (enforced by the caller/wizard; this method just refuses to persist
        an invalid combination)."""
        tenant_id = await self._require_tenant()
        mapping = await self.db.get(ServiceOptionMapping, mapping_id)
        if not mapping or mapping.deleted_at or mapping.status != "active":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Option mapping not found")
        if not mapping.tenant_selectable:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "This option is not tenant-configurable for this Job Type")

        enabled = body.get("enabled", True)
        pricing_model = body.get("pricing_model")
        if enabled and mapping.affects_estimate and mapping.usage != "DISABLED":
            if pricing_model not in self._VALID_PRICING_MODELS:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    {"field": "pricing_model",
                                     "error": "pricing_model must be one of FIXED/PER_UNIT/RANGE"})
            if pricing_model == "FIXED" and body.get("fixed_price") in (None, ""):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    {"field": "fixed_price", "error": "fixed_price is required"})
            if pricing_model == "PER_UNIT" and body.get("unit_price") in (None, ""):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    {"field": "unit_price", "error": "unit_price is required"})
            if pricing_model == "RANGE" and (body.get("minimum_price") in (None, "")
                                              or body.get("maximum_price") in (None, "")):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    {"field": "minimum_price/maximum_price",
                                     "error": "both minimum_price and maximum_price are required"})

        from decimal import Decimal
        row = await self.db.scalar(
            select(TenantSupportedServiceOption).where(
                TenantSupportedServiceOption.tenant_id == tenant_id,
                TenantSupportedServiceOption.service_option_mapping_id == mapping_id,
                TenantSupportedServiceOption.deleted_at.is_(None)))
        if not row:
            row = TenantSupportedServiceOption(
                tenant_id=tenant_id,
                master_service_id=mapping.master_service_id,
                service_option_id=mapping.service_option_id,
                service_option_mapping_id=mapping_id,
                created_by_user_id=self.actor_id,
            )
            self.db.add(row)

        row.status = "active" if enabled else "inactive"
        row.pricing_model = pricing_model
        row.fixed_price = Decimal(str(body["fixed_price"])) if body.get("fixed_price") not in (None, "") else None
        row.unit_price = Decimal(str(body["unit_price"])) if body.get("unit_price") not in (None, "") else None
        row.minimum_price = Decimal(str(body["minimum_price"])) if body.get("minimum_price") not in (None, "") else None
        row.maximum_price = Decimal(str(body["maximum_price"])) if body.get("maximum_price") not in (None, "") else None
        row.currency = body.get("currency", row.currency or "INR")
        await self.db.flush()
        await self._audit("tenant_supported_service_options", row.id,
                          "tenant_option_price.set",
                          new={"mapping_id": str(mapping_id), "pricing_model": pricing_model})
        await self.db.commit()
        return row.to_dict()

    async def resolve_tenant_option_price(self, tenant_id: uuid.UUID, mapping_id: uuid.UUID,
                                          quantity: int = 1) -> dict:
        """Backend-only price resolution -- never trusts a client-supplied
        price or total. Returns the tenant's configured price/unit/total for
        this exact mapping, or raises if none is configured."""
        mapping = await self.db.get(ServiceOptionMapping, mapping_id)
        if not mapping or mapping.deleted_at or mapping.status != "active":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Option mapping not found")
        if mapping.quantity_supported:
            lo = mapping.minimum_quantity or 1
            hi = mapping.maximum_quantity
            if quantity < lo or (hi is not None and quantity > hi):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    f"Quantity must be between {lo} and {hi or lo}")
        elif quantity != 1:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "This option does not support a quantity other than 1")
        if quantity <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Quantity must be positive")

        row = await self.db.scalar(
            select(TenantSupportedServiceOption).where(
                TenantSupportedServiceOption.tenant_id == tenant_id,
                TenantSupportedServiceOption.service_option_mapping_id == mapping_id,
                TenantSupportedServiceOption.status == "active",
                TenantSupportedServiceOption.deleted_at.is_(None)))
        if not row or not row.pricing_model:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "This tenant has not configured a valid price for this option")

        from decimal import Decimal
        if row.pricing_model == "FIXED":
            unit_price = row.fixed_price
        elif row.pricing_model == "PER_UNIT":
            unit_price = row.unit_price
        else:  # RANGE — resolves to the minimum as the quoted starting price
            unit_price = row.minimum_price
        if unit_price is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Tenant price is misconfigured")

        total = (unit_price * quantity).quantize(Decimal("0.01"))
        return {
            "service_option_mapping_id": str(mapping_id),
            "unit_price": str(unit_price),
            "quantity": quantity,
            "total": str(total),
            "currency": row.currency,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # CUSTOMER CATALOG
    # ─────────────────────────────────────────────────────────────────────────
    async def get_customer_options(self, master_service_id: uuid.UUID | None,
                                   category_id: uuid.UUID | None = None,
                                   job_type_id: uuid.UUID | None = None,
                                   tenant_id: uuid.UUID | None = None) -> list[dict]:
        """Options eligible for customer selection: active mapping for the
        EXACT job type, customer_selectable at the mapping level (not the
        deprecated global template flag), and — when the option affects the
        estimate and a tenant is known — a valid tenant price actually
        resolves. Never returns a mapping with no job_type_id assigned yet
        (fails closed rather than assuming it applies to every job type)."""
        conditions = [ServiceOptionMapping.status == "active",
                      ServiceOptionMapping.usage != "DISABLED",
                      ServiceOptionMapping.customer_selectable == True,
                      ServiceOptionMapping.deleted_at.is_(None),
                      MasterServiceOption.status == "active"]
        if master_service_id:
            conditions.append(ServiceOptionMapping.master_service_id == master_service_id)
        if job_type_id:
            conditions.append(ServiceOptionMapping.job_type_id == job_type_id)
        else:
            # No job type context supplied: only ever surface options already
            # scoped to a specific job type, never the ambiguous NULL rows.
            conditions.append(ServiceOptionMapping.job_type_id.isnot(None))
        if category_id:
            conditions.append(MasterServiceOption.category_id == category_id)
        q = (select(ServiceOptionMapping, MasterServiceOption)
             .join(MasterServiceOption, ServiceOptionMapping.service_option_id == MasterServiceOption.id)
             .where(*conditions)
             .order_by(ServiceOptionMapping.display_order, MasterServiceOption.display_order))
        rows = (await self.db.execute(q)).all()

        tenant_prices: dict[uuid.UUID, TenantSupportedServiceOption] = {}
        if tenant_id:
            tsso_rows = (await self.db.scalars(
                select(TenantSupportedServiceOption).where(
                    TenantSupportedServiceOption.tenant_id == tenant_id,
                    TenantSupportedServiceOption.status == "active",
                    TenantSupportedServiceOption.deleted_at.is_(None)))).all()
            tenant_prices = {r.service_option_mapping_id: r for r in tsso_rows if r.service_option_mapping_id}

        result = []
        for mapping, opt in rows:
            tenant_row = tenant_prices.get(mapping.id) if tenant_id else None
            if tenant_id:
                # Tenant must provide the option; if it affects the estimate,
                # a resolvable price is mandatory for customer visibility.
                if not tenant_row:
                    continue
                if mapping.affects_estimate and not tenant_row.pricing_model:
                    continue
            d = {
                "service_option_id":   str(opt.id),
                "service_option_mapping_id": str(mapping.id),
                "name":                 opt.name,
                "display_name":         opt.name,
                "code":                 opt.code,
                "option_group_id":      str(opt.option_group_id) if opt.option_group_id else None,
                "job_type_id":          str(mapping.job_type_id) if mapping.job_type_id else None,
                "is_required":          mapping.is_required,
                "is_default":           mapping.is_default,
                "quantity_supported":   mapping.quantity_supported,
                "minimum_quantity":     mapping.minimum_quantity,
                "maximum_quantity":     mapping.maximum_quantity,
                "measurement_unit":     mapping.measurement_unit or opt.unit,
                "display_order":        mapping.display_order,
            }
            if tenant_row:
                d["unit_price"] = (str(tenant_row.fixed_price) if tenant_row.pricing_model == "FIXED"
                                   else str(tenant_row.unit_price) if tenant_row.pricing_model == "PER_UNIT"
                                   else str(tenant_row.minimum_price) if tenant_row.pricing_model == "RANGE"
                                   else None)
                d["currency"] = tenant_row.currency
            result.append(d)
        return result

    async def get_customer_issue_types(self, master_service_id: uuid.UUID | None,
                                       category_id: uuid.UUID | None = None) -> list[dict]:
        """Active issue types mapped to the service, common first."""
        q = (select(ServiceIssueMapping, MasterIssueType)
             .join(MasterIssueType, ServiceIssueMapping.issue_type_id == MasterIssueType.id)
             .where(ServiceIssueMapping.status == "active",
                    ServiceIssueMapping.deleted_at.is_(None),
                    ServiceIssueMapping.customer_visible == True,
                    MasterIssueType.status == "active",
                    MasterIssueType.customer_visible == True))
        if master_service_id:
            q = q.where(ServiceIssueMapping.master_service_id == master_service_id)
        if category_id:
            q = q.where(MasterIssueType.category_id == category_id)
        q = q.order_by(ServiceIssueMapping.is_common.desc(), ServiceIssueMapping.display_order,
                       MasterIssueType.display_order)
        rows = (await self.db.execute(q)).all()
        result = []
        for mapping, it in rows:
            result.append({
                "issue_type_id":        str(it.id),
                "name":                 it.name,
                "code":                 it.code,
                "severity":             mapping.severity_override or it.severity,
                "is_common":            mapping.is_common,
                "requires_photo":       mapping.requires_photo,
                "requires_description": mapping.requires_description,
                "display_order":        mapping.display_order,
            })
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # DIAGNOSTIC VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    async def validate_service_diagnostics(self, body: dict) -> dict:
        """Validate issue_type_id + service_option_id for a service; fuzzy-match text fallback."""
        service_id_raw = body.get("service_id")
        issue_type_id_raw = body.get("issue_type_id")
        service_option_id_raw = body.get("service_option_id")
        typed_issue = (body.get("typed_issue") or "").strip().lower()
        typed_option = (body.get("typed_option") or "").strip().lower()

        master_service_id = uuid.UUID(service_id_raw) if service_id_raw else None
        result: dict[str, Any] = {"valid": True, "warnings": []}

        # ── Issue type ────────────────────────────────────────────────────────
        matched_issue_id: uuid.UUID | None = None
        requires_photo = False
        requires_description = False

        if issue_type_id_raw:
            issue_type_id = uuid.UUID(issue_type_id_raw)
            if master_service_id:
                mapping = await self.db.scalar(
                    select(ServiceIssueMapping).where(
                        ServiceIssueMapping.master_service_id == master_service_id,
                        ServiceIssueMapping.issue_type_id == issue_type_id,
                        ServiceIssueMapping.status == "active",
                        ServiceIssueMapping.deleted_at.is_(None)))
                if not mapping:
                    return {"valid": False, "error": "ISSUE_TYPE_NOT_MAPPED_TO_SERVICE"}
                requires_photo = mapping.requires_photo
                requires_description = mapping.requires_description
            else:
                it = await self.db.get(MasterIssueType, issue_type_id)
                if not it or it.status != "active":
                    return {"valid": False, "error": "ISSUE_TYPE_INACTIVE"}
                requires_photo = it.requires_photo
                requires_description = it.requires_description
            matched_issue_id = issue_type_id
        elif typed_issue:
            # fuzzy match against active mapped issues
            issues = await self.get_customer_issue_types(master_service_id)
            for iss in issues:
                if typed_issue in iss["name"].lower() or iss["name"].lower() in typed_issue:
                    matched_issue_id = uuid.UUID(iss["issue_type_id"])
                    requires_photo = iss["requires_photo"]
                    requires_description = iss["requires_description"]
                    break
            if not matched_issue_id:
                result["warnings"].append("ISSUE_TYPE_NOT_MATCHED")

        # ── Service option ────────────────────────────────────────────────────
        matched_option_id: uuid.UUID | None = None

        if service_option_id_raw:
            service_option_id = uuid.UUID(service_option_id_raw)
            if master_service_id:
                mapping = await self.db.scalar(
                    select(ServiceOptionMapping).where(
                        ServiceOptionMapping.master_service_id == master_service_id,
                        ServiceOptionMapping.service_option_id == service_option_id,
                        ServiceOptionMapping.status == "active",
                        ServiceOptionMapping.deleted_at.is_(None)))
                if not mapping:
                    return {"valid": False, "error": "SERVICE_OPTION_NOT_MAPPED_TO_SERVICE"}
            else:
                opt = await self.db.get(MasterServiceOption, service_option_id)
                if not opt or opt.status != "active":
                    return {"valid": False, "error": "SERVICE_OPTION_INACTIVE"}
            matched_option_id = service_option_id
        elif typed_option:
            options = await self.get_customer_options(master_service_id)
            for o in options:
                if typed_option in o["name"].lower() or o["name"].lower() in typed_option:
                    matched_option_id = uuid.UUID(o["service_option_id"])
                    break
            if not matched_option_id:
                result["warnings"].append("SERVICE_OPTION_NOT_MATCHED")

        result.update({
            "matched_issue_type_id":    str(matched_issue_id) if matched_issue_id else None,
            "matched_service_option_id": str(matched_option_id) if matched_option_id else None,
            "requires_photo":           requires_photo,
            "requires_description":     requires_description,
        })
        return result
