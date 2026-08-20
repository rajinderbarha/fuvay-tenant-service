"""Service Types Enterprise Service — CRUD, summary, type-mappings, brand-mappings."""
from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select, and_, or_, case, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    ServiceType, ServiceTypeMapping, BrandMapping, Brand,
    ServiceCategory, ServiceGroup, MasterService, MasterServiceType, MasterServiceBrand,
    TenantServiceType, MasterDataAuditLog,
)
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("types_service")
utcnow = lambda: datetime.now(timezone.utc)

TYPE_FAMILIES = ["appliance_type", "home_size", "vehicle_type", "fuel_type",
                 "property_type", "custom"]
VALID_STATUSES = {"active", "inactive", "archived"}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class TypesService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _type_dict(self, t: ServiceType, mapping_counts: dict | None = None) -> dict:
        mc = mapping_counts or {}
        return {
            "type_id":          str(t.id),
            "name":             t.name,
            "code":             t.code,
            "slug":             t.slug,
            "description":      t.description,
            "type_family":      t.type_family,
            "customer_visible": t.customer_visible,
            "status":           t.status,
            "display_order":    t.display_order,
            "is_active":        t.is_active,
            "icon_url":         t.icon_url,
            "category_count":   mc.get("categories", 0),
            "service_count":    mc.get("services", 0),
            "mapping_count":    mc.get("total", 0),
            "created_at":       t.created_at.isoformat(),
            "updated_at":       t.updated_at.isoformat(),
            "deleted_at":       t.deleted_at.isoformat() if t.deleted_at else None,
        }

    def _mapping_dict(self, m: ServiceTypeMapping) -> dict:
        return {
            "mapping_id":       str(m.id),
            "type_id":          str(m.type_id),
            "category_id":      str(m.category_id) if m.category_id else None,
            "service_group_id": str(m.service_group_id) if m.service_group_id else None,
            "service_id":       str(m.service_id) if m.service_id else None,
            "customer_visible": m.customer_visible,
            "provider_visible": m.provider_visible,
            "status":           m.status,
            "display_order":    m.display_order,
            "created_at":       m.created_at.isoformat(),
        }

    def _brand_mapping_dict(self, m: BrandMapping) -> dict:
        return {
            "mapping_id":       str(m.id),
            "brand_id":         str(m.brand_id),
            "category_id":      str(m.category_id) if m.category_id else None,
            "service_group_id": str(m.service_group_id) if m.service_group_id else None,
            "service_id":       str(m.service_id) if m.service_id else None,
            "customer_visible": m.customer_visible,
            "provider_visible": m.provider_visible,
            "status":           m.status,
            "display_order":    m.display_order,
            "created_at":       m.created_at.isoformat(),
        }

    async def _mapping_counts(self, type_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(func.count(ServiceTypeMapping.id)).where(
                ServiceTypeMapping.type_id == type_id,
                ServiceTypeMapping.status != "archived",
            )
        )
        total = r.scalar_one_or_none() or 0
        # BUG FIX: this counted every mapping ROW with a non-null
        # category_id, not distinct categories -- since every mapping
        # always carries category_id alongside its service_group_id (the
        # frontend sets both on create), mapping one type to 4 service
        # groups under the SAME category showed "Cat: 4" instead of the
        # correct "Cat: 1". Same distinct-ness issue applied to services.
        rc = await self.db.execute(
            select(func.count(func.distinct(ServiceTypeMapping.category_id))).where(
                ServiceTypeMapping.type_id == type_id,
                ServiceTypeMapping.category_id.isnot(None),
                ServiceTypeMapping.status != "archived",
            )
        )
        categories = rc.scalar_one_or_none() or 0
        rs = await self.db.execute(
            select(func.count(func.distinct(ServiceTypeMapping.service_id))).where(
                ServiceTypeMapping.type_id == type_id,
                ServiceTypeMapping.service_id.isnot(None),
                ServiceTypeMapping.status != "archived",
            )
        )
        services = rs.scalar_one_or_none() or 0
        return {"total": total, "categories": categories, "services": services}

    # ── Service Types CRUD ────────────────────────────────────────────────────

    async def list_types(
        self, q: str | None = None, category_id: uuid.UUID | None = None,
        status: str | None = None, mapped: bool | None = None,
        customer_visible: bool | None = None, type_family: str | None = None,
        has_providers: bool | None = None,
        page: int = 1, page_size: int = 50, sort_by: str = "name",
        sort_dir: str = "asc", retired: bool = False,
    ) -> dict:
        mapping_counts = (
            select(
                ServiceTypeMapping.type_id.label("type_id"),
                func.count(ServiceTypeMapping.id).filter(ServiceTypeMapping.status != "archived").label("mapping_count"),
                func.count(func.distinct(ServiceTypeMapping.category_id)).filter(ServiceTypeMapping.status != "archived").label("category_count"),
                func.count(func.distinct(ServiceTypeMapping.service_id)).filter(ServiceTypeMapping.status != "archived").label("service_count"),
            ).group_by(ServiceTypeMapping.type_id).subquery()
        )
        query = select(
            ServiceType,
            func.coalesce(mapping_counts.c.mapping_count, 0),
            func.coalesce(mapping_counts.c.category_count, 0),
            func.coalesce(mapping_counts.c.service_count, 0),
        ).outerjoin(mapping_counts, mapping_counts.c.type_id == ServiceType.id)
        query = query.where(
            ServiceType.deleted_at.isnot(None) if retired else ServiceType.deleted_at.is_(None)
        )
        if q:
            query = query.where(or_(
                ServiceType.name.ilike(f"%{q}%"),
                ServiceType.code.ilike(f"%{q}%"),
                ServiceType.slug.ilike(f"%{q}%"),
            ))
        if status:
            query = query.where(ServiceType.status == status)
        if customer_visible is not None:
            query = query.where(ServiceType.customer_visible == customer_visible)
        if type_family:
            query = query.where(ServiceType.type_family == type_family)
        if has_providers is not None:
            provider_exists = exists().where(
                TenantServiceType.service_type_id == ServiceType.id,
                TenantServiceType.is_enabled.is_(True),
            )
            query = query.where(provider_exists if has_providers else ~provider_exists)
        if mapped is not None:
            mapped_subq = select(ServiceTypeMapping.type_id).where(
                ServiceTypeMapping.status != "archived").distinct().scalar_subquery()
            if mapped:
                query = query.where(ServiceType.id.in_(mapped_subq))
            else:
                query = query.where(ServiceType.id.notin_(mapped_subq))
        if category_id:
            cat_subq = select(ServiceTypeMapping.type_id).where(
                ServiceTypeMapping.category_id == category_id,
                ServiceTypeMapping.status != "archived",
            ).scalar_subquery()
            query = query.where(ServiceType.id.in_(cat_subq))

        sort_columns = {
            "name": ServiceType.name, "code": ServiceType.code,
            "status": ServiceType.status, "type_family": ServiceType.type_family,
            "display_order": ServiceType.display_order, "updated_at": ServiceType.updated_at,
            "mapping_count": mapping_counts.c.mapping_count,
        }
        col = sort_columns.get(sort_by, ServiceType.name)
        direction = col.asc() if sort_dir == "asc" else col.desc()
        query = query.order_by(direction.nulls_last(), ServiceType.name.asc(), ServiceType.id.asc())

        count_r = await self.db.execute(
            select(func.count()).select_from(query.order_by(None).subquery()))
        total = count_r.scalar_one_or_none() or 0

        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)
        rows = (await self.db.execute(query)).all()
        items = [self._type_dict(t, {
            "total": int(mapping_count), "categories": int(category_count),
            "services": int(service_count),
        }) for t, mapping_count, category_count, service_count in rows]

        return {"types": items, "total": total, "page": page,
                "page_size": page_size, "pages": max(1, -(-total // page_size))}

    async def get_type(self, type_id: uuid.UUID, include_retired: bool = False) -> dict:
        r = await self.db.execute(
            select(ServiceType).where(
                ServiceType.id == type_id,
                ServiceType.deleted_at.isnot(None) if include_retired else ServiceType.deleted_at.is_(None),
            ))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("ServiceType", str(type_id))
        mc = await self._mapping_counts(t.id)
        d = self._type_dict(t, mc)
        # Fetch mappings for detail view
        mr = await self.db.execute(
            select(ServiceTypeMapping).where(
                ServiceTypeMapping.type_id == type_id,
                ServiceTypeMapping.status != "archived",
            ).order_by(ServiceTypeMapping.display_order))
        d["mappings"] = [self._mapping_dict(m) for m in mr.scalars().all()]
        return d

    async def create_type(self, data: dict) -> dict:
        name = data["name"].strip()
        slug = data.get("slug") or _slugify(name)
        code = data.get("code") or slug.upper().replace("-", "_")

        existing = await self.db.execute(
            select(ServiceType).where(ServiceType.slug == slug,
                                      ServiceType.deleted_at.is_(None)))
        if existing.scalar_one_or_none():
            raise ServiceOSException("DUPLICATE", f"Service type slug '{slug}' already exists.",
                                     status_code=409)

        t = ServiceType(
            name=name, slug=slug, code=code,
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            type_family=data.get("type_family"),
            customer_visible=data.get("customer_visible", True),
            status=data.get("status", "active"),
            display_order=data.get("display_order", 0),
            is_active=data.get("status", "active") == "active",
        )
        self.db.add(t)
        await self.db.flush()

        # Optional initial mappings
        for m in data.get("mappings", []):
            mapping = await self._create_mapping_row(t.id, m)
            await self._sync_type_mapping(mapping, active=mapping.status == "active")

        await self._audit_type(t, "service_type.created")
        await self.db.commit()
        await self.db.refresh(t)
        return self._type_dict(t)

    async def update_type(self, type_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id,
                                      ServiceType.deleted_at.is_(None)))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("ServiceType", str(type_id))

        old_name, old_code = t.name, t.code
        for field in ("name", "code", "description", "icon_url", "type_family", "display_order"):
            if field in data:
                setattr(t, field, data[field])
        if "customer_visible" in data:
            t.customer_visible = data["customer_visible"]
        if "status" in data and data["status"] != t.status:
            raise ServiceOSException("LIFECYCLE_ENDPOINT_REQUIRED",
                "Use the activate, deactivate, retire, or restore action for status changes.", status_code=409)
        duplicate = await self.db.scalar(select(func.count(ServiceType.id)).where(
            ServiceType.id != type_id, ServiceType.deleted_at.is_(None),
            or_(ServiceType.name.ilike(t.name), ServiceType.code.ilike(t.code))
        ))
        if duplicate:
            raise ServiceOSException("DUPLICATE", "A live service type already uses this name or code.", status_code=409)
        t.updated_at = utcnow()
        await self._audit_type(t, "service_type.updated", f"Updated {old_name} ({old_code})")
        await self.db.commit()
        await self.db.refresh(t)
        return self._type_dict(t)

    async def _set_status(self, type_id: uuid.UUID, new_status: str, reason: str | None = None) -> dict:
        r = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id,
                                      ServiceType.deleted_at.is_(None)))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("ServiceType", str(type_id))
        t.status = new_status
        t.is_active = new_status == "active"
        t.updated_at = utcnow()
        await self._audit_type(t, f"service_type.{new_status}", reason)
        await self.db.commit()
        return {"type_id": str(type_id), "status": new_status}

    async def activate_type(self, type_id: uuid.UUID) -> dict:
        return await self._set_status(type_id, "active")

    async def deactivate_type(self, type_id: uuid.UUID) -> dict:
        return await self._set_status(type_id, "inactive")

    async def archive_type(self, type_id: uuid.UUID, reason: str) -> dict:
        if len(reason.strip()) < 10:
            raise ServiceOSException("RETIRE_REASON_REQUIRED", "A retirement reason of at least 10 characters is required.", status_code=422)
        in_use = await self.db.scalar(select(func.count(TenantServiceType.id)).where(
            TenantServiceType.service_type_id == type_id, TenantServiceType.is_enabled == True))
        if in_use:
            raise ServiceOSException("SERVICE_TYPE_IN_USE", "This type is enabled by providers. Deactivate provider usage before retiring it.", status_code=409,
                                     context={"provider_mappings": int(in_use)})
        t = (await self.db.execute(select(ServiceType).where(
            ServiceType.id == type_id, ServiceType.deleted_at.is_(None)))).scalar_one_or_none()
        if not t:
            raise NotFoundException("ServiceType", str(type_id))
        t.status = "archived"; t.is_active = False; t.deleted_at = utcnow(); t.updated_at = utcnow()
        await self._audit_type(t, "service_type.retired", reason)
        await self.db.commit()
        return {"type_id": str(type_id), "status": "archived"}

    async def restore_type(self, type_id: uuid.UUID, reason: str) -> dict:
        if len(reason.strip()) < 10:
            raise ServiceOSException("RESTORE_REASON_REQUIRED", "A restore reason of at least 10 characters is required.", status_code=422)
        t = (await self.db.execute(select(ServiceType).where(
            ServiceType.id == type_id, ServiceType.deleted_at.isnot(None)))).scalar_one_or_none()
        if not t:
            raise NotFoundException("ServiceType", str(type_id))
        t.deleted_at = None; t.status = "inactive"; t.is_active = False; t.updated_at = utcnow()
        await self._audit_type(t, "service_type.restored", reason)
        await self.db.commit()
        return {"type_id": str(type_id), "status": "inactive"}

    async def get_type_audit(self, type_id: uuid.UUID, limit: int = 100) -> dict:
        rows = (await self.db.execute(select(MasterDataAuditLog).where(
            MasterDataAuditLog.entity_type == "service_type",
            MasterDataAuditLog.entity_id == type_id,
        ).order_by(MasterDataAuditLog.created_at.desc()).limit(min(limit, 200)))).scalars().all()
        return {"audit_log": [row.to_dict() for row in rows], "total": len(rows)}

    async def _audit_type(self, t: ServiceType, action: str, reason: str | None = None) -> None:
        self.db.add(MasterDataAuditLog(
            entity_type="service_type", entity_id=t.id, action=action,
            actor_user_id=self.actor_id, actor_role=self.actor_role,
            new_value={"name": t.name, "status": t.status, "reason": reason},
            change_summary=reason or action, request_id=self.request_id,
        ))
        await self.db.flush()

    async def summary(self) -> dict:
        totals = (await self.db.execute(select(
            func.count(ServiceType.id).filter(ServiceType.deleted_at.is_(None)),
            func.count(ServiceType.id).filter(ServiceType.deleted_at.is_(None), ServiceType.status == "active"),
            func.count(ServiceType.id).filter(ServiceType.deleted_at.is_(None), ServiceType.status == "inactive"),
            func.count(ServiceType.id).filter(ServiceType.deleted_at.isnot(None)),
            func.count(ServiceType.id).filter(ServiceType.deleted_at.is_(None), ServiceType.customer_visible.is_(True)),
        ))).one()
        total, active, inactive, retired, cust_vis = (int(v or 0) for v in totals)

        mapped_subq = select(ServiceTypeMapping.type_id).where(
            ServiceTypeMapping.status != "archived").distinct().scalar_subquery()
        mapped   = (await self.db.execute(
            select(func.count(ServiceType.id)).where(
                ServiceType.id.in_(mapped_subq), ServiceType.deleted_at.is_(None))
        )).scalar_one_or_none() or 0
        unmapped = total - mapped

        return {"total": total, "active": active, "inactive": inactive,
                "archived": retired, "retired": retired, "mapped": mapped, "unmapped": unmapped,
                "customer_visible": cust_vis}

    # ── Type Mappings ─────────────────────────────────────────────────────────

    async def _create_mapping_row(self, type_id: uuid.UUID, data: dict) -> ServiceTypeMapping:
        category_id = uuid.UUID(data["category_id"]) if data.get("category_id") else None
        service_group_id = uuid.UUID(data["service_group_id"]) if data.get("service_group_id") else None
        service_id = uuid.UUID(data["service_id"]) if data.get("service_id") else None

        # The uq_stm_type_cat_grp_svc UNIQUE constraint does NOT prevent
        # duplicates in practice: service_id (and often service_group_id) is
        # NULL for "all services in group" mappings, and Postgres treats
        # NULLs as never-equal, so the constraint silently never fires for
        # them. That let the same type->category/group mapping be inserted
        # unlimited times -- e.g. "Split AC / Air Conditioning" existed 9x,
        # showing duplicate rows in the Type Mappings tab and duplicate
        # "Currently Mapped" entries in the Map Type modal.
        # Guarded here at the application layer instead, using IS NULL so
        # NULL columns compare correctly. Reactivates an archived duplicate
        # rather than stacking another row on top of it.
        dup_q = select(ServiceTypeMapping).where(
            ServiceTypeMapping.type_id == type_id,
            ServiceTypeMapping.category_id == category_id if category_id is not None
                else ServiceTypeMapping.category_id.is_(None),
            ServiceTypeMapping.service_group_id == service_group_id if service_group_id is not None
                else ServiceTypeMapping.service_group_id.is_(None),
            ServiceTypeMapping.service_id == service_id if service_id is not None
                else ServiceTypeMapping.service_id.is_(None),
        )
        existing = (await self.db.execute(dup_q)).scalars().first()
        if existing:
            existing.status = data.get("status", "active")
            existing.customer_visible = data.get("customer_visible", True)
            existing.provider_visible = data.get("provider_visible", True)
            await self.db.flush()
            return existing

        m = ServiceTypeMapping(
            type_id=type_id,
            category_id=category_id,
            service_group_id=service_group_id,
            service_id=service_id,
            customer_visible=data.get("customer_visible", True),
            provider_visible=data.get("provider_visible", True),
            status=data.get("status", "active"),
            display_order=data.get("display_order", 0),
        )
        self.db.add(m)
        await self.db.flush()
        return m

    async def _mapping_service_ids(self, category_id: uuid.UUID | None,
                                   group_id: uuid.UUID | None,
                                   service_id: uuid.UUID | None) -> list[uuid.UUID]:
        if not any((category_id, group_id, service_id)):
            raise ServiceOSException("MAPPING_SCOPE_REQUIRED",
                "Select a category, service group, or master service.", status_code=422)
        q = select(MasterService.id).where(MasterService.deleted_at.is_(None))
        if service_id:
            q = q.where(MasterService.id == service_id)
        if group_id:
            q = q.where(MasterService.service_group_id == group_id)
        if category_id:
            q = q.where(MasterService.category_id == category_id)
        ids = list((await self.db.execute(q)).scalars().all())
        if service_id and not ids:
            raise ServiceOSException("INVALID_MAPPING_HIERARCHY",
                "The selected service does not belong to the selected category/group.", status_code=422)
        return ids

    async def _sync_type_mapping(self, m: ServiceTypeMapping, active: bool) -> None:
        service_ids = await self._mapping_service_ids(m.category_id, m.service_group_id, m.service_id)
        for service_id in service_ids:
            if not active and await self._type_has_other_scope(m, service_id):
                continue
            row = (await self.db.execute(select(MasterServiceType).where(
                MasterServiceType.master_service_id == service_id,
                MasterServiceType.service_type_id == m.type_id,
            ))).scalar_one_or_none()
            if row:
                row.is_active = active
            elif active:
                self.db.add(MasterServiceType(master_service_id=service_id,
                                               service_type_id=m.type_id, is_active=True))
        await self.db.flush()

    async def _type_has_other_scope(self, mapping: ServiceTypeMapping, service_id: uuid.UUID) -> bool:
        svc = (await self.db.execute(select(MasterService).where(MasterService.id == service_id))).scalar_one()
        return bool(await self.db.scalar(select(func.count(ServiceTypeMapping.id)).where(
            ServiceTypeMapping.id != mapping.id, ServiceTypeMapping.type_id == mapping.type_id,
            ServiceTypeMapping.status == "active",
            or_(ServiceTypeMapping.service_id == service_id,
                and_(ServiceTypeMapping.service_id.is_(None), ServiceTypeMapping.service_group_id == svc.service_group_id),
                and_(ServiceTypeMapping.service_id.is_(None), ServiceTypeMapping.service_group_id.is_(None),
                     ServiceTypeMapping.category_id == svc.category_id)),
        )))

    async def _sync_brand_mapping(self, m: BrandMapping, active: bool) -> None:
        service_ids = await self._mapping_service_ids(m.category_id, m.service_group_id, m.service_id)
        for service_id in service_ids:
            if not active and await self._brand_has_other_scope(m, service_id):
                continue
            row = (await self.db.execute(select(MasterServiceBrand).where(
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.brand_id == m.brand_id,
            ))).scalar_one_or_none()
            if row:
                row.is_active = active
                row.status = "active" if active else "inactive"
            elif active:
                self.db.add(MasterServiceBrand(master_service_id=service_id,
                    brand_id=m.brand_id, is_active=True, status="active",
                    created_by_user_id=self.actor_id))
        await self.db.flush()

    async def _brand_has_other_scope(self, mapping: BrandMapping, service_id: uuid.UUID) -> bool:
        svc = (await self.db.execute(select(MasterService).where(MasterService.id == service_id))).scalar_one()
        return bool(await self.db.scalar(select(func.count(BrandMapping.id)).where(
            BrandMapping.id != mapping.id, BrandMapping.brand_id == mapping.brand_id,
            BrandMapping.status == "active",
            or_(BrandMapping.service_id == service_id,
                and_(BrandMapping.service_id.is_(None), BrandMapping.service_group_id == svc.service_group_id),
                and_(BrandMapping.service_id.is_(None), BrandMapping.service_group_id.is_(None),
                     BrandMapping.category_id == svc.category_id)),
        )))

    async def _audit_mapping(self, entity_type: str, entity_id: uuid.UUID,
                             action: str, value: dict | None = None) -> None:
        self.db.add(MasterDataAuditLog(
            entity_type=entity_type, entity_id=entity_id, action=action,
            actor_user_id=self.actor_id, actor_role=self.actor_role,
            new_value=value, change_summary=action, request_id=self.request_id,
        ))
        await self.db.flush()

    async def list_type_mappings(
        self, type_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        q = (select(ServiceTypeMapping, ServiceType.name, ServiceCategory.name,
                    ServiceGroup.name, MasterService.service_name)
             .join(ServiceType, ServiceType.id == ServiceTypeMapping.type_id)
             .outerjoin(ServiceCategory, ServiceCategory.id == ServiceTypeMapping.category_id)
             .outerjoin(ServiceGroup, ServiceGroup.id == ServiceTypeMapping.service_group_id)
             .outerjoin(MasterService, MasterService.id == ServiceTypeMapping.service_id))
        if type_id:
            q = q.where(ServiceTypeMapping.type_id == type_id)
        if category_id:
            q = q.where(ServiceTypeMapping.category_id == category_id)
        if service_id:
            q = q.where(ServiceTypeMapping.service_id == service_id)
        if status:
            q = q.where(ServiceTypeMapping.status == status)
        else:
            q = q.where(ServiceTypeMapping.status != "archived")

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery()))).scalar_one_or_none() or 0
        q = q.order_by(ServiceTypeMapping.display_order).limit(page_size).offset((page-1)*page_size)
        rows = (await self.db.execute(q)).all()
        items = []
        for m, type_name, category_name, group_name, service_name in rows:
            d = self._mapping_dict(m)
            d.update(type_name=type_name, category_name=category_name,
                     group_name=group_name, service_name=service_name)
            items.append(d)

        return {"mappings": items, "total": total, "page": page, "page_size": page_size}

    async def create_type_mapping(self, data: dict) -> dict:
        type_id = uuid.UUID(data["type_id"])
        tr = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id,
                                      ServiceType.deleted_at.is_(None)))
        if not tr.scalar_one_or_none():
            raise NotFoundException("ServiceType", str(type_id))
        m = await self._create_mapping_row(type_id, data)
        await self._sync_type_mapping(m, active=m.status == "active")
        await self._audit_mapping("service_type_mapping", m.id, "mapping.created", data)
        await self.db.commit()
        await self.db.refresh(m)
        return self._mapping_dict(m)

    async def update_type_mapping(self, mapping_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(
            select(ServiceTypeMapping).where(ServiceTypeMapping.id == mapping_id))
        m = r.scalar_one_or_none()
        if not m:
            raise NotFoundException("ServiceTypeMapping", str(mapping_id))
        for field in ("customer_visible", "provider_visible", "status", "display_order"):
            if field in data:
                setattr(m, field, data[field])
        m.updated_at = utcnow()
        await self._sync_type_mapping(m, active=m.status == "active")
        await self._audit_mapping("service_type_mapping", m.id, "mapping.updated", data)
        await self.db.commit()
        return self._mapping_dict(m)

    async def delete_type_mapping(self, mapping_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(ServiceTypeMapping).where(ServiceTypeMapping.id == mapping_id))
        m = r.scalar_one_or_none()
        if not m:
            raise NotFoundException("ServiceTypeMapping", str(mapping_id))
        m.status = "archived"
        m.updated_at = utcnow()
        await self._sync_type_mapping(m, active=False)
        await self._audit_mapping("service_type_mapping", m.id, "mapping.retired")
        await self.db.commit()
        return {"mapping_id": str(mapping_id), "deleted": True}

    # ── Brand Summary ─────────────────────────────────────────────────────────

    async def brand_summary(self) -> dict:
        totals = (await self.db.execute(select(
            func.count(Brand.id).filter(Brand.deleted_at.is_(None)),
            func.count(Brand.id).filter(Brand.deleted_at.is_(None), Brand.status == "active"),
            func.count(Brand.id).filter(Brand.deleted_at.is_(None), Brand.status == "inactive"),
            func.count(Brand.id).filter(Brand.deleted_at.isnot(None)),
            func.count(Brand.id).filter(Brand.deleted_at.is_(None), Brand.is_global.is_(True)),
        ))).one()
        total, active, inactive, retired, glbl = (int(v or 0) for v in totals)

        mapped_subq = select(MasterServiceBrand.brand_id).where(
            MasterServiceBrand.is_active.is_(True)).distinct().scalar_subquery()
        mapped   = (await self.db.execute(
            select(func.count(Brand.id)).where(
                Brand.id.in_(mapped_subq), Brand.deleted_at.is_(None))
        )).scalar_one_or_none() or 0
        unmapped = total - mapped

        cust_vis = int(await self.db.scalar(select(func.count(Brand.id)).where(
            Brand.deleted_at.is_(None), Brand.is_active.is_(True))) or 0)

        return {"total": total, "active": active, "inactive": inactive, "archived": retired, "retired": retired,
                "mapped": mapped, "unmapped": unmapped, "global": glbl,
                "customer_visible": cust_vis}

    # ── Brand Mappings ────────────────────────────────────────────────────────

    async def list_brand_mappings(
        self, brand_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        q = (select(BrandMapping, Brand.name, ServiceCategory.name,
                    ServiceGroup.name, MasterService.service_name)
             .join(Brand, Brand.id == BrandMapping.brand_id)
             .outerjoin(ServiceCategory, ServiceCategory.id == BrandMapping.category_id)
             .outerjoin(ServiceGroup, ServiceGroup.id == BrandMapping.service_group_id)
             .outerjoin(MasterService, MasterService.id == BrandMapping.service_id))
        if brand_id:
            q = q.where(BrandMapping.brand_id == brand_id)
        if category_id:
            q = q.where(BrandMapping.category_id == category_id)
        if service_id:
            q = q.where(BrandMapping.service_id == service_id)
        if status:
            q = q.where(BrandMapping.status == status)
        else:
            q = q.where(BrandMapping.status != "archived")

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery()))).scalar_one_or_none() or 0
        q = q.order_by(BrandMapping.display_order).limit(page_size).offset((page-1)*page_size)
        rows = (await self.db.execute(q)).all()

        items = []
        for m, brand_name, category_name, group_name, service_name in rows:
            d = self._brand_mapping_dict(m)
            d.update(brand_name=brand_name, category_name=category_name,
                     group_name=group_name, service_name=service_name)
            items.append(d)

        return {"mappings": items, "total": total, "page": page, "page_size": page_size}

    async def create_brand_mapping(self, data: dict) -> dict:
        brand_id = uuid.UUID(data["brand_id"])
        br = await self.db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None)))
        if not br.scalar_one_or_none():
            raise NotFoundException("Brand", str(brand_id))

        category_id = uuid.UUID(data["category_id"]) if data.get("category_id") else None
        service_group_id = uuid.UUID(data["service_group_id"]) if data.get("service_group_id") else None
        service_id = uuid.UUID(data["service_id"]) if data.get("service_id") else None

        # Same NULL-defeats-UNIQUE duplicate problem as _create_mapping_row
        # above -- see that method's comment for the full explanation.
        dup_q = select(BrandMapping).where(
            BrandMapping.brand_id == brand_id,
            BrandMapping.category_id == category_id if category_id is not None
                else BrandMapping.category_id.is_(None),
            BrandMapping.service_group_id == service_group_id if service_group_id is not None
                else BrandMapping.service_group_id.is_(None),
            BrandMapping.service_id == service_id if service_id is not None
                else BrandMapping.service_id.is_(None),
        )
        existing = (await self.db.execute(dup_q)).scalars().first()
        if existing:
            existing.status = data.get("status", "active")
            existing.customer_visible = data.get("customer_visible", True)
            existing.provider_visible = data.get("provider_visible", True)
            await self.db.flush()
            await self._sync_brand_mapping(existing, active=existing.status == "active")
            await self._audit_mapping("brand_mapping", existing.id, "mapping.reactivated", data)
            await self.db.commit()
            await self.db.refresh(existing)
            return self._brand_mapping_dict(existing)

        m = BrandMapping(
            brand_id=brand_id,
            category_id=category_id,
            service_group_id=service_group_id,
            service_id=service_id,
            customer_visible=data.get("customer_visible", True),
            provider_visible=data.get("provider_visible", True),
            status=data.get("status", "active"),
            display_order=data.get("display_order", 0),
        )
        self.db.add(m)
        await self.db.flush()
        await self._sync_brand_mapping(m, active=m.status == "active")
        await self._audit_mapping("brand_mapping", m.id, "mapping.created", data)
        await self.db.commit()
        await self.db.refresh(m)
        return self._brand_mapping_dict(m)

    async def update_brand_mapping(self, mapping_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(
            select(BrandMapping).where(BrandMapping.id == mapping_id))
        m = r.scalar_one_or_none()
        if not m:
            raise NotFoundException("BrandMapping", str(mapping_id))
        for field in ("customer_visible", "provider_visible", "status", "display_order"):
            if field in data:
                setattr(m, field, data[field])
        m.updated_at = utcnow()
        await self._sync_brand_mapping(m, active=m.status == "active")
        await self._audit_mapping("brand_mapping", m.id, "mapping.updated", data)
        await self.db.commit()
        return self._brand_mapping_dict(m)

    async def delete_brand_mapping(self, mapping_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(BrandMapping).where(BrandMapping.id == mapping_id))
        m = r.scalar_one_or_none()
        if not m:
            raise NotFoundException("BrandMapping", str(mapping_id))
        m.status = "archived"
        m.updated_at = utcnow()
        await self._sync_brand_mapping(m, active=False)
        await self._audit_mapping("brand_mapping", m.id, "mapping.retired")
        await self.db.commit()
        return {"mapping_id": str(mapping_id), "deleted": True}

    # ── Export ────────────────────────────────────────────────────────────────

    async def export_types(self) -> list[dict]:
        rows = (await self.db.execute(
            select(ServiceType).where(ServiceType.deleted_at.is_(None))
            .order_by(ServiceType.name)
        )).scalars().all()
        return [self._type_dict(t) for t in rows]

    async def export_type_mappings(self) -> list[dict]:
        r = await self.list_type_mappings(page_size=5000)
        return r["mappings"]

    async def export_brand_mappings(self) -> list[dict]:
        r = await self.list_brand_mappings(page_size=5000)
        return r["mappings"]
