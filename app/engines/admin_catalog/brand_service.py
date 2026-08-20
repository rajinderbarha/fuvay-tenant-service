"""Sprint 34D — Enterprise Brand Management Service.

Handles:
  - Brand normalization + duplicate detection
  - Brand CRUD (admin)
  - Brand ↔ category mapping
  - Brand ↔ master-service mapping (delegates to existing MasterServiceBrand)
  - Brand merge / alias
  - Brand requests (provider-submitted, admin-reviewed)
  - Brand templates (starter packs)
  - Tenant supported brands (provider selects brands per service)
  - Customer brand catalog (filtered by provider coverage)
  - Audit logging via MasterDataAuditLog
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    Brand,
    BrandCategoryMapping,
    BrandRequest,
    BrandTemplate,
    BrandTemplateItem,
    BrandServiceOptionMapping,
    MasterDataAuditLog,
    MasterService,
    MasterServiceBrand,
    ServiceCategory,
    TenantService,
    TenantServiceBrand,
    TenantSupportedBrand,
)
from app.exceptions import NotFoundException, ServiceOSException

logger = structlog.get_logger("brand_service")
utcnow = lambda: datetime.now(timezone.utc)

VALID_BRAND_STATUSES = {"active", "inactive", "archived", "deprecated", "pending_review", "rejected"}
VALID_REQUEST_STATUSES = {"pending", "approved", "rejected", "merged"}


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize_brand_name(name: str) -> str:
    """Normalize brand name for duplicate detection.

    LG = L.G. = L G
    Blue Star = Bluestar
    SAMSUNG = Samsung
    """
    n = name.strip().lower()
    # Remove dots/hyphens that are within/between letters (L.G. → lg)
    n = re.sub(r"(?<=[a-z])\.(?=[a-z])", "", n)
    n = re.sub(r"(?<=[a-z])-(?=[a-z])", "", n)
    # Remove all punctuation except spaces
    n = re.sub(r"[^\w\s]", "", n)
    # Collapse spaces
    n = re.sub(r"\s+", " ", n).strip()
    # Remove standalone qualifiers
    for suffix in (" india", " global", " international", " ltd", " pvt", " llc", " inc"):
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


# ── Service ───────────────────────────────────────────────────────────────────

class BrandService:
    def __init__(
        self,
        db: AsyncSession,
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        request_id: str = "—",
        tenant_id: uuid.UUID | None = None,
    ):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id
        self.tenant_id = tenant_id

    # ─────────────────────────────────────────────────────────
    # ADMIN BRAND CRUD
    # ─────────────────────────────────────────────────────────

    async def list_brands(
        self,
        status: str | None = None,
        category_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
        retired: bool = False,
        mapped: bool | None = None,
        has_providers: bool | None = None,
        sort_by: str = "display_order",
        sort_dir: str = "asc",
    ) -> dict:
        provider_counts = (
            select(TenantSupportedBrand.brand_id.label("brand_id"), func.count(TenantSupportedBrand.id).label("provider_count"))
            .where(TenantSupportedBrand.status == "active")
            .group_by(TenantSupportedBrand.brand_id).subquery()
        )
        category_counts = (
            select(BrandCategoryMapping.brand_id.label("brand_id"), func.count(BrandCategoryMapping.id).label("category_count"))
            .where(BrandCategoryMapping.status == "active", BrandCategoryMapping.deleted_at.is_(None))
            .group_by(BrandCategoryMapping.brand_id).subquery()
        )
        service_counts = (
            select(MasterServiceBrand.brand_id.label("brand_id"), func.count(MasterServiceBrand.id).label("service_count"))
            .where(MasterServiceBrand.is_active == True)
            .group_by(MasterServiceBrand.brand_id).subquery()
        )
        stmt = select(
            Brand,
            func.coalesce(provider_counts.c.provider_count, 0),
            func.coalesce(category_counts.c.category_count, 0),
            func.coalesce(service_counts.c.service_count, 0),
        ).outerjoin(provider_counts, provider_counts.c.brand_id == Brand.id)
        stmt = stmt.outerjoin(category_counts, category_counts.c.brand_id == Brand.id)
        stmt = stmt.outerjoin(service_counts, service_counts.c.brand_id == Brand.id)
        stmt = stmt.where(Brand.deleted_at.isnot(None) if retired else Brand.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Brand.status == status)
        elif is_active is not None:
            stmt = stmt.where(Brand.is_active == is_active)
        if category_id:
            # Filter by direct category_id OR by brand_category_mappings
            from sqlalchemy import or_, exists
            sub = (
                select(BrandCategoryMapping.brand_id)
                .where(
                    BrandCategoryMapping.category_id == category_id,
                    BrandCategoryMapping.status == "active",
                )
                .correlate(Brand)
            )
            stmt = stmt.where(
                or_(Brand.category_id == category_id, Brand.id.in_(sub))
            )
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(or_(
                func.lower(Brand.name).like(term), func.lower(Brand.slug).like(term),
                func.lower(func.coalesce(Brand.code, "")).like(term),
                func.lower(func.coalesce(Brand.normalized_name, "")).like(term),
            ))
        if mapped is not None:
            stmt = stmt.where(service_counts.c.service_count > 0 if mapped else func.coalesce(service_counts.c.service_count, 0) == 0)
        if has_providers is not None:
            stmt = stmt.where(provider_counts.c.provider_count > 0 if has_providers else func.coalesce(provider_counts.c.provider_count, 0) == 0)

        total = int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        sort_columns = {
            "name": Brand.name, "code": Brand.code, "status": Brand.status,
            "display_order": Brand.display_order, "updated_at": Brand.updated_at,
            "provider_usage_count": provider_counts.c.provider_count,
            "service_mapping_count": service_counts.c.service_count,
        }
        col = sort_columns.get(sort_by, Brand.display_order)
        direction = col.asc() if sort_dir == "asc" else col.desc()
        stmt = stmt.order_by(direction.nulls_last(), Brand.name.asc(), Brand.id.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        rows = (await self.db.execute(stmt)).all()
        enriched = []
        for brand, provider_count, category_count, service_count in rows:
            item = self._brand_dict(brand)
            item.update(provider_usage_count=int(provider_count), category_mapping_count=int(category_count),
                        service_mapping_count=int(service_count))
            enriched.append(item)
        return {
            "brands": enriched,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_brand(self, brand_id: uuid.UUID, include_retired: bool = False) -> dict:
        b = await self._load_brand_any(brand_id) if include_retired else await self._load_brand(brand_id)
        d = self._brand_dict(b)

        # Category mappings
        cat_res = await self.db.execute(
            select(BrandCategoryMapping, ServiceCategory)
            .join(ServiceCategory, ServiceCategory.id == BrandCategoryMapping.category_id)
            .where(
                BrandCategoryMapping.brand_id == brand_id,
                BrandCategoryMapping.status == "active",
            )
        )
        d["category_mappings"] = [
            {
                "mapping_id": str(m.id),
                "category_id": str(m.category_id),
                "category_name": c.name,
                "display_order": m.display_order,
            }
            for m, c in cat_res.all()
        ]

        # Service mappings
        svc_res = await self.db.execute(
            select(MasterServiceBrand, MasterService)
            .join(MasterService, MasterService.id == MasterServiceBrand.master_service_id)
            .where(
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.is_active == True,
            )
        )
        d["service_mappings"] = [
            {
                "mapping_id": str(m.id),
                "service_id": str(m.master_service_id),
                "service_name": svc.service_name,
                "is_required": m.is_required,
            }
            for m, svc in svc_res.all()
        ]

        # Provider usage
        usage_res = await self.db.execute(
            select(TenantSupportedBrand).where(
                TenantSupportedBrand.brand_id == brand_id,
                TenantSupportedBrand.status == "active",
            )
        )
        d["provider_usage_count"] = len(usage_res.scalars().all())

        return d

    async def create_brand(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("BRAND_NAME_REQUIRED", "Brand name is required.", status_code=422)

        norm = normalize_brand_name(name)
        slug = _slugify(name)

        # Duplicate slug check
        slug_res = await self.db.execute(
            select(Brand).where(Brand.slug == slug, Brand.deleted_at.is_(None))
        )
        if slug_res.scalar_one_or_none():
            raise ServiceOSException("BRAND_SLUG_ALREADY_EXISTS",
                                     f"A brand with slug '{slug}' already exists.", status_code=409)

        # Duplicate name / normalized name check
        norm_res = await self.db.execute(
            select(Brand).where(Brand.normalized_name == norm, Brand.deleted_at.is_(None))
        )
        existing_similar = norm_res.scalars().all()
        if existing_similar:
            # Return warning + possible duplicates — admin must confirm by passing force=True
            if not data.get("force"):
                return {
                    "warning": "BRAND_DUPLICATE_POSSIBLE",
                    "message": f"A brand with similar name already exists.",
                    "possible_duplicates": [self._brand_dict(b) for b in existing_similar],
                    "created": False,
                }

        # Code uniqueness
        code = (data.get("code") or "").strip().upper() or None
        if code:
            code_res = await self.db.execute(
                select(Brand).where(Brand.code == code, Brand.deleted_at.is_(None))
            )
            if code_res.scalar_one_or_none():
                raise ServiceOSException("BRAND_CODE_ALREADY_EXISTS",
                                         f"Brand code '{code}' already exists.", status_code=409)

        cat_id = uuid.UUID(str(data["category_id"])) if data.get("category_id") else None
        brand = Brand(
            name=name,
            slug=slug,
            code=code,
            display_name=data.get("display_name"),
            status=data.get("status", "active"),
            normalized_name=norm,
            alias_names_json=data.get("alias_names_json"),
            website_url=data.get("website_url"),
            country_of_origin=data.get("country_of_origin"),
            is_global=bool(data.get("is_global", True)),
            display_order=int(data.get("display_order", 0)),
            metadata_json=data.get("metadata_json"),
            logo_url=data.get("logo_url"),
            description=data.get("description"),
            is_active=data.get("status", "active") == "active",
            category_id=cat_id,
            created_by_user_id=self.actor_id,
            updated_by_user_id=self.actor_id,
        )
        self.db.add(brand)
        await self.db.flush()
        await self._audit("brand.created", "brand", brand.id, new_value={"name": name, "slug": slug})
        return {**self._brand_dict(brand), "created": True}

    async def update_brand(self, brand_id: uuid.UUID, data: dict) -> dict:
        b = await self._load_brand(brand_id)
        old = self._brand_dict(b)

        if "name" in data and data["name"]:
            b.name = data["name"].strip()
            b.normalized_name = normalize_brand_name(b.name)
        if "display_name" in data:
            b.display_name = data["display_name"]
        if "code" in data:
            b.code = (data["code"] or "").strip().upper() or None
        if "status" in data and data["status"] != b.status:
            raise ServiceOSException("LIFECYCLE_ENDPOINT_REQUIRED",
                "Use the activate, deactivate, retire, restore, or merge action for status changes.", status_code=409)
        if "logo_url" in data:
            b.logo_url = data["logo_url"]
        if "description" in data:
            b.description = data["description"]
        if "website_url" in data:
            b.website_url = data["website_url"]
        if "country_of_origin" in data:
            b.country_of_origin = data["country_of_origin"]
        if "is_global" in data:
            b.is_global = bool(data["is_global"])
        if "display_order" in data:
            b.display_order = int(data["display_order"])
        if "metadata_json" in data:
            b.metadata_json = data["metadata_json"]
        if "alias_names_json" in data:
            b.alias_names_json = data["alias_names_json"]
        if "replacement_brand_id" in data and data["replacement_brand_id"]:
            b.replacement_brand_id = uuid.UUID(str(data["replacement_brand_id"]))
        duplicate = await self.db.scalar(select(func.count(Brand.id)).where(
            Brand.id != brand_id, Brand.deleted_at.is_(None),
            or_(Brand.normalized_name == b.normalized_name,
                and_(b.code is not None, Brand.code == b.code)),
        ))
        if duplicate:
            raise ServiceOSException("BRAND_DUPLICATE", "A live brand already uses this name or code.", status_code=409)
        b.updated_by_user_id = self.actor_id

        await self.db.flush()
        new = self._brand_dict(b)
        await self._audit("brand.updated", "brand", brand_id, old_value=old, new_value=new)
        return new

    async def activate_brand(self, brand_id: uuid.UUID) -> dict:
        b = await self._load_brand(brand_id)
        b.status = "active"
        b.is_active = True
        b.updated_by_user_id = self.actor_id
        await self.db.flush()
        await self._audit("brand.activated", "brand", brand_id)
        return {"brand_id": str(brand_id), "status": "active"}

    async def deactivate_brand(self, brand_id: uuid.UUID) -> dict:
        b = await self._load_brand(brand_id)
        b.status = "inactive"
        b.is_active = False
        b.updated_by_user_id = self.actor_id
        await self.db.flush()
        await self._audit("brand.deactivated", "brand", brand_id)
        return {"brand_id": str(brand_id), "status": "inactive"}

    async def archive_brand(self, brand_id: uuid.UUID, reason: str) -> dict:
        if len(reason.strip()) < 10:
            raise ServiceOSException("RETIRE_REASON_REQUIRED", "A retirement reason of at least 10 characters is required.", status_code=422)
        b = await self._load_brand(brand_id)
        provider_count = int(await self.db.scalar(select(func.count(TenantSupportedBrand.id)).where(
            TenantSupportedBrand.brand_id == brand_id, TenantSupportedBrand.status == "active")) or 0)
        tenant_count = int(await self.db.scalar(select(func.count(TenantServiceBrand.id)).where(
            TenantServiceBrand.brand_id == brand_id, TenantServiceBrand.is_enabled == True)) or 0)
        if provider_count or tenant_count:
            raise ServiceOSException("BRAND_IN_USE", "This brand is enabled by providers. Remove provider usage or merge it before retirement.",
                                     status_code=409, context={"provider_mappings": provider_count + tenant_count})
        b.status = "archived"
        b.is_active = False
        b.deleted_at = utcnow()
        b.updated_by_user_id = self.actor_id
        await self.db.flush()
        await self._audit("brand.retired", "brand", brand_id, new_value={"reason": reason})
        return {"brand_id": str(brand_id), "status": "archived"}

    async def restore_brand(self, brand_id: uuid.UUID, reason: str) -> dict:
        if len(reason.strip()) < 10:
            raise ServiceOSException("RESTORE_REASON_REQUIRED", "A restore reason of at least 10 characters is required.", status_code=422)
        b = await self._load_brand_any(brand_id)
        if b.deleted_at is None:
            raise ServiceOSException("BRAND_NOT_RETIRED", "Only retired brands can be restored.", status_code=409)
        b.deleted_at = None; b.status = "inactive"; b.is_active = False; b.updated_by_user_id = self.actor_id
        await self.db.flush()
        await self._audit("brand.restored", "brand", brand_id, new_value={"reason": reason})
        return {"brand_id": str(brand_id), "status": "inactive"}

    async def get_brand_audit(self, brand_id: uuid.UUID, limit: int = 100) -> dict:
        rows = (await self.db.execute(select(MasterDataAuditLog).where(
            MasterDataAuditLog.entity_type == "brand", MasterDataAuditLog.entity_id == brand_id,
        ).order_by(MasterDataAuditLog.created_at.desc()).limit(min(limit, 200)))).scalars().all()
        return {"audit_log": [row.to_dict() for row in rows], "total": len(rows)}

    # ─────────────────────────────────────────────────────────
    # CATEGORY MAPPINGS
    # ─────────────────────────────────────────────────────────

    async def map_brand_to_categories(self, brand_id: uuid.UUID, category_ids: list[str]) -> dict:
        await self._load_brand(brand_id)
        mapped = []
        skipped = []
        for cat_id_str in category_ids:
            cat_id = uuid.UUID(cat_id_str)
            existing = await self.db.execute(
                select(BrandCategoryMapping).where(
                    BrandCategoryMapping.brand_id == brand_id,
                    BrandCategoryMapping.category_id == cat_id,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                if row.status != "active":
                    row.status = "active"
                    row.deleted_at = None
                    mapped.append(str(cat_id))
                else:
                    skipped.append(str(cat_id))
            else:
                m = BrandCategoryMapping(
                    brand_id=brand_id,
                    category_id=cat_id,
                    status="active",
                    created_by_user_id=self.actor_id,
                )
                self.db.add(m)
                mapped.append(str(cat_id))

        await self.db.flush()
        if mapped:
            await self._audit("brand.mapped_to_category", "brand", brand_id,
                              new_value={"category_ids": mapped})
        return {"brand_id": str(brand_id), "mapped": mapped, "skipped_already_mapped": skipped}

    async def unmap_brand_from_category(self, brand_id: uuid.UUID, category_id: uuid.UUID) -> dict:
        res = await self.db.execute(
            select(BrandCategoryMapping).where(
                BrandCategoryMapping.brand_id == brand_id,
                BrandCategoryMapping.category_id == category_id,
                BrandCategoryMapping.status == "active",
            )
        )
        mapping = res.scalar_one_or_none()
        if not mapping:
            raise NotFoundException("BrandCategoryMapping", f"{brand_id}/{category_id}")
        mapping.status = "archived"
        mapping.deleted_at = utcnow()
        await self.db.flush()
        await self._audit("brand.unmapped_from_category", "brand", brand_id,
                          new_value={"category_id": str(category_id)})
        return {"brand_id": str(brand_id), "category_id": str(category_id), "unmapped": True}

    async def list_category_mappings(self, brand_id: uuid.UUID) -> dict:
        await self._load_brand(brand_id)
        res = await self.db.execute(
            select(BrandCategoryMapping, ServiceCategory)
            .join(ServiceCategory, ServiceCategory.id == BrandCategoryMapping.category_id)
            .where(
                BrandCategoryMapping.brand_id == brand_id,
                BrandCategoryMapping.status == "active",
            )
        )
        return {
            "category_mappings": [
                {
                    "mapping_id": str(m.id),
                    "category_id": str(m.category_id),
                    "category_name": c.name,
                    "display_order": m.display_order,
                }
                for m, c in res.all()
            ]
        }

    # ─────────────────────────────────────────────────────────
    # SERVICE MAPPINGS (delegates to MasterServiceBrand)
    # ─────────────────────────────────────────────────────────

    async def map_brand_to_services(self, brand_id: uuid.UUID, service_ids: list[str]) -> dict:
        b = await self._load_brand(brand_id)
        if b.status not in ("active",):
            raise ServiceOSException("BRAND_INACTIVE", "Only active brands can be mapped to services.", status_code=422)

        mapped = []
        skipped = []
        for svc_id_str in service_ids:
            svc_id = uuid.UUID(svc_id_str)
            # Check service exists
            svc_res = await self.db.execute(
                select(MasterService).where(MasterService.id == svc_id, MasterService.is_active == True)
            )
            if not svc_res.scalar_one_or_none():
                skipped.append({"service_id": svc_id_str, "reason": "service_not_found_or_inactive"})
                continue

            # Check duplicate
            dup = await self.db.execute(
                select(MasterServiceBrand).where(
                    MasterServiceBrand.master_service_id == svc_id,
                    MasterServiceBrand.brand_id == brand_id,
                    MasterServiceBrand.is_active == True,
                )
            )
            if dup.scalar_one_or_none():
                skipped.append({"service_id": svc_id_str, "reason": "already_mapped"})
                continue

            m = MasterServiceBrand(
                master_service_id=svc_id,
                brand_id=brand_id,
                is_required=False,
                is_default=False,
                is_active=True,
            )
            self.db.add(m)
            mapped.append(svc_id_str)

        await self.db.flush()
        if mapped:
            await self._audit("brand.mapped_to_service", "brand", brand_id,
                              new_value={"service_ids": mapped})
        return {"brand_id": str(brand_id), "mapped": mapped, "skipped": skipped}

    async def list_service_mappings(self, brand_id: uuid.UUID) -> dict:
        """List all master services this brand is mapped to."""
        await self._load_brand(brand_id)
        res = await self.db.execute(
            select(MasterServiceBrand, MasterService)
            .join(MasterService, MasterService.id == MasterServiceBrand.master_service_id)
            .where(
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.is_active == True,
            )
            .order_by(MasterService.service_name)
        )
        return {
            "brand_id": str(brand_id),
            "service_mappings": [
                {
                    "mapping_id": str(m.id),
                    "service_id": str(m.master_service_id),
                    "service_name": svc.service_name,
                    "job_type": svc.job_type,
                    "is_required": m.is_required,
                    "is_default": m.is_default,
                }
                for m, svc in res.all()
            ],
        }

    async def unmap_brand_from_service(self, brand_id: uuid.UUID, service_id: uuid.UUID) -> dict:
        """Remove a brand ↔ master-service mapping (soft-deactivate)."""
        res = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.is_active == True,
            )
        )
        m = res.scalar_one_or_none()
        if not m:
            raise NotFoundException("BrandServiceMapping", f"{brand_id}/{service_id}")
        m.is_active = False
        await self.db.flush()
        await self._audit("brand.unmapped_from_service", "brand", brand_id,
                          new_value={"service_id": str(service_id)})
        return {"brand_id": str(brand_id), "service_id": str(service_id), "unmapped": True}

    async def bulk_map_brands_to_services(self, brand_ids: list[str], service_ids: list[str]) -> dict:
        """Map N brands × M services. Skips already-mapped combinations."""
        total_mapped = 0
        total_skipped = 0
        errors: list[dict] = []
        for brand_id_str in brand_ids:
            try:
                result = await self.map_brand_to_services(uuid.UUID(brand_id_str), service_ids)
                total_mapped += len(result.get("mapped", []))
                total_skipped += len(result.get("skipped", []))
            except Exception as exc:
                errors.append({"brand_id": brand_id_str, "error": str(exc)})
        return {
            "created_mappings": total_mapped,
            "skipped_existing": total_skipped,
            "errors": errors,
        }

    async def get_available_brands_for_category(self, category_id: uuid.UUID) -> dict:
        """All active brands mapped to a category — used by provider offerings view."""
        res = await self.db.execute(
            select(BrandCategoryMapping, Brand)
            .join(Brand, Brand.id == BrandCategoryMapping.brand_id)
            .where(
                BrandCategoryMapping.category_id == category_id,
                BrandCategoryMapping.status == "active",
                Brand.status == "active",
                Brand.deleted_at.is_(None),
            )
            .order_by(Brand.display_order, Brand.name)
        )
        return {
            "category_id": str(category_id),
            "brands": [
                {
                    "brand_id": str(b.id),
                    "name": b.name,
                    "display_name": b.display_name or b.name,
                    "logo_url": b.logo_url,
                }
                for _, b in res.all()
            ],
        }

    # ─────────────────────────────────────────────────────────
    # BRAND MERGE
    # ─────────────────────────────────────────────────────────

    async def merge_brand(self, source_id: uuid.UUID, target_id: uuid.UUID, admin_note: str | None = None) -> dict:
        """Merge source brand into target. Moves mappings, archives source."""
        if source_id == target_id:
            raise ServiceOSException("BRAND_MERGE_SAME", "Source and target must differ.", status_code=422)

        source = await self._load_brand(source_id)
        target = await self._load_brand(target_id)

        moved_category = 0
        moved_service = 0
        moved_provider = 0

        # Move category mappings
        src_cats = await self.db.execute(
            select(BrandCategoryMapping).where(
                BrandCategoryMapping.brand_id == source_id,
                BrandCategoryMapping.status == "active",
            )
        )
        for cm in src_cats.scalars().all():
            dup = await self.db.execute(
                select(BrandCategoryMapping).where(
                    BrandCategoryMapping.brand_id == target_id,
                    BrandCategoryMapping.category_id == cm.category_id,
                    BrandCategoryMapping.status == "active",
                )
            )
            if not dup.scalar_one_or_none():
                new_m = BrandCategoryMapping(
                    brand_id=target_id,
                    category_id=cm.category_id,
                    status="active",
                    created_by_user_id=self.actor_id,
                )
                self.db.add(new_m)
                moved_category += 1
            cm.status = "archived"

        # Move service mappings
        src_svcs = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.brand_id == source_id,
                MasterServiceBrand.is_active == True,
            )
        )
        for sm in src_svcs.scalars().all():
            dup = await self.db.execute(
                select(MasterServiceBrand).where(
                    MasterServiceBrand.brand_id == target_id,
                    MasterServiceBrand.master_service_id == sm.master_service_id,
                    MasterServiceBrand.is_active == True,
                )
            )
            if not dup.scalar_one_or_none():
                new_sm = MasterServiceBrand(
                    master_service_id=sm.master_service_id,
                    brand_id=target_id,
                    is_required=sm.is_required,
                    is_default=sm.is_default,
                    is_active=True,
                )
                self.db.add(new_sm)
                moved_service += 1
            sm.is_active = False

        # Move provider supported brands
        src_prov = await self.db.execute(
            select(TenantSupportedBrand).where(
                TenantSupportedBrand.brand_id == source_id,
                TenantSupportedBrand.status == "active",
            )
        )
        for pm in src_prov.scalars().all():
            dup = await self.db.execute(
                select(TenantSupportedBrand).where(
                    TenantSupportedBrand.tenant_id == pm.tenant_id,
                    TenantSupportedBrand.master_service_id == pm.master_service_id,
                    TenantSupportedBrand.brand_id == target_id,
                    TenantSupportedBrand.status == "active",
                )
            )
            if not dup.scalar_one_or_none():
                new_pm = TenantSupportedBrand(
                    tenant_id=pm.tenant_id,
                    master_service_id=pm.master_service_id,
                    brand_id=target_id,
                    status="active",
                    support_level=pm.support_level,
                    created_by_user_id=self.actor_id,
                )
                self.db.add(new_pm)
                moved_provider += 1
            pm.status = "archived"

        # Add source name as alias on target
        aliases: list = list(target.alias_names_json or [])
        if source.name not in aliases:
            aliases.append(source.name)
            if source.display_name and source.display_name not in aliases:
                aliases.append(source.display_name)
        target.alias_names_json = aliases

        # Archive source, point to target
        source.status = "archived"
        source.is_active = False
        source.deleted_at = utcnow()
        source.replacement_brand_id = target_id
        source.updated_by_user_id = self.actor_id

        await self.db.flush()
        await self._audit("brand.merged", "brand", source_id,
                          new_value={
                              "merged_into": str(target_id),
                              "moved_category": moved_category,
                              "moved_service": moved_service,
                              "moved_provider": moved_provider,
                              "admin_note": admin_note,
                          })
        return {
            "source_brand_id": str(source_id),
            "target_brand_id": str(target_id),
            "moved_category_mappings": moved_category,
            "moved_service_mappings": moved_service,
            "moved_provider_brands": moved_provider,
            "source_archived": True,
        }

    # ─────────────────────────────────────────────────────────
    # BRAND REQUESTS
    # ─────────────────────────────────────────────────────────

    async def list_brand_requests(
        self, status: str | None = None, tenant_id: uuid.UUID | None = None,
        search: str | None = None, page: int = 1, page_size: int = 50,
    ) -> dict:
        stmt = select(BrandRequest)
        if status:
            stmt = stmt.where(BrandRequest.status == status)
        if tenant_id:
            stmt = stmt.where(BrandRequest.tenant_id == tenant_id)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(or_(
                func.lower(BrandRequest.requested_brand_name).like(term),
                func.lower(BrandRequest.normalized_name).like(term),
                func.lower(BrandRequest.reason).like(term),
            ))
        total = int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        stmt = (stmt.order_by(BrandRequest.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size))
        res = await self.db.execute(stmt)
        return {
            "requests": [self._request_dict(r) for r in res.scalars().all()],
            "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
        }

    async def create_brand_request(self, data: dict) -> dict:
        name = (data.get("requested_brand_name") or "").strip()
        if not name:
            raise ServiceOSException("BRAND_REQUEST_NAME_REQUIRED", "Brand name is required.", status_code=422)
        norm = normalize_brand_name(name)
        req = BrandRequest(
            requested_by_user_id=self.actor_id,
            tenant_id=self.tenant_id,
            requested_brand_name=name,
            normalized_name=norm,
            suggested_category_id=uuid.UUID(str(data["suggested_category_id"])) if data.get("suggested_category_id") else None,
            suggested_service_id=uuid.UUID(str(data["suggested_service_id"])) if data.get("suggested_service_id") else None,
            reason=data.get("reason"),
            status="pending",
        )
        self.db.add(req)
        await self.db.flush()
        await self._audit("brand.requested", "brand_request", req.id,
                          new_value={"name": name, "tenant_id": str(self.tenant_id) if self.tenant_id else None})
        return self._request_dict(req)

    async def approve_brand_request(self, request_id: uuid.UUID, admin_note: str | None = None) -> dict:
        req = await self._load_request(request_id)
        if req.status != "pending":
            raise ServiceOSException("BRAND_REQUEST_NOT_PENDING", "Request is not pending.", status_code=422)

        # Create the brand
        brand_data = {
            "name": req.requested_brand_name,
            "force": True,
        }
        if req.suggested_category_id:
            brand_data["category_id"] = str(req.suggested_category_id)
        result = await self.create_brand(brand_data)
        brand_id = result.get("brand_id")

        req.status = "approved"
        req.matched_brand_id = uuid.UUID(str(brand_id)) if brand_id else None
        req.admin_note = admin_note
        req.reviewed_by_user_id = self.actor_id
        req.reviewed_at = utcnow()
        await self.db.flush()
        await self._audit("brand.request_approved", "brand_request", request_id,
                          new_value={"brand_id": brand_id, "admin_note": admin_note})
        return {**self._request_dict(req), "brand": result}

    async def reject_brand_request(self, request_id: uuid.UUID, admin_note: str | None = None) -> dict:
        req = await self._load_request(request_id)
        if req.status != "pending":
            raise ServiceOSException("BRAND_REQUEST_NOT_PENDING", "Request is not pending.", status_code=422)
        req.status = "rejected"
        req.admin_note = admin_note
        req.reviewed_by_user_id = self.actor_id
        req.reviewed_at = utcnow()
        await self.db.flush()
        await self._audit("brand.request_rejected", "brand_request", request_id,
                          new_value={"admin_note": admin_note})
        return self._request_dict(req)

    async def merge_brand_request(self, request_id: uuid.UUID, existing_brand_id: uuid.UUID, admin_note: str | None = None) -> dict:
        """Admin merges request into an existing brand (no new brand created)."""
        req = await self._load_request(request_id)
        if req.status != "pending":
            raise ServiceOSException("BRAND_REQUEST_NOT_PENDING", "Request is not pending.", status_code=422)
        target = await self._load_brand(existing_brand_id)

        # Add requested name as alias
        aliases: list = list(target.alias_names_json or [])
        if req.requested_brand_name not in aliases:
            aliases.append(req.requested_brand_name)
        target.alias_names_json = aliases
        target.updated_by_user_id = self.actor_id

        req.status = "merged"
        req.matched_brand_id = existing_brand_id
        req.admin_note = admin_note
        req.reviewed_by_user_id = self.actor_id
        req.reviewed_at = utcnow()
        await self.db.flush()
        await self._audit("brand.request_merged", "brand_request", request_id,
                          new_value={"merged_into": str(existing_brand_id), "admin_note": admin_note})
        return {**self._request_dict(req), "merged_into_brand": self._brand_dict(target)}

    # ─────────────────────────────────────────────────────────
    # BRAND TEMPLATES
    # ─────────────────────────────────────────────────────────

    async def list_brand_templates(self, status: str | None = None, category_id: uuid.UUID | None = None) -> dict:
        stmt = select(BrandTemplate)
        if status:
            stmt = stmt.where(BrandTemplate.status == status)
        if category_id:
            stmt = stmt.where(BrandTemplate.category_id == category_id)
        stmt = stmt.order_by(BrandTemplate.name)
        res = await self.db.execute(stmt)
        templates = res.scalars().all()
        result = []
        for t in templates:
            d = self._template_dict(t)
            items_res = await self.db.execute(
                select(BrandTemplateItem, Brand)
                .join(Brand, Brand.id == BrandTemplateItem.brand_id)
                .where(
                    BrandTemplateItem.brand_template_id == t.id,
                    BrandTemplateItem.status == "active",
                )
                .order_by(BrandTemplateItem.display_order)
            )
            d["items"] = [
                {"brand_id": str(i.brand_id), "brand_name": b.name, "display_order": i.display_order}
                for i, b in items_res.all()
            ]
            result.append(d)
        return {"templates": result}

    async def create_brand_template(self, data: dict) -> dict:
        code = (data.get("code") or "").strip().upper()
        if not code:
            raise ServiceOSException("TEMPLATE_CODE_REQUIRED", "Template code is required.", status_code=422)
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("TEMPLATE_NAME_REQUIRED", "Template name is required.", status_code=422)

        t = BrandTemplate(
            code=code,
            name=name,
            description=data.get("description"),
            category_id=uuid.UUID(str(data["category_id"])) if data.get("category_id") else None,
            vertical_type=data.get("vertical_type"),
            status=data.get("status", "active"),
        )
        self.db.add(t)
        await self.db.flush()

        # Add brand items
        for order, brand_id_str in enumerate(data.get("brand_ids", [])):
            item = BrandTemplateItem(
                brand_template_id=t.id,
                brand_id=uuid.UUID(brand_id_str),
                display_order=order,
                status="active",
            )
            self.db.add(item)

        await self.db.flush()
        return self._template_dict(t)

    async def apply_brand_template(self, template_id: uuid.UUID, service_ids: list[str] | None = None) -> dict:
        """Apply template: map all template brands to the given services (or template's category services)."""
        res = await self.db.execute(
            select(BrandTemplate).where(BrandTemplate.id == template_id, BrandTemplate.status == "active")
        )
        template = res.scalar_one_or_none()
        if not template:
            raise NotFoundException("BrandTemplate", str(template_id))

        # Get template brand IDs
        items_res = await self.db.execute(
            select(BrandTemplateItem).where(
                BrandTemplateItem.brand_template_id == template_id,
                BrandTemplateItem.status == "active",
            )
        )
        brand_ids = [str(item.brand_id) for item in items_res.scalars().all()]
        if not brand_ids:
            return {"template_id": str(template_id), "applied_brands": 0, "service_mappings": []}

        # Resolve service IDs
        if not service_ids:
            if template.category_id:
                svc_res = await self.db.execute(
                    select(MasterService).where(
                        MasterService.category_id == template.category_id,
                        MasterService.is_active == True,
                    )
                )
                service_ids = [str(s.id) for s in svc_res.scalars().all()]
            else:
                service_ids = []

        results = []
        for brand_id_str in brand_ids:
            brand_id = uuid.UUID(brand_id_str)
            brand_result = await self.map_brand_to_services(brand_id, service_ids or [])
            results.append(brand_result)

        return {
            "template_id": str(template_id),
            "template_name": template.name,
            "applied_brands": len(brand_ids),
            "service_mappings": results,
        }

    # ─────────────────────────────────────────────────────────
    # PROVIDER SUPPORTED BRANDS
    # ─────────────────────────────────────────────────────────

    async def get_available_brands_for_service(self, service_id: uuid.UUID) -> dict:
        """Brands admin has mapped to this service — what provider can select."""
        res = await self.db.execute(
            select(MasterServiceBrand, Brand)
            .join(Brand, Brand.id == MasterServiceBrand.brand_id)
            .where(
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.is_active == True,
                Brand.status == "active",
                Brand.deleted_at.is_(None),
            )
            .order_by(Brand.display_order, Brand.name)
        )
        return {
            "service_id": str(service_id),
            "brands": [
                {
                    "brand_id": str(b.id),
                    "name": b.name,
                    "display_name": b.display_name or b.name,
                    "logo_url": b.logo_url,
                    "is_required": m.is_required,
                    "is_default": m.is_default,
                }
                for m, b in res.all()
            ],
        }

    async def get_provider_supported_brands(self, service_id: uuid.UUID) -> dict:
        """Get brands this tenant/provider currently supports for a service."""
        if not self.tenant_id:
            raise ServiceOSException("NO_TENANT_CONTEXT", "Tenant context required.", status_code=403)
        res = await self.db.execute(
            select(TenantSupportedBrand, Brand)
            .join(Brand, Brand.id == TenantSupportedBrand.brand_id)
            .where(
                TenantSupportedBrand.tenant_id == self.tenant_id,
                TenantSupportedBrand.master_service_id == service_id,
                TenantSupportedBrand.status == "active",
            )
            .order_by(Brand.name)
        )
        return {
            "service_id": str(service_id),
            "tenant_id": str(self.tenant_id),
            "supported_brands": [
                {
                    "record_id": str(tsb.id),
                    "brand_id": str(b.id),
                    "name": b.name,
                    "display_name": b.display_name or b.name,
                    "logo_url": b.logo_url,
                    "support_level": tsb.support_level,
                    "notes": tsb.notes,
                }
                for tsb, b in res.all()
            ],
        }

    async def set_provider_supported_brands(self, service_id: uuid.UUID, brand_ids: list[str], support_level: str | None = None) -> dict:
        """Provider selects which brands they support for a service.
        Only brands admin has mapped to the service are allowed.
        """
        if not self.tenant_id:
            raise ServiceOSException("NO_TENANT_CONTEXT", "Tenant context required.", status_code=403)

        # Get admin-mapped brand IDs for this service
        allowed_res = await self.db.execute(
            select(MasterServiceBrand.brand_id).where(
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.is_active == True,
            )
        )
        allowed_ids = {str(row) for row in allowed_res.scalars().all()}

        # Validate all requested brands are allowed
        rejected = [bid for bid in brand_ids if bid not in allowed_ids]
        if rejected:
            raise ServiceOSException(
                "BRAND_NOT_SUPPORTED",
                f"These brands are not mapped to this service: {rejected}",
                status_code=422,
            )

        # Deactivate existing records not in new list
        existing_res = await self.db.execute(
            select(TenantSupportedBrand).where(
                TenantSupportedBrand.tenant_id == self.tenant_id,
                TenantSupportedBrand.master_service_id == service_id,
                TenantSupportedBrand.status == "active",
            )
        )
        existing = existing_res.scalars().all()
        existing_map = {str(e.brand_id): e for e in existing}

        new_brand_set = set(brand_ids)
        # Remove brands no longer in the list
        for bid_str, rec in existing_map.items():
            if bid_str not in new_brand_set:
                rec.status = "archived"
                rec.deleted_at = utcnow()

        added = []
        for bid_str in brand_ids:
            bid = uuid.UUID(bid_str)
            if bid_str in existing_map and existing_map[bid_str].status == "active":
                continue
            # Add or reactivate
            old_res = await self.db.execute(
                select(TenantSupportedBrand).where(
                    TenantSupportedBrand.tenant_id == self.tenant_id,
                    TenantSupportedBrand.master_service_id == service_id,
                    TenantSupportedBrand.brand_id == bid,
                )
            )
            old = old_res.scalar_one_or_none()
            if old:
                old.status = "active"
                old.deleted_at = None
                old.support_level = support_level or old.support_level
            else:
                new_rec = TenantSupportedBrand(
                    tenant_id=self.tenant_id,
                    master_service_id=service_id,
                    brand_id=bid,
                    status="active",
                    support_level=support_level,
                    created_by_user_id=self.actor_id,
                )
                self.db.add(new_rec)
            added.append(bid_str)

        await self.db.flush()
        await self._audit("provider_brand.updated", "tenant_supported_brand",
                          service_id,
                          new_value={"tenant_id": str(self.tenant_id), "brand_ids": brand_ids})
        return {
            "service_id": str(service_id),
            "tenant_id": str(self.tenant_id),
            "selected_count": len(brand_ids),
        }

    # ─────────────────────────────────────────────────────────
    # CUSTOMER CATALOG
    # ─────────────────────────────────────────────────────────

    async def get_customer_catalog_brands(
        self,
        service_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
    ) -> dict:
        """Return brands visible to customer: active + service-mapped + provider-supported."""
        stmt = (
            select(Brand, MasterServiceBrand)
            .join(MasterServiceBrand, MasterServiceBrand.brand_id == Brand.id)
            .where(
                Brand.status == "active",
                Brand.deleted_at.is_(None),
                MasterServiceBrand.is_active == True,
            )
        )
        if service_id:
            stmt = stmt.where(MasterServiceBrand.master_service_id == service_id)
        stmt = stmt.order_by(Brand.display_order, Brand.name)
        res = await self.db.execute(stmt)
        rows = res.all()

        result = []
        for b, msb in rows:
            if service_id:
                # Count providers supporting this brand for this service
                prov_res = await self.db.execute(
                    select(TenantSupportedBrand).where(
                        TenantSupportedBrand.brand_id == b.id,
                        TenantSupportedBrand.master_service_id == service_id,
                        TenantSupportedBrand.status == "active",
                    )
                )
                provider_count = len(prov_res.scalars().all())
            else:
                provider_count = 1  # All active brands shown when no service filter

            result.append({
                "brand_id": str(b.id),
                "name": b.name,
                "display_name": b.display_name or b.name,
                "logo_url": b.logo_url,
                "provider_count": provider_count,
                "is_popular": provider_count >= 3,
            })

        # Sort by provider_count desc for relevance when service is filtered
        if service_id:
            result.sort(key=lambda x: (-x["provider_count"], x["name"]))

        return {"brands": result, "total": len(result)}

    async def validate_brand(self, service_id: uuid.UUID, brand_id: uuid.UUID,
                              typed_name: str | None = None) -> dict:
        """Validate a brand is active and mapped to the given service."""
        res = await self.db.execute(
            select(Brand, MasterServiceBrand)
            .join(MasterServiceBrand, MasterServiceBrand.brand_id == Brand.id)
            .where(
                Brand.id == brand_id,
                Brand.status == "active",
                Brand.deleted_at.is_(None),
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.is_active == True,
            )
        )
        row = res.first()
        if not row:
            # Try fuzzy match by typed name
            if typed_name:
                norm = normalize_brand_name(typed_name)
                fuzzy = await self.db.execute(
                    select(Brand).where(
                        Brand.normalized_name == norm,
                        Brand.status == "active",
                        Brand.deleted_at.is_(None),
                    )
                )
                fuzzy_brand = fuzzy.scalar_one_or_none()
                if fuzzy_brand:
                    # Check if mapped
                    msb_res = await self.db.execute(
                        select(MasterServiceBrand).where(
                            MasterServiceBrand.brand_id == fuzzy_brand.id,
                            MasterServiceBrand.master_service_id == service_id,
                            MasterServiceBrand.is_active == True,
                        )
                    )
                    if msb_res.scalar_one_or_none():
                        return {
                            "valid": True,
                            "brand_id": str(fuzzy_brand.id),
                            "matched_name": fuzzy_brand.name,
                            "match_type": "fuzzy",
                        }
            return {"valid": False, "brand_id": str(brand_id), "reason": "not_mapped_or_inactive"}

        b, _ = row
        return {"valid": True, "brand_id": str(b.id), "matched_name": b.name, "match_type": "exact"}

    # ─────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────

    async def _load_brand(self, brand_id: uuid.UUID) -> Brand:
        res = await self.db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
        )
        b = res.scalar_one_or_none()
        if not b:
            raise NotFoundException("Brand", str(brand_id))
        return b

    async def _load_brand_any(self, brand_id: uuid.UUID) -> Brand:
        b = (await self.db.execute(select(Brand).where(Brand.id == brand_id))).scalar_one_or_none()
        if not b:
            raise NotFoundException("Brand", str(brand_id))
        return b

    async def _load_request(self, request_id: uuid.UUID) -> BrandRequest:
        res = await self.db.execute(select(BrandRequest).where(BrandRequest.id == request_id))
        r = res.scalar_one_or_none()
        if not r:
            raise NotFoundException("BrandRequest", str(request_id))
        return r

    def _brand_dict(self, b: Brand) -> dict:
        return {
            "brand_id": str(b.id),
            "name": b.name,
            "display_name": b.display_name or b.name,
            "slug": b.slug,
            "code": b.code,
            "status": b.status,
            "normalized_name": b.normalized_name,
            "alias_names": b.alias_names_json or [],
            "logo_url": b.logo_url,
            "description": b.description,
            "website_url": b.website_url,
            "country_of_origin": b.country_of_origin,
            "is_global": b.is_global,
            "display_order": b.display_order,
            "is_active": b.is_active,
            "category_id": str(b.category_id) if b.category_id else None,
            "replacement_brand_id": str(b.replacement_brand_id) if b.replacement_brand_id else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
            "deleted_at": b.deleted_at.isoformat() if b.deleted_at else None,
        }

    def _request_dict(self, r: BrandRequest) -> dict:
        return {
            "request_id": str(r.id),
            "tenant_id": str(r.tenant_id) if r.tenant_id else None,
            "requested_by_user_id": str(r.requested_by_user_id) if r.requested_by_user_id else None,
            "requested_brand_name": r.requested_brand_name,
            "normalized_name": r.normalized_name,
            "reason": r.reason,
            "status": r.status,
            "matched_brand_id": str(r.matched_brand_id) if r.matched_brand_id else None,
            "admin_note": r.admin_note,
            "suggested_category_id": str(r.suggested_category_id) if r.suggested_category_id else None,
            "suggested_service_id": str(r.suggested_service_id) if r.suggested_service_id else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    def _template_dict(self, t: BrandTemplate) -> dict:
        return {
            "template_id": str(t.id),
            "code": t.code,
            "name": t.name,
            "description": t.description,
            "category_id": str(t.category_id) if t.category_id else None,
            "vertical_type": t.vertical_type,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    async def seed_starter_brands(self) -> dict:
        """Idempotent: seeds 25 common brands if they don't already exist by normalized name."""
        starters = [
            {"name": "Samsung",    "code": "samsung",   "country_of_origin": "South Korea", "is_global": True},
            {"name": "LG",         "code": "lg",        "country_of_origin": "South Korea", "is_global": True},
            {"name": "Voltas",     "code": "voltas",    "country_of_origin": "India",        "is_global": False},
            {"name": "Blue Star",  "code": "blue_star", "country_of_origin": "India",        "is_global": False},
            {"name": "Daikin",     "code": "daikin",    "country_of_origin": "Japan",        "is_global": True},
            {"name": "Carrier",    "code": "carrier",   "country_of_origin": "USA",          "is_global": True},
            {"name": "Hitachi",    "code": "hitachi",   "country_of_origin": "Japan",        "is_global": True},
            {"name": "Panasonic",  "code": "panasonic", "country_of_origin": "Japan",        "is_global": True},
            {"name": "Whirlpool",  "code": "whirlpool", "country_of_origin": "USA",          "is_global": True},
            {"name": "Haier",      "code": "haier",     "country_of_origin": "China",        "is_global": True},
            {"name": "Godrej",     "code": "godrej",    "country_of_origin": "India",        "is_global": False},
            {"name": "Videocon",   "code": "videocon",  "country_of_origin": "India",        "is_global": False},
            {"name": "IFB",        "code": "ifb",       "country_of_origin": "India",        "is_global": False},
            {"name": "Bosch",      "code": "bosch",     "country_of_origin": "Germany",      "is_global": True},
            {"name": "Siemens",    "code": "siemens",   "country_of_origin": "Germany",      "is_global": True},
            {"name": "Electrolux", "code": "electrolux","country_of_origin": "Sweden",       "is_global": True},
            {"name": "Mitsubishi", "code": "mitsubishi","country_of_origin": "Japan",        "is_global": True},
            {"name": "Toshiba",    "code": "toshiba",   "country_of_origin": "Japan",        "is_global": True},
            {"name": "Sharp",      "code": "sharp",     "country_of_origin": "Japan",        "is_global": True},
            {"name": "Kenstar",    "code": "kenstar",   "country_of_origin": "India",        "is_global": False},
            {"name": "Onida",      "code": "onida",     "country_of_origin": "India",        "is_global": False},
            {"name": "TCL",        "code": "tcl",       "country_of_origin": "China",        "is_global": True},
            {"name": "Hisense",    "code": "hisense",   "country_of_origin": "China",        "is_global": True},
            {"name": "Philips",    "code": "philips",   "country_of_origin": "Netherlands",  "is_global": True},
            {"name": "Sony",       "code": "sony",      "country_of_origin": "Japan",        "is_global": True},
        ]
        seeded = skipped = 0
        for s in starters:
            norm = normalize_brand_name(s["name"])
            q = await self.db.execute(select(Brand).where(Brand.normalized_name == norm))
            if q.scalars().first():
                skipped += 1
                continue
            slug = _slugify(s["name"])
            brand = Brand(
                name=s["name"], display_name=s["name"], slug=slug,
                code=s["code"], normalized_name=norm,
                country_of_origin=s.get("country_of_origin"),
                is_global=s.get("is_global", True),
                status="active", is_active=True,
                created_by_user_id=self.actor_id,
            )
            self.db.add(brand)
            seeded += 1
        await self.db.commit()
        return {"seeded": seeded, "skipped": skipped, "total": seeded + skipped}

    async def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        old_value: dict | None = None,
        new_value: dict | None = None,
    ) -> None:
        # Use a savepoint so audit failure never rolls back the main transaction.
        try:
            async with self.db.begin_nested():
                log = MasterDataAuditLog(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action=action,
                    actor_user_id=self.actor_id,
                    actor_role=self.actor_role,
                    old_value=old_value,
                    new_value=new_value,
                    change_summary=f"{action} by {self.actor_role or 'system'}",
                    request_id=self.request_id,
                )
                self.db.add(log)
        except Exception as exc:
            logger.warning("brand_audit_failed", action=action, error=str(exc))
