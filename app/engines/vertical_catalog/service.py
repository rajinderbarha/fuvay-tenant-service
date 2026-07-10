"""Vertical Catalog Service — business logic."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.models import (
    Vertical, CatalogModuleDefinition, VerticalCatalogModule, VerticalMenuConfig,
    VerticalEngineMapping,
)


class VerticalCatalogService:

    # ── Verticals ─────────────────────────────────────────────────────────────

    async def list_verticals(self, db: AsyncSession, *, include_disabled: bool = False) -> list[dict]:
        q = select(Vertical).order_by(Vertical.sort_order)
        if not include_disabled:
            q = q.where(Vertical.is_enabled == True)  # noqa: E712
        rows = (await db.execute(q)).scalars().all()
        return [self._v_dict(v) for v in rows]

    async def get_vertical(self, db: AsyncSession, key: str) -> dict | None:
        v = await self._by_key(db, key)
        if not v:
            return None
        modules = await self._modules_for_vertical(db, v.id)
        d = self._v_dict(v)
        d["modules"] = modules
        return d

    async def enable_vertical(self, db: AsyncSession, key: str) -> dict:
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        v.is_enabled = True
        await db.commit()
        await db.refresh(v)
        return self._v_dict(v)

    async def disable_vertical(self, db: AsyncSession, key: str) -> dict:
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        v.is_enabled = False
        await db.commit()
        await db.refresh(v)
        return self._v_dict(v)

    async def update_vertical(self, db: AsyncSession, key: str, payload: dict) -> dict:
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        allowed = {"label", "description", "icon", "color", "sort_order", "finance_model", "meta", "is_beta"}
        for k, val in payload.items():
            if k in allowed:
                setattr(v, k, val)
        await db.commit()
        await db.refresh(v)
        return self._v_dict(v)

    # ── Catalog Modules ───────────────────────────────────────────────────────

    async def list_modules(self, db: AsyncSession) -> list[dict]:
        rows = (await db.execute(
            select(CatalogModuleDefinition).order_by(CatalogModuleDefinition.sort_order)
        )).scalars().all()
        return [self._mod_dict(m) for m in rows]

    async def toggle_module(self, db: AsyncSession, vertical_key: str, module_key: str, enabled: bool) -> dict:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        m = await self._module_by_key(db, module_key)
        if not m:
            raise ValueError(f"Module '{module_key}' not found")

        vcm = (await db.execute(
            select(VerticalCatalogModule).where(
                VerticalCatalogModule.vertical_id == v.id,
                VerticalCatalogModule.module_id == m.id,
            )
        )).scalar_one_or_none()

        if vcm:
            if vcm.is_required and not enabled:
                raise ValueError(f"Module '{module_key}' is required for this vertical and cannot be disabled")
            vcm.is_enabled = enabled
        else:
            if not enabled:
                return {"status": "no_change"}
            vcm = VerticalCatalogModule(
                vertical_id=v.id, module_id=m.id, is_enabled=True, is_required=False
            )
            db.add(vcm)

        await db.commit()
        return {"vertical_key": vertical_key, "module_key": module_key, "is_enabled": enabled}

    # ── Engine Mappings ───────────────────────────────────────────────────────

    async def list_engine_mappings(self, db: AsyncSession, vertical_key: str) -> list[dict]:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        rows = (await db.execute(
            select(VerticalEngineMapping).where(
                VerticalEngineMapping.vertical_id == v.id
            ).order_by(VerticalEngineMapping.sort_order)
        )).scalars().all()
        return [self._engine_mapping_dict(m) for m in rows]

    async def set_engine_mappings(self, db: AsyncSession, vertical_key: str, mappings: list[dict]) -> list[dict]:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        existing = (await db.execute(
            select(VerticalEngineMapping).where(VerticalEngineMapping.vertical_id == v.id)
        )).scalars().all()
        for row in existing:
            await db.delete(row)
        await db.flush()
        for i, m in enumerate(mappings):
            db.add(VerticalEngineMapping(
                vertical_id=v.id, engine_key=m["engine_key"],
                is_required=m.get("is_required", False), sort_order=m.get("sort_order", i),
            ))
        await db.commit()
        return await self.list_engine_mappings(db, vertical_key)

    def _engine_mapping_dict(self, m: VerticalEngineMapping) -> dict:
        return {
            "id": str(m.id), "vertical_id": str(m.vertical_id), "engine_key": m.engine_key,
            "is_required": m.is_required, "sort_order": m.sort_order,
        }

    # ── Effective Navigation Menu ─────────────────────────────────────────────

    # Which verticals require each cross-vertical "Operations"/"Finance" nav item.
    # Keys match the operation_visibility flags returned by get_effective_menu().
    _OPERATION_VERTICAL_RULES: dict[str, set[str]] = {
        "jobs_field_ops": {"home_services", "repair_services", "cleaning_services", "automotive"},
        "site_visits": {"real_estate"},
        "orders": {"restaurant", "product_marketplace", "marketplace_products"},
        "leads_crm": {"coaching", "real_estate", "professional_services"},
        "appointments": {"coaching", "professional_services", "real_estate"},
        # Home-Services-only finance concepts (usage credits / security deposit model —
        # never real tenant payouts; see business rules in Trust & Quality / Tenant Detail work).
        "security_deposit": {"home_services"},
        "usage_credits": {"home_services"},
    }

    async def get_effective_menu(self, db: AsyncSession) -> dict:
        """Returns the full sidebar menu config: universal modules + per-vertical enabled
        modules + cross-vertical "operation visibility" flags (Jobs/Site Visits/Orders/
        Leads CRM/Appointments/Finance items that must not show for every vertical)."""
        verticals = await self.list_verticals(db, include_disabled=True)
        modules = await self.list_modules(db)
        universal = [m for m in modules if m["is_universal"]]

        enabled_keys = {v["key"] for v in verticals if v["is_enabled"]}

        result: list[dict] = []
        for v in verticals:
            mods = await self._modules_for_vertical(db, uuid.UUID(v["id"]))
            result.append({
                "vertical_key": v["key"],
                "vertical_label": v["label"],
                "is_enabled": v["is_enabled"],
                "is_beta": v["is_beta"],
                "icon": v["icon"],
                "color": v["color"],
                "modules": [m for m in mods if m["is_enabled"]],
            })

        operation_visibility = {
            op_key: bool(enabled_keys & required_verticals)
            for op_key, required_verticals in self._OPERATION_VERTICAL_RULES.items()
        }

        return {
            "universal_modules": universal,
            "verticals": result,
            "enabled_vertical_keys": sorted(enabled_keys),
            "operation_visibility": operation_visibility,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _by_key(self, db: AsyncSession, key: str) -> Vertical | None:
        return (await db.execute(
            select(Vertical).where(Vertical.key == key)
        )).scalar_one_or_none()

    async def _module_by_key(self, db: AsyncSession, key: str) -> CatalogModuleDefinition | None:
        return (await db.execute(
            select(CatalogModuleDefinition).where(CatalogModuleDefinition.key == key)
        )).scalar_one_or_none()

    async def _modules_for_vertical(self, db: AsyncSession, vertical_id: uuid.UUID) -> list[dict]:
        rows = (await db.execute(text("""
            SELECT
                cmd.key, cmd.label, cmd.icon, cmd.admin_path, cmd.module_group,
                cmd.is_universal, cmd.sort_order,
                vcm.is_enabled, vcm.is_required, vcm.custom_label
            FROM vertical_catalog_modules vcm
            JOIN catalog_module_definitions cmd ON cmd.id = vcm.module_id
            WHERE vcm.vertical_id = :vid
            ORDER BY vcm.sort_order
        """), {"vid": str(vertical_id)})).fetchall()
        return [
            {
                "key": r.key,
                "label": r.custom_label or r.label,
                "icon": r.icon,
                "admin_path": r.admin_path,
                "module_group": r.module_group,
                "is_universal": r.is_universal,
                "is_enabled": r.is_enabled,
                "is_required": r.is_required,
            }
            for r in rows
        ]

    def _v_dict(self, v: Vertical) -> dict:
        return {
            "id": str(v.id),
            "key": v.key,
            "label": v.label,
            "description": v.description,
            "icon": v.icon,
            "color": v.color,
            "is_enabled": v.is_enabled,
            "is_beta": v.is_beta,
            "sort_order": v.sort_order,
            "finance_model": v.finance_model,
            "meta": v.meta,
        }

    def _mod_dict(self, m: CatalogModuleDefinition) -> dict:
        return {
            "id": str(m.id),
            "key": m.key,
            "label": m.label,
            "icon": m.icon,
            "admin_path": m.admin_path,
            "module_group": m.module_group,
            "is_universal": m.is_universal,
            "sort_order": m.sort_order,
        }
