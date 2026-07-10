"""Service Setup Templates — SetupTemplatesService."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.service_setup.models import (
    ServiceSetupTemplate,
    ServiceSetupTemplateModule,
    ServiceSetupTemplateItem,
    ServiceSetupTemplateVersion,
    ServiceSetupTemplateUsage,
)

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tpl_dict(t: ServiceSetupTemplate, modules: list | None = None, items: list | None = None) -> dict:
    d = t.to_dict()
    if modules is not None:
        d["modules"] = [m.to_dict() for m in modules]
        d["modules_count"] = len(modules)
    if items is not None:
        d["items"] = [i.to_dict() for i in items]
    return d


# ── Default seed data ─────────────────────────────────────────────────────────

_DEFAULT_TEMPLATES: list[dict] = [
    {
        "name": "Home Services Starter Pack",
        "code": "home_services_starter_pack",
        "description": "Complete starter pack for home services businesses including AC, plumbing, electrical, cleaning.",
        "vertical_key": "home_services",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["service_groups", "master_services", "issue_types", "service_options", "categories", "brands"],
        "items": {
            "service_groups": [
                {"item_name": "AC Services", "item_key": "ac_services"},
                {"item_name": "Plumbing", "item_key": "plumbing"},
                {"item_name": "Electrical", "item_key": "electrical"},
                {"item_name": "Cleaning", "item_key": "cleaning"},
                {"item_name": "Pest Control", "item_key": "pest_control"},
            ],
            "master_services": [
                {"item_name": "AC Repair", "item_key": "ac_repair"},
                {"item_name": "AC Installation", "item_key": "ac_installation"},
                {"item_name": "Pipe Repair", "item_key": "pipe_repair"},
                {"item_name": "Tap Installation", "item_key": "tap_installation"},
                {"item_name": "Switch Repair", "item_key": "switch_repair"},
                {"item_name": "Fan Installation", "item_key": "fan_installation"},
                {"item_name": "Home Cleaning", "item_key": "home_cleaning"},
                {"item_name": "Pest Control", "item_key": "pest_control_svc"},
            ],
            "issue_types": [
                {"item_name": "Not Cooling", "item_key": "not_cooling"},
                {"item_name": "Water Leakage", "item_key": "water_leakage"},
                {"item_name": "Power Issue", "item_key": "power_issue"},
                {"item_name": "Broken Pipe", "item_key": "broken_pipe"},
                {"item_name": "Noisy Fan", "item_key": "noisy_fan"},
            ],
            "service_options": [
                {"item_name": "Deep Cleaning", "item_key": "deep_cleaning"},
                {"item_name": "Gas Refill", "item_key": "gas_refill"},
                {"item_name": "Extra Pipe", "item_key": "extra_pipe"},
                {"item_name": "Wall Mounting", "item_key": "wall_mounting"},
                {"item_name": "Emergency Visit", "item_key": "emergency_visit"},
            ],
        },
    },
    {
        "name": "Coaching IELTS Starter Pack",
        "code": "coaching_ielts_starter_pack",
        "description": "Starter pack for coaching and IELTS preparation centers.",
        "vertical_key": "coaching_ielts",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["courses", "course_categories", "batches", "demo_class_types", "study_modes", "fee_plans"],
        "items": {},
    },
    {
        "name": "Real Estate Starter Pack",
        "code": "real_estate_starter_pack",
        "description": "Starter pack for real estate agencies including property types and listing workflows.",
        "vertical_key": "real_estate",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["property_types", "listing_types", "amenities", "localities", "site_visit_workflow"],
        "items": {},
    },
    {
        "name": "Beauty & Wellness Starter Pack",
        "code": "beauty_wellness_starter_pack",
        "description": "Starter pack for beauty salons and wellness centers.",
        "vertical_key": "beauty_wellness",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["categories", "service_groups", "master_services", "brands"],
        "items": {},
    },
    {
        "name": "Restaurant & Food Starter Pack",
        "code": "restaurant_food_starter_pack",
        "description": "Starter pack for restaurants and food delivery businesses.",
        "vertical_key": "restaurant_food",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["menu_categories", "menu_items", "variants", "add_ons", "cuisine_types"],
        "items": {},
    },
    {
        "name": "Product Marketplace Starter Pack",
        "code": "product_marketplace_starter_pack",
        "description": "Starter pack for product marketplaces including catalog and inventory.",
        "vertical_key": "product_marketplace",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["product_categories", "products", "brands", "attributes", "inventory_rules"],
        "items": {},
    },
    {
        "name": "Professional Services Starter Pack",
        "code": "professional_services_starter_pack",
        "description": "Starter pack for professional service providers like lawyers, consultants.",
        "vertical_key": "professional_services",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["service_categories_ps", "consultation_types", "document_requirements", "appointment_types"],
        "items": {},
    },
    {
        "name": "Universal Category Launch",
        "code": "universal_category_launch",
        "description": "Universal template for launching any new category.",
        "vertical_key": "universal",
        "template_type": "category_launch",
        "is_system": True,
        "modules": ["categories", "display_groups", "documents", "media_assets", "visibility_rules"],
        "items": {},
    },
    {
        "name": "Home Services Quick Setup",
        "code": "home_services_quick_setup",
        "description": "Minimal quick-setup pack for home services — just the essentials.",
        "vertical_key": "home_services",
        "template_type": "service_bundle",
        "is_system": True,
        "modules": ["service_groups", "master_services", "pricing_defaults"],
        "items": {},
    },
    {
        "name": "Provider Onboarding Pack",
        "code": "provider_onboarding_pack",
        "description": "Sets up everything needed for provider onboarding in any vertical.",
        "vertical_key": "universal",
        "template_type": "starter_pack",
        "is_system": True,
        "modules": ["categories", "documents", "workflow_mapping", "provider_setup_rules"],
        "items": {},
    },
    {
        "name": "Home Services Full Suite",
        "code": "home_services_full_suite",
        "description": "Full enterprise suite for home services — all modules included.",
        "vertical_key": "home_services",
        "template_type": "category_launch",
        "is_system": True,
        "modules": [
            "categories", "display_groups", "documents", "media_assets", "visibility_rules",
            "workflow_mapping", "service_groups", "master_services", "service_types",
            "brands", "issue_types", "service_options", "checklists",
            "provider_setup_rules", "pricing_defaults", "job_workflow",
        ],
        "items": {},
    },
]


class SetupTemplatesService:

    async def list_templates(
        self,
        db: AsyncSession,
        *,
        q: str | None = None,
        vertical: str | None = None,
        template_type: str | None = None,
        status: str | None = None,
        is_system: bool | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> dict:
        stmt = select(ServiceSetupTemplate)
        if q:
            stmt = stmt.where(or_(
                ServiceSetupTemplate.name.ilike(f"%{q}%"),
                ServiceSetupTemplate.code.ilike(f"%{q}%"),
                ServiceSetupTemplate.description.ilike(f"%{q}%"),
            ))
        if vertical:
            stmt = stmt.where(ServiceSetupTemplate.vertical_key == vertical)
        if template_type:
            stmt = stmt.where(ServiceSetupTemplate.template_type == template_type)
        if status:
            stmt = stmt.where(ServiceSetupTemplate.status == status)
        if is_system is not None:
            stmt = stmt.where(ServiceSetupTemplate.is_system == is_system)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        col = getattr(ServiceSetupTemplate, sort_by, ServiceSetupTemplate.created_at)
        if sort_dir == "asc":
            stmt = stmt.order_by(col.asc())
        else:
            stmt = stmt.order_by(col.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(stmt)
        templates = result.scalars().all()

        items = []
        for t in templates:
            mod_count_result = await db.execute(
                select(func.count()).where(ServiceSetupTemplateModule.template_id == t.id)
            )
            modules_count = mod_count_result.scalar() or 0
            d = _tpl_dict(t)
            d["modules_count"] = modules_count
            items.append(d)

        return {"items": items, "total": total}

    async def get_summary(self, db: AsyncSession) -> dict:
        total_r = await db.execute(select(func.count()).select_from(ServiceSetupTemplate))
        total = total_r.scalar() or 0

        pub_r = await db.execute(select(func.count()).select_from(ServiceSetupTemplate).where(ServiceSetupTemplate.status == "published"))
        published = pub_r.scalar() or 0

        draft_r = await db.execute(select(func.count()).select_from(ServiceSetupTemplate).where(ServiceSetupTemplate.status == "draft"))
        draft = draft_r.scalar() or 0

        sys_r = await db.execute(select(func.count()).select_from(ServiceSetupTemplate).where(ServiceSetupTemplate.is_system == True))
        system_count = sys_r.scalar() or 0

        custom_r = await db.execute(select(func.count()).select_from(ServiceSetupTemplate).where(ServiceSetupTemplate.is_system == False))
        custom_count = custom_r.scalar() or 0

        usage_r = await db.execute(select(func.count()).select_from(ServiceSetupTemplateUsage))
        recently_used = usage_r.scalar() or 0

        # Count templates with validation errors (invalid code format)
        all_r = await db.execute(select(ServiceSetupTemplate.code))
        codes = all_r.scalars().all()
        validation_errors = sum(1 for c in codes if not _CODE_RE.match(c or ""))

        return {
            "total": total,
            "published": published,
            "draft": draft,
            "system_count": system_count,
            "custom_count": custom_count,
            "recently_used": recently_used,
            "validation_errors": validation_errors,
        }

    async def get_template(self, db: AsyncSession, template_id: str) -> dict:
        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        t = t_r.scalar_one_or_none()
        if not t:
            raise ValueError(f"Template {template_id} not found")

        mod_r = await db.execute(
            select(ServiceSetupTemplateModule)
            .where(ServiceSetupTemplateModule.template_id == t.id)
            .order_by(ServiceSetupTemplateModule.display_order)
        )
        modules = mod_r.scalars().all()

        item_r = await db.execute(
            select(ServiceSetupTemplateItem)
            .where(ServiceSetupTemplateItem.template_id == t.id)
            .order_by(ServiceSetupTemplateItem.display_order)
        )
        items = item_r.scalars().all()

        return _tpl_dict(t, modules=list(modules), items=list(items))

    async def create_template(self, db: AsyncSession, payload: dict, user_id: str | None) -> dict:
        code = payload.get("code", "")
        if not _CODE_RE.match(code):
            raise ValueError(f"Invalid code format: '{code}'. Must match ^[a-z][a-z0-9_]*$")

        existing = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.code == code))
        if existing.scalar_one_or_none():
            raise ValueError(f"Template with code '{code}' already exists")

        modules_data = payload.pop("modules", [])
        items_data = payload.pop("items", {})

        t = ServiceSetupTemplate(
            id=uuid.uuid4(),
            name=payload["name"],
            code=code,
            description=payload.get("description"),
            vertical_key=payload.get("vertical_key", "universal"),
            template_type=payload.get("template_type", "starter_pack"),
            is_system=payload.get("is_system", False),
            status=payload.get("status", "draft"),
            version=payload.get("version", 1),
            display_order=payload.get("display_order", 0),
            config_json=payload.get("config_json"),
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(t)
        await db.flush()

        for i, mk in enumerate(modules_data):
            m = ServiceSetupTemplateModule(
                id=uuid.uuid4(),
                template_id=t.id,
                module_key=mk,
                module_name=mk.replace("_", " ").title(),
                is_enabled=True,
                display_order=i,
            )
            db.add(m)

        item_order = 0
        for mk, mk_items in items_data.items():
            for item in mk_items:
                it = ServiceSetupTemplateItem(
                    id=uuid.uuid4(),
                    template_id=t.id,
                    module_key=mk,
                    item_type=mk,
                    item_key=item.get("item_key", item.get("item_name", "").lower().replace(" ", "_")),
                    item_name=item.get("item_name"),
                    payload_json=item,
                    display_order=item_order,
                )
                db.add(it)
                item_order += 1

        await db.commit()
        await db.refresh(t)

        # Save version snapshot
        ver = ServiceSetupTemplateVersion(
            id=uuid.uuid4(),
            template_id=t.id,
            version=1,
            snapshot_json=t.to_dict(),
            changed_by_user_id=uuid.UUID(user_id) if user_id else None,
            change_reason="created",
        )
        db.add(ver)
        await db.commit()

        return await self.get_template(db, str(t.id))

    async def update_template(self, db: AsyncSession, template_id: str, payload: dict) -> dict:
        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        t = t_r.scalar_one_or_none()
        if not t:
            raise ValueError(f"Template {template_id} not found")

        allowed = {"name", "description", "vertical_key", "template_type", "is_system", "display_order", "config_json"}
        for k, v in payload.items():
            if k in allowed:
                setattr(t, k, v)

        await db.commit()
        await db.refresh(t)
        return await self.get_template(db, template_id)

    async def publish_template(self, db: AsyncSession, template_id: str) -> dict:
        validation = await self.validate_template(db, template_id)
        if not validation["valid"]:
            raise ValueError(f"Template has validation errors: {validation['errors']}")

        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        t = t_r.scalar_one_or_none()
        if not t:
            raise ValueError(f"Template {template_id} not found")

        t.status = "published"
        t.version = (t.version or 1) + 1
        await db.commit()
        await db.refresh(t)
        return _tpl_dict(t)

    async def archive_template(self, db: AsyncSession, template_id: str) -> dict:
        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        t = t_r.scalar_one_or_none()
        if not t:
            raise ValueError(f"Template {template_id} not found")

        t.status = "archived"
        t.archived_at = _now()
        await db.commit()
        await db.refresh(t)
        return _tpl_dict(t)

    async def clone_template(self, db: AsyncSession, template_id: str, user_id: str | None) -> dict:
        original = await self.get_template(db, template_id)
        new_code = original["code"] + "_copy"
        # ensure unique
        suffix = 1
        base_code = new_code
        while True:
            exists = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.code == new_code))
            if not exists.scalar_one_or_none():
                break
            new_code = f"{base_code}_{suffix}"
            suffix += 1

        modules = [m["module_key"] for m in original.get("modules", [])]
        items_dict: dict[str, list] = {}
        for item in original.get("items", []):
            mk = item.get("module_key", "")
            items_dict.setdefault(mk, []).append({"item_key": item["item_key"], "item_name": item["item_name"]})

        payload = {
            "name": original["name"] + " (Copy)",
            "code": new_code,
            "description": original.get("description"),
            "vertical_key": original.get("vertical_key", "universal"),
            "template_type": original.get("template_type", "starter_pack"),
            "is_system": False,
            "status": "draft",
            "modules": modules,
            "items": items_dict,
        }
        return await self.create_template(db, payload, user_id)

    async def delete_template(self, db: AsyncSession, template_id: str) -> None:
        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        t = t_r.scalar_one_or_none()
        if not t:
            raise ValueError(f"Template {template_id} not found")
        if t.status not in ("draft", "archived"):
            raise ValueError("Only draft or archived templates can be deleted")
        await db.delete(t)
        await db.commit()

    async def validate_template(self, db: AsyncSession, template_id: str) -> dict:
        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        t = t_r.scalar_one_or_none()
        if not t:
            raise ValueError(f"Template {template_id} not found")

        errors: list[str] = []
        warnings: list[str] = []

        if not _CODE_RE.match(t.code or ""):
            errors.append(f"Invalid code format: '{t.code}'")

        if not t.name or not t.name.strip():
            errors.append("Template name is required")

        mod_r = await db.execute(
            select(ServiceSetupTemplateModule).where(ServiceSetupTemplateModule.template_id == t.id)
        )
        modules = mod_r.scalars().all()
        module_keys = {m.module_key for m in modules}

        if t.vertical_key == "coaching_ielts" and "issue_types" in module_keys:
            errors.append("Coaching templates cannot include issue_types module")

        if t.vertical_key == "home_services" and "master_services" in module_keys:
            item_r = await db.execute(
                select(func.count()).select_from(ServiceSetupTemplateItem).where(
                    and_(
                        ServiceSetupTemplateItem.template_id == t.id,
                        ServiceSetupTemplateItem.module_key == "master_services",
                    )
                )
            )
            item_count = item_r.scalar() or 0
            if item_count > 0 and "service_groups" not in module_keys:
                warnings.append("Template has master_services items but no service_groups module")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    async def get_versions(self, db: AsyncSession, template_id: str) -> dict:
        t_r = await db.execute(select(ServiceSetupTemplate).where(ServiceSetupTemplate.id == uuid.UUID(template_id)))
        if not t_r.scalar_one_or_none():
            raise ValueError(f"Template {template_id} not found")

        ver_r = await db.execute(
            select(ServiceSetupTemplateVersion)
            .where(ServiceSetupTemplateVersion.template_id == uuid.UUID(template_id))
            .order_by(ServiceSetupTemplateVersion.version.desc())
        )
        versions = ver_r.scalars().all()
        return {"items": [v.to_dict() for v in versions]}

    async def seed_defaults_preview(self, db: AsyncSession) -> dict:
        existing_r = await db.execute(select(ServiceSetupTemplate.code))
        existing_codes = set(existing_r.scalars().all())

        to_create = [
            {"name": t["name"], "code": t["code"], "vertical_key": t["vertical_key"]}
            for t in _DEFAULT_TEMPLATES
            if t["code"] not in existing_codes
        ]
        return {"templates_to_create": to_create}

    async def seed_defaults(self, db: AsyncSession, user_id: str | None) -> dict:
        existing_r = await db.execute(select(ServiceSetupTemplate.code))
        existing_codes = set(existing_r.scalars().all())

        created = 0
        skipped = 0
        for tdata in _DEFAULT_TEMPLATES:
            if tdata["code"] in existing_codes:
                skipped += 1
                continue

            payload = {**tdata}
            await self.create_template(db, payload, user_id)
            created += 1

        # After seeding, publish all system templates
        sys_r = await db.execute(
            select(ServiceSetupTemplate).where(
                and_(ServiceSetupTemplate.is_system == True, ServiceSetupTemplate.status == "draft")
            )
        )
        for t in sys_r.scalars().all():
            t.status = "published"
        await db.commit()

        return {"created": created, "skipped": skipped}
