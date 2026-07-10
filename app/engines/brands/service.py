"""Brand Management Service — Sprint 34D.

Handles: brand normalization, duplicate detection, full CRUD with status transitions,
category/service mapping, brand merge/alias, brand requests, brand templates,
provider supported-brand selection, customer brand catalog, and seed data.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    Brand, BrandCategoryMapping, BrandServiceOptionMapping,
    TenantSupportedBrand, BrandRequest, BrandTemplate, BrandTemplateItem,
    MasterServiceBrand, ServiceCategory, MasterService,
)
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("brands.service")
utcnow = lambda: datetime.now(timezone.utc)

VALID_BRAND_STATUSES = {"active", "inactive", "archived", "deprecated", "pending_review", "rejected"}

# 25 starter brands
STARTER_BRANDS = [
    {"name": "Samsung",      "code": "SAMSUNG",      "country_of_origin": "South Korea", "is_global": True},
    {"name": "LG",           "code": "LG",            "country_of_origin": "South Korea", "is_global": True},
    {"name": "Voltas",       "code": "VOLTAS",        "country_of_origin": "India",        "is_global": False},
    {"name": "Blue Star",    "code": "BLUE_STAR",     "country_of_origin": "India",        "is_global": False},
    {"name": "Daikin",       "code": "DAIKIN",        "country_of_origin": "Japan",        "is_global": True},
    {"name": "Hitachi",      "code": "HITACHI",       "country_of_origin": "Japan",        "is_global": True},
    {"name": "Panasonic",    "code": "PANASONIC",     "country_of_origin": "Japan",        "is_global": True},
    {"name": "Whirlpool",    "code": "WHIRLPOOL",     "country_of_origin": "USA",          "is_global": True},
    {"name": "Haier",        "code": "HAIER",         "country_of_origin": "China",        "is_global": True},
    {"name": "Godrej",       "code": "GODREJ",        "country_of_origin": "India",        "is_global": False},
    {"name": "IFB",          "code": "IFB",           "country_of_origin": "India",        "is_global": False},
    {"name": "Videocon",     "code": "VIDEOCON",      "country_of_origin": "India",        "is_global": False},
    {"name": "Bosch",        "code": "BOSCH",         "country_of_origin": "Germany",      "is_global": True},
    {"name": "Siemens",      "code": "SIEMENS",       "country_of_origin": "Germany",      "is_global": True},
    {"name": "Carrier",      "code": "CARRIER",       "country_of_origin": "USA",          "is_global": True},
    {"name": "Mitsubishi",   "code": "MITSUBISHI",    "country_of_origin": "Japan",        "is_global": True},
    {"name": "Fujitsu",      "code": "FUJITSU",       "country_of_origin": "Japan",        "is_global": True},
    {"name": "TCL",          "code": "TCL",           "country_of_origin": "China",        "is_global": True},
    {"name": "Electrolux",   "code": "ELECTROLUX",    "country_of_origin": "Sweden",       "is_global": True},
    {"name": "O General",    "code": "O_GENERAL",     "country_of_origin": "Japan",        "is_global": True},
    {"name": "Lloyd",        "code": "LLOYD",         "country_of_origin": "India",        "is_global": False},
    {"name": "Kenstar",      "code": "KENSTAR",       "country_of_origin": "India",        "is_global": False},
    {"name": "Havells",      "code": "HAVELLS",       "country_of_origin": "India",        "is_global": False},
    {"name": "Symphony",     "code": "SYMPHONY",      "country_of_origin": "India",        "is_global": False},
    {"name": "Crompton",     "code": "CROMPTON",      "country_of_origin": "India",        "is_global": False},
]


def normalize_brand_name(name: str) -> str:
    """Trim, lowercase, strip punctuation, collapse whitespace."""
    n = name.strip().lower()
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\s+", " ", n)
    return n.strip()


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class BrandService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None, request_id: str = "—"):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    # ═══════════════════════════════════════════════════════════
    # BRAND CRUD
    # ═══════════════════════════════════════════════════════════

    async def list_brands(self, status: str | None = None, is_active: bool | None = None,
                          category_id: uuid.UUID | None = None,
                          is_global: bool | None = None, q: str | None = None,
                          limit: int = 100, offset: int = 0) -> dict:
        stmt = select(Brand).where(Brand.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Brand.status == status)
        if is_active is not None:
            stmt = stmt.where(Brand.is_active == is_active)
        if is_global is not None:
            stmt = stmt.where(Brand.is_global == is_global)
        if category_id:
            # filter via BrandCategoryMapping
            sub = select(BrandCategoryMapping.brand_id).where(
                BrandCategoryMapping.category_id == category_id,
                BrandCategoryMapping.status == "active",
            )
            stmt = stmt.where(Brand.id.in_(sub))
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(Brand.name).like(like) |
                func.lower(Brand.code).like(like)
            )
        stmt = stmt.order_by(Brand.display_order, Brand.name).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        brands = result.scalars().all()
        return {"brands": [b.to_dict() for b in brands], "total": len(brands)}

    async def get_brand(self, brand_id: uuid.UUID) -> dict:
        brand = await self._load_brand(brand_id)
        data = brand.to_dict()
        # enrich with category mappings
        cm_result = await self.db.execute(
            select(BrandCategoryMapping).where(
                BrandCategoryMapping.brand_id == brand_id,
                BrandCategoryMapping.status == "active",
            )
        )
        data["category_mappings"] = [m.to_dict() for m in cm_result.scalars().all()]
        # enrich with service mappings
        sm_result = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.is_active == True,
            )
        )
        data["service_mappings"] = [m.to_dict() for m in sm_result.scalars().all()]
        return data

    async def create_brand(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("BRAND_NAME_REQUIRED", "name is required.", status_code=422)
        normalized = normalize_brand_name(name)

        # Duplicate detection
        existing = await self.db.execute(
            select(Brand).where(Brand.normalized_name == normalized, Brand.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise ServiceOSException(
                "BRAND_DUPLICATE",
                f"A brand with normalized name '{normalized}' already exists.",
                status_code=409,
            )

        slug = _slugify(data.get("slug") or name)
        slug_check = await self.db.execute(select(Brand).where(Brand.slug == slug))
        if slug_check.scalar_one_or_none():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        code = (data.get("code") or "").strip().upper() or None
        status = (data.get("status") or "active").strip()
        if status not in VALID_BRAND_STATUSES:
            raise ServiceOSException("BRAND_INVALID_STATUS",
                                     f"status must be one of {sorted(VALID_BRAND_STATUSES)}.", status_code=422)

        brand = Brand(
            name=name, slug=slug, normalized_name=normalized,
            code=code, display_name=(data.get("display_name") or name).strip(),
            status=status, is_active=(status == "active"),
            is_global=bool(data.get("is_global", True)),
            display_order=int(data.get("display_order", 0) or 0),
            logo_url=data.get("logo_url"),
            description=data.get("description"),
            website_url=data.get("website_url"),
            country_of_origin=data.get("country_of_origin"),
            alias_names_json=data.get("alias_names") or [],
            metadata_json=data.get("metadata") or {},
            created_by_user_id=self.actor_id,
            updated_by_user_id=self.actor_id,
        )
        self.db.add(brand)
        await self.db.flush()
        logger.info("brand.created", id=str(brand.id), name=name)
        return brand.to_dict()

    async def update_brand(self, brand_id: uuid.UUID, data: dict) -> dict:
        brand = await self._load_brand(brand_id)
        for field in ("display_name", "description", "website_url",
                      "country_of_origin", "display_order", "logo_url"):
            if field in data and data[field] is not None:
                setattr(brand, field, data[field])
        if "code" in data and data["code"]:
            brand.code = str(data["code"]).strip().upper()
        if "is_global" in data:
            brand.is_global = bool(data["is_global"])
        if "alias_names" in data:
            brand.alias_names_json = data["alias_names"] or []
        if "metadata" in data:
            brand.metadata_json = data["metadata"] or {}
        brand.updated_by_user_id = self.actor_id
        await self.db.flush()
        return brand.to_dict()

    async def activate_brand(self, brand_id: uuid.UUID) -> dict:
        brand = await self._load_brand(brand_id)
        brand.status = "active"
        brand.is_active = True
        brand.updated_by_user_id = self.actor_id
        await self.db.flush()
        return brand.to_dict()

    async def deactivate_brand(self, brand_id: uuid.UUID) -> dict:
        brand = await self._load_brand(brand_id)
        brand.status = "inactive"
        brand.is_active = False
        brand.updated_by_user_id = self.actor_id
        await self.db.flush()
        return brand.to_dict()

    async def archive_brand(self, brand_id: uuid.UUID) -> dict:
        brand = await self._load_brand(brand_id)
        brand.status = "archived"
        brand.is_active = False
        brand.deleted_at = utcnow()
        brand.updated_by_user_id = self.actor_id
        await self.db.flush()
        return {"archived": True, "brand_id": str(brand_id)}

    async def merge_brands(self, source_id: uuid.UUID, target_id: uuid.UUID,
                           admin_note: str | None = None) -> dict:
        source = await self._load_brand(source_id)
        target = await self._load_brand(target_id)
        if source_id == target_id:
            raise ServiceOSException("BRAND_MERGE_SAME", "Cannot merge a brand with itself.", status_code=422)

        # Point source to target as replacement
        source.status = "deprecated"
        source.is_active = False
        source.replacement_brand_id = target_id
        source.updated_by_user_id = self.actor_id

        # Add source name as alias of target
        aliases = list(target.alias_names_json or [])
        if source.name not in aliases:
            aliases.append(source.name)
        if source.normalized_name and source.normalized_name not in aliases:
            aliases.append(source.normalized_name)
        target.alias_names_json = aliases
        target.updated_by_user_id = self.actor_id

        await self.db.flush()
        logger.info("brand.merged", source=str(source_id), target=str(target_id))
        return {"merged": True, "source_brand_id": str(source_id), "target_brand_id": str(target_id)}

    # ═══════════════════════════════════════════════════════════
    # CATEGORY MAPPINGS
    # ═══════════════════════════════════════════════════════════

    async def map_categories(self, brand_id: uuid.UUID, category_ids: list[str]) -> dict:
        brand = await self._load_brand(brand_id)
        added = []
        for cat_id_str in category_ids:
            cat_id = uuid.UUID(str(cat_id_str))
            existing = await self.db.execute(
                select(BrandCategoryMapping).where(
                    BrandCategoryMapping.brand_id == brand_id,
                    BrandCategoryMapping.category_id == cat_id,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.status = "active"
            else:
                row = BrandCategoryMapping(
                    brand_id=brand_id, category_id=cat_id,
                    status="active", created_by_user_id=self.actor_id,
                )
                self.db.add(row)
            added.append(str(cat_id))
        await self.db.flush()
        return {"brand_id": str(brand_id), "mapped_categories": added}

    async def list_brand_categories(self, brand_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(BrandCategoryMapping).where(
                BrandCategoryMapping.brand_id == brand_id,
                BrandCategoryMapping.status == "active",
            )
        )
        return {"mappings": [m.to_dict() for m in result.scalars().all()]}

    # ═══════════════════════════════════════════════════════════
    # SERVICE MAPPINGS (master_service_brands)
    # ═══════════════════════════════════════════════════════════

    async def map_services(self, brand_id: uuid.UUID, service_ids: list[str]) -> dict:
        brand = await self._load_brand(brand_id)
        added = []
        for svc_id_str in service_ids:
            svc_id = uuid.UUID(str(svc_id_str))
            existing = await self.db.execute(
                select(MasterServiceBrand).where(
                    MasterServiceBrand.brand_id == brand_id,
                    MasterServiceBrand.master_service_id == svc_id,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.is_active = True
                row.status = "active"
            else:
                row = MasterServiceBrand(
                    brand_id=brand_id, master_service_id=svc_id,
                    is_active=True, status="active",
                    created_by_user_id=self.actor_id,
                )
                self.db.add(row)
            added.append(str(svc_id))
        await self.db.flush()
        return {"brand_id": str(brand_id), "mapped_services": added}

    async def list_brand_services(self, brand_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.is_active == True,
            )
        )
        return {"mappings": [m.to_dict() for m in result.scalars().all()]}

    # ═══════════════════════════════════════════════════════════
    # BRAND REQUESTS
    # ═══════════════════════════════════════════════════════════

    async def list_brand_requests(self, status: str | None = None,
                                  tenant_id: uuid.UUID | None = None) -> dict:
        stmt = select(BrandRequest)
        if status:
            stmt = stmt.where(BrandRequest.status == status)
        if tenant_id:
            stmt = stmt.where(BrandRequest.tenant_id == tenant_id)
        stmt = stmt.order_by(BrandRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return {"requests": [r.to_dict() for r in result.scalars().all()]}

    async def create_brand_request(self, data: dict, tenant_id: uuid.UUID | None = None) -> dict:
        name = (data.get("requested_brand_name") or "").strip()
        if not name:
            raise ServiceOSException("BRAND_REQUEST_NAME_REQUIRED",
                                     "requested_brand_name is required.", status_code=422)
        normalized = normalize_brand_name(name)
        req = BrandRequest(
            requested_by_user_id=self.actor_id,
            tenant_id=tenant_id,
            requested_brand_name=name,
            normalized_name=normalized,
            suggested_category_id=uuid.UUID(str(data["suggested_category_id"])) if data.get("suggested_category_id") else None,
            suggested_service_id=uuid.UUID(str(data["suggested_service_id"])) if data.get("suggested_service_id") else None,
            reason=data.get("reason"),
            status="pending",
        )
        self.db.add(req)
        await self.db.flush()
        logger.info("brand_request.created", id=str(req.id), name=name)
        return req.to_dict()

    async def approve_brand_request(self, request_id: uuid.UUID,
                                    admin_note: str | None = None) -> dict:
        req = await self._load_brand_request(request_id)
        if req.status != "pending":
            raise ServiceOSException("BRAND_REQUEST_NOT_PENDING",
                                     "Only pending requests can be approved.", status_code=409)
        req.status = "approved"
        req.admin_note = admin_note
        req.reviewed_by_user_id = self.actor_id
        req.reviewed_at = utcnow()
        await self.db.flush()
        return req.to_dict()

    async def reject_brand_request(self, request_id: uuid.UUID,
                                   admin_note: str | None = None) -> dict:
        req = await self._load_brand_request(request_id)
        if req.status != "pending":
            raise ServiceOSException("BRAND_REQUEST_NOT_PENDING",
                                     "Only pending requests can be rejected.", status_code=409)
        req.status = "rejected"
        req.admin_note = admin_note
        req.reviewed_by_user_id = self.actor_id
        req.reviewed_at = utcnow()
        await self.db.flush()
        return req.to_dict()

    async def merge_brand_request(self, request_id: uuid.UUID,
                                  matched_brand_id: uuid.UUID,
                                  admin_note: str | None = None) -> dict:
        """Mark request as matched to an existing brand (duplicate of approved brand)."""
        req = await self._load_brand_request(request_id)
        req.status = "matched"
        req.matched_brand_id = matched_brand_id
        req.admin_note = admin_note
        req.reviewed_by_user_id = self.actor_id
        req.reviewed_at = utcnow()
        await self.db.flush()
        return req.to_dict()

    # ═══════════════════════════════════════════════════════════
    # BRAND TEMPLATES
    # ═══════════════════════════════════════════════════════════

    async def list_templates(self, status: str | None = None,
                             category_id: uuid.UUID | None = None) -> dict:
        stmt = select(BrandTemplate)
        if status:
            stmt = stmt.where(BrandTemplate.status == status)
        if category_id:
            stmt = stmt.where(BrandTemplate.category_id == category_id)
        stmt = stmt.order_by(BrandTemplate.name)
        result = await self.db.execute(stmt)
        templates = result.scalars().all()
        out = []
        for t in templates:
            d = t.to_dict()
            items_result = await self.db.execute(
                select(BrandTemplateItem).where(
                    BrandTemplateItem.brand_template_id == t.id,
                    BrandTemplateItem.status == "active",
                ).order_by(BrandTemplateItem.display_order)
            )
            d["items"] = [i.to_dict() for i in items_result.scalars().all()]
            out.append(d)
        return {"templates": out}

    async def create_template(self, data: dict) -> dict:
        code = (data.get("code") or "").strip().upper()
        name = (data.get("name") or "").strip()
        if not code:
            raise ServiceOSException("TEMPLATE_CODE_REQUIRED", "code is required.", status_code=422)
        if not name:
            raise ServiceOSException("TEMPLATE_NAME_REQUIRED", "name is required.", status_code=422)
        existing = await self.db.execute(select(BrandTemplate).where(BrandTemplate.code == code))
        if existing.scalar_one_or_none():
            raise ServiceOSException("TEMPLATE_CODE_DUPLICATE",
                                     f"Template with code '{code}' already exists.", status_code=409)
        t = BrandTemplate(
            code=code, name=name, description=data.get("description"),
            category_id=uuid.UUID(str(data["category_id"])) if data.get("category_id") else None,
            vertical_type=data.get("vertical_type"),
            status="active",
        )
        self.db.add(t)
        await self.db.flush()

        # Add items (brand_ids)
        for i, brand_id_str in enumerate(data.get("brand_ids") or []):
            item = BrandTemplateItem(
                brand_template_id=t.id,
                brand_id=uuid.UUID(str(brand_id_str)),
                display_order=i,
                status="active",
            )
            self.db.add(item)
        await self.db.flush()
        return t.to_dict()

    async def apply_template(self, template_id: uuid.UUID,
                             category_id: uuid.UUID | None = None,
                             service_ids: list[str] | None = None) -> dict:
        """Apply a brand template: map all template brands to the given category/services."""
        t = await self._load_template(template_id)
        items_result = await self.db.execute(
            select(BrandTemplateItem).where(
                BrandTemplateItem.brand_template_id == template_id,
                BrandTemplateItem.status == "active",
            )
        )
        items = items_result.scalars().all()
        brand_ids = [i.brand_id for i in items]
        applied_categories = []
        applied_services = []

        if category_id:
            for bid in brand_ids:
                await self.map_categories(bid, [str(category_id)])
            applied_categories = [str(category_id)]

        if service_ids:
            for bid in brand_ids:
                await self.map_services(bid, service_ids)
            applied_services = service_ids

        return {
            "template_id": str(template_id),
            "brands_applied": len(brand_ids),
            "categories": applied_categories,
            "services": applied_services,
        }

    # ═══════════════════════════════════════════════════════════
    # PROVIDER BRAND SELECTION
    # ═══════════════════════════════════════════════════════════

    async def list_available_brands_for_service(self, master_service_id: uuid.UUID,
                                                 tenant_id: uuid.UUID | None = None) -> dict:
        """List admin-approved brands mapped to a service. Used by provider UI."""
        result = await self.db.execute(
            select(Brand).join(
                MasterServiceBrand,
                and_(
                    MasterServiceBrand.brand_id == Brand.id,
                    MasterServiceBrand.master_service_id == master_service_id,
                    MasterServiceBrand.is_active == True,
                )
            ).where(Brand.is_active == True, Brand.deleted_at.is_(None))
            .order_by(Brand.display_order, Brand.name)
        )
        brands = result.scalars().all()

        supported_ids: set[uuid.UUID] = set()
        if tenant_id:
            sup_result = await self.db.execute(
                select(TenantSupportedBrand.brand_id).where(
                    TenantSupportedBrand.tenant_id == tenant_id,
                    TenantSupportedBrand.master_service_id == master_service_id,
                    TenantSupportedBrand.status == "active",
                )
            )
            supported_ids = {row[0] for row in sup_result.all()}

        out = []
        for b in brands:
            d = b.to_dict()
            d["is_provider_supported"] = b.id in supported_ids
            out.append(d)
        return {"brands": out, "total": len(out)}

    async def set_provider_supported_brands(self, tenant_id: uuid.UUID,
                                            master_service_id: uuid.UUID,
                                            brand_ids: list[str]) -> dict:
        """Provider selects which admin-approved brands they support for a service."""
        # Validate all brand_ids are actually mapped to this service
        mapped_result = await self.db.execute(
            select(MasterServiceBrand.brand_id).where(
                MasterServiceBrand.master_service_id == master_service_id,
                MasterServiceBrand.is_active == True,
            )
        )
        valid_brand_ids = {row[0] for row in mapped_result.all()}

        enabled = []
        for bid_str in brand_ids:
            bid = uuid.UUID(str(bid_str))
            if bid not in valid_brand_ids:
                raise ServiceOSException(
                    "BRAND_NOT_MAPPED_TO_SERVICE",
                    f"Brand {bid} is not mapped to service {master_service_id}.",
                    status_code=422,
                )
            existing = await self.db.execute(
                select(TenantSupportedBrand).where(
                    TenantSupportedBrand.tenant_id == tenant_id,
                    TenantSupportedBrand.master_service_id == master_service_id,
                    TenantSupportedBrand.brand_id == bid,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.status = "active"
            else:
                row = TenantSupportedBrand(
                    tenant_id=tenant_id,
                    master_service_id=master_service_id,
                    brand_id=bid,
                    status="active",
                    created_by_user_id=self.actor_id,
                )
                self.db.add(row)
            enabled.append(str(bid))

        # Deactivate brands not in the new list
        all_result = await self.db.execute(
            select(TenantSupportedBrand).where(
                TenantSupportedBrand.tenant_id == tenant_id,
                TenantSupportedBrand.master_service_id == master_service_id,
                TenantSupportedBrand.status == "active",
            )
        )
        for row in all_result.scalars().all():
            if str(row.brand_id) not in brand_ids:
                row.status = "inactive"

        await self.db.flush()
        return {"tenant_id": str(tenant_id), "master_service_id": str(master_service_id),
                "enabled_brands": enabled}

    async def list_provider_supported_brands(self, tenant_id: uuid.UUID,
                                             master_service_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(TenantSupportedBrand).where(
                TenantSupportedBrand.tenant_id == tenant_id,
                TenantSupportedBrand.master_service_id == master_service_id,
                TenantSupportedBrand.status == "active",
            )
        )
        return {"supported_brands": [r.to_dict() for r in result.scalars().all()]}

    # ═══════════════════════════════════════════════════════════
    # CUSTOMER BRAND CATALOG (location-aware)
    # ═══════════════════════════════════════════════════════════

    async def list_customer_brands(self, master_service_id: uuid.UUID | None = None,
                                   category_id: uuid.UUID | None = None) -> dict:
        """Return only active, admin-approved brands that are mapped to services.
        No provider filtering for now (location-awareness deferred)."""
        stmt = select(Brand).where(Brand.is_active == True, Brand.deleted_at.is_(None))
        if master_service_id:
            sub = select(MasterServiceBrand.brand_id).where(
                MasterServiceBrand.master_service_id == master_service_id,
                MasterServiceBrand.is_active == True,
            )
            stmt = stmt.where(Brand.id.in_(sub))
        elif category_id:
            sub = select(BrandCategoryMapping.brand_id).where(
                BrandCategoryMapping.category_id == category_id,
                BrandCategoryMapping.status == "active",
            )
            stmt = stmt.where(Brand.id.in_(sub))
        stmt = stmt.order_by(Brand.display_order, Brand.name)
        result = await self.db.execute(stmt)
        brands = result.scalars().all()
        return {"brands": [b.to_dict() for b in brands]}

    async def validate_brand(self, brand_id: uuid.UUID,
                             master_service_id: uuid.UUID) -> dict:
        """Check if a brand is active and mapped to the given service."""
        mapping = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.master_service_id == master_service_id,
                MasterServiceBrand.is_active == True,
            )
        )
        if not mapping.scalar_one_or_none():
            return {"valid": False, "reason": "Brand not mapped to this service or inactive."}
        brand = await self._load_brand(brand_id)
        if not brand.is_active:
            return {"valid": False, "reason": "Brand is not active."}
        return {"valid": True, "brand": brand.to_dict()}

    # ═══════════════════════════════════════════════════════════
    # SEED
    # ═══════════════════════════════════════════════════════════

    async def seed_starter_brands(self) -> dict:
        """Idempotently create the 25 starter brands if they don't already exist."""
        created = 0
        for b_data in STARTER_BRANDS:
            normalized = normalize_brand_name(b_data["name"])
            existing = await self.db.execute(
                select(Brand).where(Brand.normalized_name == normalized, Brand.deleted_at.is_(None))
            )
            if existing.scalar_one_or_none():
                continue
            slug = _slugify(b_data["name"])
            slug_check = await self.db.execute(select(Brand).where(Brand.slug == slug))
            if slug_check.scalar_one_or_none():
                slug = f"{slug}-{b_data['code'].lower()}"
            brand = Brand(
                name=b_data["name"], slug=slug,
                code=b_data["code"], display_name=b_data["name"],
                normalized_name=normalized, status="active", is_active=True,
                is_global=b_data["is_global"],
                country_of_origin=b_data["country_of_origin"],
                alias_names_json=[], metadata_json={},
            )
            self.db.add(brand)
            created += 1
        await self.db.flush()
        logger.info("brands.seeded", created=created)
        return {"seeded": created}

    # ═══════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════

    async def _load_brand(self, brand_id: uuid.UUID) -> Brand:
        result = await self.db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
        )
        brand = result.scalar_one_or_none()
        if not brand:
            raise NotFoundException("Brand", str(brand_id))
        return brand

    async def _load_brand_request(self, request_id: uuid.UUID) -> BrandRequest:
        result = await self.db.execute(
            select(BrandRequest).where(BrandRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if not req:
            raise NotFoundException("BrandRequest", str(request_id))
        return req

    async def _load_template(self, template_id: uuid.UUID) -> BrandTemplate:
        result = await self.db.execute(
            select(BrandTemplate).where(BrandTemplate.id == template_id)
        )
        t = result.scalar_one_or_none()
        if not t:
            raise NotFoundException("BrandTemplate", str(template_id))
        return t
