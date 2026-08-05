"""Service Types Enterprise Service — CRUD, summary, type-mappings, brand-mappings."""
from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    ServiceType, ServiceTypeMapping, BrandMapping, Brand,
    ServiceCategory, ServiceGroup, MasterService,
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
        customer_visible: bool | None = None,
        page: int = 1, page_size: int = 50, sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> dict:
        query = select(ServiceType).where(ServiceType.deleted_at.is_(None))
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

        col = getattr(ServiceType, sort_by, ServiceType.name)
        query = query.order_by(col.asc() if sort_dir == "asc" else col.desc())

        count_r = await self.db.execute(
            select(func.count()).select_from(query.subquery()))
        total = count_r.scalar_one_or_none() or 0

        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)
        rows = (await self.db.execute(query)).scalars().all()

        items = []
        for t in rows:
            mc = await self._mapping_counts(t.id)
            items.append(self._type_dict(t, mc))

        return {"types": items, "total": total, "page": page,
                "page_size": page_size, "pages": max(1, -(-total // page_size))}

    async def get_type(self, type_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id,
                                      ServiceType.deleted_at.is_(None)))
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
            await self._create_mapping_row(t.id, m)

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

        for field in ("name", "code", "description", "icon_url", "type_family", "display_order"):
            if field in data:
                setattr(t, field, data[field])
        if "customer_visible" in data:
            t.customer_visible = data["customer_visible"]
        if "status" in data:
            if data["status"] not in VALID_STATUSES:
                raise ServiceOSException("VALIDATION_ERROR",
                    f"status must be one of {sorted(VALID_STATUSES)}", status_code=422)
            t.status = data["status"]
            t.is_active = data["status"] == "active"
        t.updated_at = utcnow()
        await self.db.commit()
        await self.db.refresh(t)
        return self._type_dict(t)

    async def _set_status(self, type_id: uuid.UUID, new_status: str) -> dict:
        r = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id,
                                      ServiceType.deleted_at.is_(None)))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("ServiceType", str(type_id))
        t.status = new_status
        t.is_active = new_status == "active"
        t.updated_at = utcnow()
        await self.db.commit()
        return {"type_id": str(type_id), "status": new_status}

    async def activate_type(self, type_id: uuid.UUID) -> dict:
        return await self._set_status(type_id, "active")

    async def deactivate_type(self, type_id: uuid.UUID) -> dict:
        return await self._set_status(type_id, "inactive")

    async def archive_type(self, type_id: uuid.UUID) -> dict:
        return await self._set_status(type_id, "archived")

    async def summary(self) -> dict:
        base = select(func.count(ServiceType.id)).where(ServiceType.deleted_at.is_(None))
        total      = (await self.db.execute(base)).scalar_one_or_none() or 0
        active     = (await self.db.execute(base.where(ServiceType.status == "active"))).scalar_one_or_none() or 0
        inactive   = (await self.db.execute(base.where(ServiceType.status == "inactive"))).scalar_one_or_none() or 0
        archived   = (await self.db.execute(base.where(ServiceType.status == "archived"))).scalar_one_or_none() or 0
        cust_vis   = (await self.db.execute(base.where(ServiceType.customer_visible == True))).scalar_one_or_none() or 0

        mapped_subq = select(ServiceTypeMapping.type_id).where(
            ServiceTypeMapping.status != "archived").distinct().scalar_subquery()
        mapped   = (await self.db.execute(
            select(func.count(ServiceType.id)).where(
                ServiceType.id.in_(mapped_subq), ServiceType.deleted_at.is_(None))
        )).scalar_one_or_none() or 0
        unmapped = total - mapped

        return {"total": total, "active": active, "inactive": inactive,
                "archived": archived, "mapped": mapped, "unmapped": unmapped,
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

    async def list_type_mappings(
        self, type_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        q = select(ServiceTypeMapping)
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
        rows = (await self.db.execute(q)).scalars().all()

        # Enrich with names
        items = []
        for m in rows:
            d = self._mapping_dict(m)
            # Fetch type name
            tr = await self.db.execute(select(ServiceType).where(ServiceType.id == m.type_id))
            tp = tr.scalar_one_or_none()
            d["type_name"] = tp.name if tp else None
            # Fetch category name
            if m.category_id:
                cr = await self.db.execute(select(ServiceCategory).where(
                    ServiceCategory.id == m.category_id))
                cat = cr.scalar_one_or_none()
                d["category_name"] = cat.name if cat else None
            if m.service_id:
                svr = await self.db.execute(select(MasterService).where(
                    MasterService.id == m.service_id))
                svc = svr.scalar_one_or_none()
                d["service_name"] = getattr(svc, "name", None)
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
        await self.db.commit()
        return {"mapping_id": str(mapping_id), "deleted": True}

    # ── Brand Summary ─────────────────────────────────────────────────────────

    async def brand_summary(self) -> dict:
        base = select(func.count(Brand.id)).where(Brand.deleted_at.is_(None))
        total    = (await self.db.execute(base)).scalar_one_or_none() or 0
        active   = (await self.db.execute(base.where(Brand.status == "active"))).scalar_one_or_none() or 0
        inactive = (await self.db.execute(base.where(Brand.status == "inactive"))).scalar_one_or_none() or 0
        archived = (await self.db.execute(base.where(Brand.status == "archived"))).scalar_one_or_none() or 0
        glbl     = (await self.db.execute(base.where(Brand.is_global == True))).scalar_one_or_none() or 0

        mapped_subq = select(BrandMapping.brand_id).where(
            BrandMapping.status != "archived").distinct().scalar_subquery()
        mapped   = (await self.db.execute(
            select(func.count(Brand.id)).where(
                Brand.id.in_(mapped_subq), Brand.deleted_at.is_(None))
        )).scalar_one_or_none() or 0
        unmapped = total - mapped

        cust_vis = (await self.db.execute(
            base.where(Brand.is_active == True))).scalar_one_or_none() or 0

        return {"total": total, "active": active, "inactive": inactive, "archived": archived,
                "mapped": mapped, "unmapped": unmapped, "global": glbl,
                "customer_visible": cust_vis}

    # ── Brand Mappings ────────────────────────────────────────────────────────

    async def list_brand_mappings(
        self, brand_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None,
        service_id: uuid.UUID | None = None, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        q = select(BrandMapping)
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
        rows = (await self.db.execute(q)).scalars().all()

        items = []
        for m in rows:
            d = self._brand_mapping_dict(m)
            br = await self.db.execute(select(Brand).where(Brand.id == m.brand_id))
            brand = br.scalar_one_or_none()
            d["brand_name"] = brand.name if brand else None
            if m.category_id:
                cr = await self.db.execute(select(ServiceCategory).where(
                    ServiceCategory.id == m.category_id))
                cat = cr.scalar_one_or_none()
                d["category_name"] = cat.name if cat else None
            if m.service_id:
                svr = await self.db.execute(select(MasterService).where(
                    MasterService.id == m.service_id))
                svc = svr.scalar_one_or_none()
                d["service_name"] = getattr(svc, "name", None)
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
