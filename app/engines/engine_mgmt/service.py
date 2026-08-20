"""Enterprise Engine Management service."""
import time
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.engine_mgmt.models import (
    PlatformEngine, EngineDependency, CategoryEngineMatrix,
    PackageEngineEntitlement, TenantEngineOverride,
    EngineHealthCheck, EnginePermission, EngineAuditLog,
)
from app.exceptions import ServiceOSException
from app.engine_registry.registry import registry as runtime_registry

log = structlog.get_logger("engine_mgmt.service")


def _now() -> datetime:
    return datetime.now(timezone.utc)


VALID_OVERRIDE_TYPES = {
    "grant", "revoke", "temporary_grant", "temporary_revoke",
    "force_disable", "beta_access",
}

# Historical database identifiers are retained for audit compatibility, but the
# runtime registry is the canonical identity used by the application.  Keeping
# the translation in one place prevents the admin console from presenting old
# subsystem names as separate live engines.
LEGACY_ENGINE_ALIASES: dict[str, str] = {
    "auth_iam": "auth",
    "ai_workflow": "workflow",
    "badge_engine": "trust_quality",
    "badge_rule_engine": "trust_quality",
    "health_engine": "trust_quality",
    "health_rule_engine": "trust_quality",
    "risk_scoring_engine": "trust_quality",
    "rule_simulator_engine": "trust_quality",
    "recalculation_job_engine": "trust_quality",
    "trust_quality_engine": "trust_quality",
    "customer_svc_credit": "platform_commerce",
    "finance": "platform_commerce",
    "commission": "platform_commerce",
    "package_credit": "platform_commerce",
    "food_menu": "food",
    "job_dispatch": "dispatch",
    "leads_crm": "leads",
    "loyalty_rewards": "loyalty",
    "media_vault": "media",
    "review_rating": "review",
    "settings_config": "settings",
    "security": "auth",
}


def _canonical_engine_key(engine_key: str) -> str:
    return LEGACY_ENGINE_ALIASES.get(engine_key, engine_key)


def _is_prefix_mounted(api_prefix: str, route_paths: set[str]) -> bool:
    """Return whether the FastAPI application exposes an engine prefix.

    Registry prefixes may include a path parameter.  Matching the stable part
    makes the check useful for templated admin routes without executing a
    mutating endpoint.
    """
    stable = api_prefix.split("{", 1)[0].rstrip("/")
    if not stable:
        return False
    return any(path == stable or path.startswith(stable + "/") for path in route_paths)

# ── Category Engine Matrix — recommended default templates ────────────────────
CATEGORY_ENGINE_TEMPLATES: dict[str, dict] = {
    "home_services_default": {
        "vertical_type": "home_services",
        "required": ["auth_iam", "service_catalog", "pricing", "booking", "field_ops",
                     "notification", "finance", "package_credit", "complaint_dispute",
                     "customer_svc_credit", "audit", "security"],
        "optional": ["rag", "analytics", "review_rating", "marketing", "loyalty_rewards",
                     "chat", "bargain"],
    },
    "real_estate_default": {
        "vertical_type": "real_estate",
        "required": ["auth_iam", "media_vault", "leads_crm", "notification", "audit", "security"],
        "optional": ["appointment", "analytics", "marketing", "chat"],
    },
    "restaurant_default": {
        "vertical_type": "restaurant",
        "required": ["auth_iam", "food_menu", "notification", "audit", "security"],
        "optional": ["inventory", "payment", "analytics", "marketing"],
    },
    "coaching_default": {
        "vertical_type": "coaching",
        "required": ["auth_iam", "appointment", "notification", "pricing", "audit", "security"],
        "optional": ["chat", "analytics", "marketing", "review_rating"],
    },
    "professional_services_default": {
        "vertical_type": "professional_services",
        "required": ["auth_iam", "service_catalog", "booking", "notification", "pricing",
                     "audit", "security"],
        "optional": ["analytics", "marketing", "review_rating", "chat"],
    },
    "marketplace_products_default": {
        "vertical_type": "marketplace_products",
        "required": ["auth_iam", "inventory", "payment", "notification", "audit", "security"],
        "optional": ["analytics", "marketing", "loyalty_rewards", "review_rating"],
    },
}


def _template_for_vertical(vertical_type: str | None) -> str | None:
    if not vertical_type:
        return None
    for key, tpl in CATEGORY_ENGINE_TEMPLATES.items():
        if tpl["vertical_type"] == vertical_type:
            return key
    return None


class EngineMgmtService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str = "super_admin"):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role

    # ── Audit helper ──────────────────────────────────────────────────────────

    def _audit(self, action_type: str, engine_key: str | None = None,
               engine_id: uuid.UUID | None = None,
               scope_type: str = "global", scope_id: uuid.UUID | None = None,
               old_value: dict | None = None, new_value: dict | None = None,
               reason: str | None = None) -> None:
        self.db.add(EngineAuditLog(
            engine_id=engine_id,
            engine_key=engine_key,
            action_type=action_type,
            scope_type=scope_type,
            scope_id=scope_id,
            actor_user_id=self.actor_id,
            actor_role=self.actor_role,
            old_value_json=old_value,
            new_value_json=new_value,
            reason=reason,
            created_at=_now(),
        ))

    # ── Engine helpers ─────────────────────────────────────────────────────────

    async def _get_engine(self, engine_key: str) -> PlatformEngine:
        e = await self.db.scalar(
            select(PlatformEngine).where(PlatformEngine.engine_key == engine_key))
        if not e:
            raise ServiceOSException("NOT_FOUND", f"Engine '{engine_key}' not found.")
        return e

    # ── Registry / List ────────────────────────────────────────────────────────

    async def list_engines(self, engine_type: str | None = None,
                            global_status: str | None = None,
                            lifecycle_status: str | None = None,
                            is_core: bool | None = None,
                            q: str | None = None,
                            page: int = 1, limit: int = 50) -> dict:
        stmt = select(PlatformEngine).order_by(
            PlatformEngine.is_core.desc(), PlatformEngine.display_name)
        if engine_type:
            stmt = stmt.where(PlatformEngine.engine_type == engine_type)
        if global_status:
            stmt = stmt.where(PlatformEngine.global_status == global_status)
        if lifecycle_status:
            stmt = stmt.where(PlatformEngine.lifecycle_status == lifecycle_status)
        if is_core is not None:
            stmt = stmt.where(PlatformEngine.is_core == is_core)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                (PlatformEngine.display_name.ilike(like)) |
                (PlatformEngine.engine_key.ilike(like)))

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "engines": [e.to_dict() for e in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit,
                     "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
        }

    async def get_summary(self) -> dict:
        total = await self.db.scalar(select(func.count()).select_from(PlatformEngine))
        enabled = await self.db.scalar(
            select(func.count()).select_from(PlatformEngine).where(
                PlatformEngine.global_status.in_(["enabled", "locked"])))
        disabled = await self.db.scalar(
            select(func.count()).select_from(PlatformEngine).where(
                PlatformEngine.global_status == "disabled"))
        core_locked = await self.db.scalar(
            select(func.count()).select_from(PlatformEngine).where(
                PlatformEngine.is_locked == True))
        beta = await self.db.scalar(
            select(func.count()).select_from(PlatformEngine).where(
                PlatformEngine.lifecycle_status == "beta"))

        cat_mapped = await self.db.scalar(
            select(func.count(CategoryEngineMatrix.engine_id.distinct())))
        pkg_entitled = await self.db.scalar(
            select(func.count(PackageEngineEntitlement.engine_id.distinct())).where(
                PackageEngineEntitlement.is_included == True))
        overrides = await self.db.scalar(
            select(func.count()).select_from(TenantEngineOverride).where(
                TenantEngineOverride.status == "active"))

        latest_health = await self.db.execute(
            text("""
                SELECT engine_key, health_status
                FROM engine_health_checks ehc
                WHERE checked_at = (
                    SELECT MAX(checked_at) FROM engine_health_checks e2
                    WHERE e2.engine_key = ehc.engine_key
                )
            """))
        health_rows = latest_health.fetchall()
        degraded = sum(1 for _, hs in health_rows if hs == "degraded")
        down = sum(1 for _, hs in health_rows if hs == "down")

        return {
            "total_engines": total or 0,
            "enabled_globally": enabled or 0,
            "disabled": disabled or 0,
            "core_locked": core_locked or 0,
            "beta_engines": beta or 0,
            "category_mapped": cat_mapped or 0,
            "package_entitled": pkg_entitled or 0,
            "tenant_overrides_active": overrides or 0,
            "degraded_or_down": degraded + down,
        }

    async def get_control_plane(self, route_paths: set[str]) -> dict:
        """Runtime-aware engine inventory used by the admin command centre.

        ``platform_engines`` remains the governance/audit store.  The running
        FastAPI route table is the truth for whether an engine is actually
        mounted, while ``engine_registry`` supplies canonical metadata.  This
        endpoint deliberately exposes drift instead of labelling every seeded
        database row as healthy.
        """
        db_engines = (await self.db.execute(
            select(PlatformEngine).order_by(PlatformEngine.display_name)
        )).scalars().all()
        db_by_canonical: dict[str, list[PlatformEngine]] = {}
        for row in db_engines:
            db_by_canonical.setdefault(_canonical_engine_key(row.engine_key), []).append(row)

        vertical_rows = (await self.db.execute(text("""
            SELECT v.key AS vertical_key, v.label AS vertical_label,
                   v.is_enabled AS vertical_enabled, vem.engine_key,
                   vem.is_required
            FROM vertical_engine_mappings vem
            JOIN verticals v ON v.id = vem.vertical_id
            ORDER BY v.sort_order, vem.sort_order
        """))).mappings().all()
        usage_by_engine: dict[str, list[dict]] = {}
        for row in vertical_rows:
            canonical = _canonical_engine_key(row["engine_key"])
            usage_by_engine.setdefault(canonical, []).append({
                "vertical_key": row["vertical_key"],
                "vertical_label": row["vertical_label"],
                "vertical_enabled": bool(row["vertical_enabled"]),
                "required": bool(row["is_required"]),
                "source_key": row["engine_key"],
            })

        latest_health_rows = (await self.db.execute(text("""
            SELECT DISTINCT ON (engine_key)
                   engine_key, health_status, checked_at, error_message
            FROM engine_health_checks
            ORDER BY engine_key, checked_at DESC
        """))).mappings().all()
        health_by_canonical: dict[str, dict] = {}
        for row in latest_health_rows:
            health_by_canonical[_canonical_engine_key(row["engine_key"])] = dict(row)

        items: list[dict] = []
        registered_keys = set()
        for definition in sorted(runtime_registry.all(), key=lambda item: (item.category, item.name)):
            registered_keys.add(definition.engine_id)
            matches = db_by_canonical.get(definition.engine_id, [])
            primary = next((m for m in matches if m.engine_key == definition.engine_id), None)
            primary = primary or (matches[0] if matches else None)
            mounted = _is_prefix_mounted(definition.api_prefix, route_paths)
            enabled_records = [m for m in matches if m.global_status in ("enabled", "locked")]
            configured = bool(enabled_records)
            enabled_verticals = [
                row for row in usage_by_engine.get(definition.engine_id, [])
                if row["vertical_enabled"]
            ]
            in_current_scope = bool(enabled_verticals) or definition.engine_type == "core"
            health = health_by_canonical.get(definition.engine_id)
            alias_keys = sorted(m.engine_key for m in matches if m.engine_key != definition.engine_id)
            if mounted and configured:
                runtime_state = "operational"
            elif mounted and in_current_scope:
                runtime_state = "unconfigured"
            elif configured and in_current_scope:
                runtime_state = "configured_not_mounted"
            else:
                runtime_state = "inactive"
            items.append({
                "engine_key": definition.engine_id,
                "display_name": definition.name,
                "description": definition.description,
                "engine_type": definition.engine_type,
                "category": definition.category,
                "version": definition.version,
                "api_prefix": definition.api_prefix,
                "endpoint_count": definition.endpoint_count,
                "dependencies": definition.dependencies,
                "registered": True,
                "mounted": mounted,
                "configured": configured,
                "runtime_state": runtime_state,
                "global_status": primary.global_status if primary else "not_configured",
                "is_core": bool(primary.is_core) if primary else definition.engine_type == "core",
                "is_locked": bool(primary.is_locked) if primary else False,
                "lifecycle_status": primary.lifecycle_status if primary else "registry_only",
                "database_key": primary.engine_key if primary else None,
                "legacy_aliases": alias_keys,
                "vertical_usage": usage_by_engine.get(definition.engine_id, []),
                "active_vertical_count": len(enabled_verticals),
                "last_health": {
                    "status": health["health_status"],
                    "checked_at": health["checked_at"].isoformat(),
                    "error": health["error_message"],
                } if health else None,
            })

        orphaned = []
        for canonical, rows in db_by_canonical.items():
            if canonical in registered_keys:
                continue
            for row in rows:
                if row.lifecycle_status in ("retired", "archived"):
                    continue
                orphaned.append({
                    "engine_key": row.engine_key,
                    "display_name": row.display_name,
                    "global_status": row.global_status,
                    "lifecycle_status": row.lifecycle_status,
                    "reason": "No canonical runtime registration",
                })

        mounted_count = sum(1 for item in items if item["mounted"])
        operational_count = sum(1 for item in items if item["runtime_state"] == "operational")
        drift_count = sum(1 for item in items if item["runtime_state"] in {
            "unconfigured", "configured_not_mounted"
        }) + len(orphaned)
        legacy_alias_count = sum(len(item["legacy_aliases"]) for item in items)
        enabled_vertical_count = len({
            row["vertical_key"] for row in vertical_rows if row["vertical_enabled"]
        })
        return {
            "summary": {
                "registered": len(items),
                "mounted": mounted_count,
                "operational": operational_count,
                "configuration_drift": drift_count,
                "legacy_aliases": legacy_alias_count,
                "orphaned_records": len(orphaned),
                "enabled_verticals": enabled_vertical_count,
            },
            "engines": items,
            "orphaned_records": orphaned,
            "generated_at": _now().isoformat(),
        }

    async def get_vertical_usage(self) -> dict:
        rows = (await self.db.execute(text("""
            SELECT v.id, v.key, v.label, v.is_enabled, v.lifecycle_status,
                   v.release_stage, vem.engine_key, vem.is_required,
                   vem.sort_order
            FROM verticals v
            LEFT JOIN vertical_engine_mappings vem ON vem.vertical_id = v.id
            ORDER BY v.is_enabled DESC, v.sort_order, vem.sort_order
        """))).mappings().all()
        grouped: dict[str, dict] = {}
        registered = {definition.engine_id for definition in runtime_registry.all()}
        for row in rows:
            vertical = grouped.setdefault(row["key"], {
                "id": str(row["id"]),
                "key": row["key"],
                "label": row["label"],
                "is_enabled": bool(row["is_enabled"]),
                "lifecycle_status": row["lifecycle_status"],
                "release_stage": row["release_stage"],
                "engines": [],
            })
            if not row["engine_key"]:
                continue
            canonical = _canonical_engine_key(row["engine_key"])
            vertical["engines"].append({
                "engine_key": canonical,
                "source_key": row["engine_key"],
                "is_required": bool(row["is_required"]),
                "registered": canonical in registered,
                "uses_legacy_alias": canonical != row["engine_key"],
            })
        verticals = list(grouped.values())
        return {
            "verticals": verticals,
            "summary": {
                "total": len(verticals),
                "enabled": sum(1 for row in verticals if row["is_enabled"]),
                "disabled": sum(1 for row in verticals if not row["is_enabled"]),
                "mapping_count": sum(len(row["engines"]) for row in verticals),
                "legacy_mapping_count": sum(
                    1 for row in verticals for item in row["engines"]
                    if item["uses_legacy_alias"]
                ),
            },
        }

    async def get_engine(self, engine_key: str) -> dict:
        e = await self._get_engine(engine_key)
        result = e.to_dict()

        # Dependencies
        deps = (await self.db.execute(
            select(EngineDependency).where(
                EngineDependency.engine_key == engine_key,
                EngineDependency.status == "active")
        )).scalars().all()
        result["dependencies"] = [d.to_dict() for d in deps]

        # Dependent engines (who depends on this)
        dependents = (await self.db.execute(
            select(EngineDependency).where(
                EngineDependency.depends_on_engine_key == engine_key,
                EngineDependency.status == "active")
        )).scalars().all()
        result["dependent_engines"] = [d.engine_key for d in dependents]

        # Latest health check
        health = await self.db.scalar(
            select(EngineHealthCheck).where(
                EngineHealthCheck.engine_key == engine_key
            ).order_by(EngineHealthCheck.checked_at.desc()).limit(1))
        result["latest_health"] = health.to_dict() if health else None

        # Category count
        cat_count = await self.db.scalar(
            select(func.count()).select_from(CategoryEngineMatrix).where(
                CategoryEngineMatrix.engine_key == engine_key,
                CategoryEngineMatrix.is_enabled == True))
        result["category_usage_count"] = cat_count or 0

        # Package count
        pkg_count = await self.db.scalar(
            select(func.count()).select_from(PackageEngineEntitlement).where(
                PackageEngineEntitlement.engine_key == engine_key,
                PackageEngineEntitlement.is_included == True))
        result["package_usage_count"] = pkg_count or 0

        # Active overrides
        override_count = await self.db.scalar(
            select(func.count()).select_from(TenantEngineOverride).where(
                TenantEngineOverride.engine_key == engine_key,
                TenantEngineOverride.status == "active"))
        result["active_overrides"] = override_count or 0

        return result

    # ── Create / Update ────────────────────────────────────────────────────────

    async def create_engine(self, data: dict) -> dict:
        engine_key = data.get("engine_key", "").strip()
        if not engine_key:
            raise ServiceOSException("VALIDATION_ERROR", "engine_key is required.")
        existing = await self.db.scalar(
            select(PlatformEngine).where(PlatformEngine.engine_key == engine_key))
        if existing:
            raise ServiceOSException("DUPLICATE", f"Engine '{engine_key}' already exists.")

        e = PlatformEngine(
            engine_key=engine_key,
            display_name=data.get("display_name", engine_key),
            description=data.get("description"),
            engine_type=data.get("engine_type", "plugin"),
            lifecycle_status=data.get("lifecycle_status", "draft"),
            global_status=data.get("global_status", "disabled"),
            is_core=data.get("is_core", False),
            is_locked=data.get("is_locked", False),
            version=data.get("version", "1.0.0"),
            owner_team=data.get("owner_team"),
            created_at=_now(), updated_at=_now(),
        )
        self.db.add(e)
        await self.db.flush()
        self._audit("engine.created", engine_key=engine_key, engine_id=e.id,
                    new_value=e.to_dict())
        await self.db.commit()
        return e.to_dict()

    async def update_engine(self, engine_key: str, data: dict) -> dict:
        e = await self._get_engine(engine_key)
        old = e.to_dict()
        for field in ("display_name", "description", "engine_type", "lifecycle_status",
                      "version", "owner_team", "is_customer_visible", "is_tenant_visible"):
            if field in data:
                setattr(e, field, data[field])
        e.updated_at = _now()
        self._audit("engine.updated", engine_key=engine_key, engine_id=e.id,
                    old_value=old, new_value=e.to_dict(), reason=data.get("reason"))
        await self.db.commit()
        return e.to_dict()

    # ── Enable / Disable ───────────────────────────────────────────────────────

    async def get_impact_preview(self, engine_key: str, action: str) -> dict:
        """Show impact before enabling or disabling an engine."""
        e = await self._get_engine(engine_key)

        blockers = []
        warnings = []

        if action == "disable":
            if e.is_locked:
                blockers.append(f"Engine '{engine_key}' is locked and cannot be disabled.")
            # Check active dependents
            active_dependents = (await self.db.execute(
                select(EngineDependency.engine_key).where(
                    EngineDependency.depends_on_engine_key == engine_key,
                    EngineDependency.status == "active",
                    EngineDependency.dependency_type == "required")
            )).scalars().all()
            for dep_key in active_dependents:
                dep_engine = await self.db.scalar(
                    select(PlatformEngine).where(PlatformEngine.engine_key == dep_key))
                if dep_engine and dep_engine.global_status in ("enabled", "locked"):
                    blockers.append(
                        f"Engine '{dep_key}' is active and depends on '{engine_key}'.")

        if action == "enable":
            deps = (await self.db.execute(
                select(EngineDependency).where(
                    EngineDependency.engine_key == engine_key,
                    EngineDependency.status == "active",
                    EngineDependency.dependency_type == "required")
            )).scalars().all()
            for dep in deps:
                dep_engine = await self.db.scalar(
                    select(PlatformEngine).where(
                        PlatformEngine.engine_key == dep.depends_on_engine_key))
                if not dep_engine or dep_engine.global_status not in ("enabled", "locked"):
                    blockers.append(
                        f"Required dependency '{dep.depends_on_engine_key}' is not enabled.")

        cat_count = await self.db.scalar(
            select(func.count()).select_from(CategoryEngineMatrix).where(
                CategoryEngineMatrix.engine_key == engine_key,
                CategoryEngineMatrix.is_enabled == True))
        pkg_count = await self.db.scalar(
            select(func.count()).select_from(PackageEngineEntitlement).where(
                PackageEngineEntitlement.engine_key == engine_key,
                PackageEngineEntitlement.is_included == True))
        tenant_count = await self.db.scalar(
            select(func.count()).select_from(TenantEngineOverride).where(
                TenantEngineOverride.engine_key == engine_key,
                TenantEngineOverride.status == "active"))

        risk = "high" if blockers else ("medium" if cat_count or pkg_count else "low")

        return {
            "engine_key": engine_key,
            "engine_name": e.display_name,
            "action": action,
            "current_status": e.global_status,
            "is_locked": e.is_locked,
            "is_core": e.is_core,
            "categories_affected": cat_count or 0,
            "packages_affected": pkg_count or 0,
            "active_tenant_overrides": tenant_count or 0,
            "blockers": blockers,
            "warnings": warnings,
            "risk_level": risk,
            "can_proceed": len(blockers) == 0,
            "recommendation": (
                "Action is blocked. Resolve blockers first." if blockers else
                f"Safe to proceed. {cat_count or 0} categories and {pkg_count or 0} packages will be affected."
            ),
        }

    async def enable_engine(self, engine_key: str, reason: str = "") -> dict:
        preview = await self.get_impact_preview(engine_key, "enable")
        if not preview["can_proceed"]:
            raise ServiceOSException("BLOCKED", "Cannot enable engine.",
                                     context={"blockers": preview["blockers"]})
        e = await self._get_engine(engine_key)
        old_status = e.global_status
        e.global_status = "enabled"
        e.updated_at = _now()
        self._audit("engine.global_enabled", engine_key=engine_key, engine_id=e.id,
                    old_value={"global_status": old_status},
                    new_value={"global_status": "enabled"}, reason=reason)
        await self.db.commit()
        return e.to_dict()

    async def disable_engine(self, engine_key: str, reason: str = "") -> dict:
        preview = await self.get_impact_preview(engine_key, "disable")
        if not preview["can_proceed"]:
            raise ServiceOSException("BLOCKED", "Cannot disable engine.",
                                     context={"blockers": preview["blockers"]})
        e = await self._get_engine(engine_key)
        old_status = e.global_status
        e.global_status = "disabled"
        e.updated_at = _now()
        self._audit("engine.global_disabled", engine_key=engine_key, engine_id=e.id,
                    old_value={"global_status": old_status},
                    new_value={"global_status": "disabled"}, reason=reason)
        await self.db.commit()
        return e.to_dict()

    # ── Category Matrix ────────────────────────────────────────────────────────

    async def get_category_matrix(self, category_id: uuid.UUID | None = None,
                                   page: int = 1, limit: int = 100) -> dict:
        stmt = select(CategoryEngineMatrix).order_by(
            CategoryEngineMatrix.is_required.desc(), CategoryEngineMatrix.engine_key)
        if category_id:
            stmt = stmt.where(CategoryEngineMatrix.category_id == category_id)

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()

        engines = {}
        for row in rows:
            ek = row.engine_key
            if ek not in engines:
                engines[ek] = row.to_dict()
                engines[ek]["categories"] = []
            engines[ek]["categories"].append(str(row.category_id))

        return {
            "matrix": [row.to_dict() for row in rows],
            "meta": {"total": total or 0},
        }

    async def set_category_engine(self, category_id: uuid.UUID, engine_key: str,
                                   enabled: bool, is_required: bool = False,
                                   reason: str = "") -> dict:
        # Validate engine exists and is globally enabled
        engine = await self._get_engine(engine_key)
        if enabled and engine.global_status not in ("enabled", "locked"):
            raise ServiceOSException("BLOCKED",
                f"Cannot enable '{engine_key}' for category: engine is globally disabled.")

        existing = await self.db.scalar(
            select(CategoryEngineMatrix).where(
                CategoryEngineMatrix.category_id == category_id,
                CategoryEngineMatrix.engine_key == engine_key))

        action_type = "engine.category_enabled" if enabled else "engine.category_disabled"

        if existing:
            old = {"is_enabled": existing.is_enabled, "is_required": existing.is_required}
            existing.is_enabled = enabled
            existing.is_required = is_required
            existing.updated_at = _now()
            row = existing
        else:
            row = CategoryEngineMatrix(
                category_id=category_id,
                engine_id=engine.id,
                engine_key=engine_key,
                is_enabled=enabled,
                is_required=is_required,
                enabled_by_admin_id=self.actor_id,
                created_at=_now(), updated_at=_now(),
            )
            self.db.add(row)
            old = None

        self._audit(action_type, engine_key=engine_key, engine_id=engine.id,
                    scope_type="category", scope_id=category_id,
                    old_value=old, new_value={"is_enabled": enabled, "is_required": is_required},
                    reason=reason)
        await self.db.commit()
        return row.to_dict()

    # ── Category Matrix Governance (P0 sprint) ────────────────────────────────

    async def _get_category(self, category_id: uuid.UUID):
        from app.engines.admin_catalog.models import ServiceCategory
        cat = await self.db.scalar(
            select(ServiceCategory).where(ServiceCategory.id == category_id))
        if not cat:
            raise ServiceOSException("NOT_FOUND", f"Category {category_id} not found.")
        return cat

    async def _packages_for_vertical(self, vertical_type: str | None):
        from app.engines.package_commerce.models import ServicePackage
        if not vertical_type:
            return []
        rows = (await self.db.execute(
            select(ServicePackage).where(
                ServicePackage.vertical_type == vertical_type,
                ServicePackage.is_active == True)
        )).scalars().all()
        return rows

    async def _tenants_for_category(self, category_id: uuid.UUID):
        from app.engines.tenant_engine.models import Tenant
        rows = (await self.db.execute(
            select(Tenant).where(Tenant.category_id == category_id)
        )).scalars().all()
        return rows

    async def _compute_dependency_status(self, engine_key: str) -> tuple[str, list[str]]:
        """met | missing — for the engine's required global dependencies."""
        deps = (await self.db.execute(
            select(EngineDependency).where(
                EngineDependency.engine_key == engine_key,
                EngineDependency.status == "active",
                EngineDependency.dependency_type == "required")
        )).scalars().all()
        missing = []
        for dep in deps:
            dep_engine = await self.db.scalar(
                select(PlatformEngine).where(
                    PlatformEngine.engine_key == dep.depends_on_engine_key))
            if not dep_engine or dep_engine.global_status not in ("enabled", "locked"):
                missing.append(dep.depends_on_engine_key)
        return ("missing" if missing else "met"), missing

    async def get_category_matrix_for_category(self, category_id: uuid.UUID) -> dict:
        category = await self._get_category(category_id)
        rows = (await self.db.execute(
            select(CategoryEngineMatrix).where(
                CategoryEngineMatrix.category_id == category_id)
        )).scalars().all()

        packages = await self._packages_for_vertical(category.vertical_type)
        tenants = await self._tenants_for_category(category_id)
        package_ids = [p.id for p in packages]

        result_rows = []
        for row in rows:
            dep_status, missing = await self._compute_dependency_status(row.engine_key)

            pkg_count = 0
            if package_ids:
                pkg_count = await self.db.scalar(
                    select(func.count()).select_from(PackageEngineEntitlement).where(
                        PackageEngineEntitlement.engine_key == row.engine_key,
                        PackageEngineEntitlement.package_id.in_(package_ids),
                        PackageEngineEntitlement.is_included == True)) or 0

            tenant_count = len(tenants)

            risk = "low"
            if dep_status == "missing":
                risk = "high"
            if row.is_required and (pkg_count > 0 or tenant_count > 0):
                risk = "high" if risk != "blocked" else risk
            if row.is_required and not row.is_enabled:
                risk = "blocked"

            d = row.to_dict()
            d["dependency_status"] = dep_status
            d["missing_dependencies"] = missing
            d["package_usage_count"] = pkg_count
            d["tenant_impact_count"] = tenant_count
            d["runtime_risk"] = risk
            result_rows.append(d)

        engine_keys_mapped = {r.engine_key for r in rows}
        return {
            "category": {
                "id": str(category.id), "name": category.name, "slug": category.slug,
                "vertical_type": category.vertical_type,
                "customer_flow_type": category.customer_flow_type,
                "finance_model": category.finance_model,
                "status": "active" if category.is_active else "inactive",
            },
            "rows": result_rows,
            "meta": {"total": len(result_rows), "mapped_engine_keys": sorted(engine_keys_mapped)},
        }

    async def get_category_matrix_summary(self, category_id: uuid.UUID) -> dict:
        matrix = await self.get_category_matrix_for_category(category_id)
        rows = matrix["rows"]
        total = len(rows)
        enabled = sum(1 for r in rows if r["is_enabled"])
        required = sum(1 for r in rows if r["is_required"])
        optional = sum(1 for r in rows if not r["is_required"])
        missing_deps = sum(1 for r in rows if r["dependency_status"] == "missing")
        used_by_packages = sum(1 for r in rows if r["package_usage_count"] > 0)
        used_by_tenants = sum(1 for r in rows if r["tenant_impact_count"] > 0)
        blocked = sum(1 for r in rows if r["runtime_risk"] == "blocked")
        return {
            "category": matrix["category"],
            "total_engines": total,
            "enabled_engines": enabled,
            "required_engines": required,
            "optional_engines": optional,
            "missing_dependencies": missing_deps,
            "used_by_packages": used_by_packages,
            "used_by_tenants": used_by_tenants,
            "blocked_actions": blocked,
        }

    def list_category_templates(self) -> dict:
        return {
            "templates": [
                {
                    "key": key,
                    "vertical_type": tpl["vertical_type"],
                    "required_count": len(tpl["required"]),
                    "optional_count": len(tpl["optional"]),
                }
                for key, tpl in CATEGORY_ENGINE_TEMPLATES.items()
            ]
        }

    async def seed_defaults_preview(self, category_id: uuid.UUID, template: str | None = None) -> dict:
        category = await self._get_category(category_id)
        tpl_key = template or _template_for_vertical(category.vertical_type)
        if not tpl_key or tpl_key not in CATEGORY_ENGINE_TEMPLATES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"No recommended template found for vertical_type '{category.vertical_type}'. "
                f"Pass an explicit template from: {sorted(CATEGORY_ENGINE_TEMPLATES)}")
        tpl = CATEGORY_ENGINE_TEMPLATES[tpl_key]

        existing_keys = {r.engine_key for r in (await self.db.execute(
            select(CategoryEngineMatrix.engine_key).where(
                CategoryEngineMatrix.category_id == category_id))).all()}

        warnings = []
        will_create_required = [k for k in tpl["required"] if k not in existing_keys]
        will_create_optional = [k for k in tpl["optional"] if k not in existing_keys]

        all_keys = tpl["required"] + tpl["optional"]
        found_engines = (await self.db.execute(
            select(PlatformEngine.engine_key).where(
                PlatformEngine.engine_key.in_(all_keys)))).scalars().all()
        for k in all_keys:
            if k not in found_engines:
                warnings.append(f"Engine '{k}' referenced by template is not registered in platform_engines.")

        return {
            "category": category.name,
            "template": tpl_key,
            "will_create": len(will_create_required) + len(will_create_optional),
            "required_engines": tpl["required"],
            "optional_engines": tpl["optional"],
            "already_mapped": sorted(existing_keys),
            "warnings": warnings,
        }

    async def seed_defaults(self, category_id: uuid.UUID, template: str | None = None,
                             dry_run: bool = False, reason: str = "") -> dict:
        preview = await self.seed_defaults_preview(category_id, template)
        if dry_run:
            return preview

        tpl_key = preview["template"]
        tpl = CATEGORY_ENGINE_TEMPLATES[tpl_key]
        existing_keys = set(preview["already_mapped"])

        created = []
        for engine_key in tpl["required"] + tpl["optional"]:
            if engine_key in existing_keys:
                continue
            engine = await self.db.scalar(
                select(PlatformEngine).where(PlatformEngine.engine_key == engine_key))
            if not engine:
                continue
            is_required = engine_key in tpl["required"]
            row = CategoryEngineMatrix(
                category_id=category_id,
                engine_id=engine.id,
                engine_key=engine_key,
                is_enabled=is_required,
                is_required=is_required,
                recommendation_status="required" if is_required else "optional",
                dependency_status="not_checked",
                runtime_risk="low",
                status="active",
                enabled_by_admin_id=self.actor_id,
                created_by_user_id=self.actor_id,
                updated_by_user_id=self.actor_id,
                created_at=_now(), updated_at=_now(),
            )
            self.db.add(row)
            created.append(engine_key)

        self._audit("engine.category_matrix.seeded", scope_type="category", scope_id=category_id,
                    new_value={"template": tpl_key, "created": created}, reason=reason)
        await self.db.commit()
        return {**preview, "created_engine_keys": created, "dry_run": False}

    async def _get_category_engine_row(self, category_id: uuid.UUID, engine_key: str) -> CategoryEngineMatrix:
        row = await self.db.scalar(
            select(CategoryEngineMatrix).where(
                CategoryEngineMatrix.category_id == category_id,
                CategoryEngineMatrix.engine_key == engine_key))
        if not row:
            raise ServiceOSException("NOT_FOUND",
                f"No category engine mapping for '{engine_key}' in this category.")
        return row

    async def category_engine_action_preview(self, category_id: uuid.UUID, engine_key: str,
                                              action: str) -> dict:
        category = await self._get_category(category_id)
        engine = await self._get_engine(engine_key)
        row = await self.db.scalar(
            select(CategoryEngineMatrix).where(
                CategoryEngineMatrix.category_id == category_id,
                CategoryEngineMatrix.engine_key == engine_key))

        blockers, warnings = [], []
        dep_status, missing = await self._compute_dependency_status(engine_key)

        if action == "enable":
            if engine.global_status not in ("enabled", "locked"):
                blockers.append(f"Engine '{engine_key}' is globally disabled.")
            if dep_status == "missing":
                blockers.append(f"Missing required global dependencies: {', '.join(missing)}.")

        packages = await self._packages_for_vertical(category.vertical_type)
        package_ids = [p.id for p in packages]
        pkg_count = 0
        if package_ids:
            pkg_count = await self.db.scalar(
                select(func.count()).select_from(PackageEngineEntitlement).where(
                    PackageEngineEntitlement.engine_key == engine_key,
                    PackageEngineEntitlement.package_id.in_(package_ids),
                    PackageEngineEntitlement.is_included == True)) or 0
        tenants = await self._tenants_for_category(category_id)
        tenant_count = len(tenants)

        if action == "disable":
            is_required = row.is_required if row else False
            if is_required and pkg_count > 0:
                blockers.append(
                    f"'{engine.display_name}' is required for {category.name} and used by "
                    f"{pkg_count} active package(s).")
            if is_required and tenant_count > 0:
                blockers.append(
                    f"'{engine.display_name}' is required for {category.name} and "
                    f"{tenant_count} tenant(s) are on this category.")

        risk = "high" if blockers else ("medium" if (pkg_count or tenant_count) else "low")
        recommendation = (
            f"Blocked. Resolve blockers before {action} can proceed." if blockers else
            f"Safe to {action}. {pkg_count} package(s) and {tenant_count} tenant(s) affected."
        )

        return {
            "category_id": str(category_id),
            "engine_key": engine_key,
            "action": action,
            "affected_packages": pkg_count,
            "affected_tenants": tenant_count,
            "missing_dependencies": missing,
            "risk_level": risk,
            "blocked": len(blockers) > 0,
            "blockers": blockers,
            "warnings": warnings,
            "recommendation": recommendation,
        }

    async def enable_category_engine(self, category_id: uuid.UUID, engine_key: str,
                                      reason: str = "", force: bool = False) -> dict:
        preview = await self.category_engine_action_preview(category_id, engine_key, "enable")
        if preview["blocked"] and not force:
            raise ServiceOSException("BLOCKED", "Cannot enable engine for category.",
                                     context={"blockers": preview["blockers"]})
        engine = await self._get_engine(engine_key)
        row = await self.db.scalar(
            select(CategoryEngineMatrix).where(
                CategoryEngineMatrix.category_id == category_id,
                CategoryEngineMatrix.engine_key == engine_key))
        old = row.to_dict() if row else None
        dep_status, _ = await self._compute_dependency_status(engine_key)
        if row:
            row.is_enabled = True
            row.dependency_status = dep_status
            row.runtime_risk = preview["risk_level"]
            row.updated_by_user_id = self.actor_id
            row.updated_at = _now()
        else:
            row = CategoryEngineMatrix(
                category_id=category_id, engine_id=engine.id, engine_key=engine_key,
                is_enabled=True, is_required=False, recommendation_status="optional",
                dependency_status=dep_status, runtime_risk=preview["risk_level"], status="active",
                enabled_by_admin_id=self.actor_id, created_by_user_id=self.actor_id,
                updated_by_user_id=self.actor_id, created_at=_now(), updated_at=_now(),
            )
            self.db.add(row)
        self._audit("engine.category_matrix.enabled", engine_key=engine_key, engine_id=engine.id,
                    scope_type="category", scope_id=category_id, old_value=old,
                    new_value={"is_enabled": True}, reason=reason)
        await self.db.commit()
        return row.to_dict()

    async def disable_category_engine(self, category_id: uuid.UUID, engine_key: str,
                                       reason: str = "", force: bool = False) -> dict:
        preview = await self.category_engine_action_preview(category_id, engine_key, "disable")
        if preview["blocked"] and not force:
            self._audit("engine.category_matrix.validation_failed", engine_key=engine_key,
                        scope_type="category", scope_id=category_id,
                        new_value={"blockers": preview["blockers"]}, reason=reason)
            await self.db.commit()
            raise ServiceOSException("BLOCKED", "Cannot disable engine for category.",
                                     context={"blockers": preview["blockers"]})
        row = await self._get_category_engine_row(category_id, engine_key)
        old = row.to_dict()
        row.is_enabled = False
        row.runtime_risk = "low"
        row.updated_by_user_id = self.actor_id
        row.updated_at = _now()
        self._audit("engine.category_matrix.disabled", engine_key=engine_key, engine_id=row.engine_id,
                    scope_type="category", scope_id=category_id, old_value=old,
                    new_value={"is_enabled": False}, reason=reason)
        await self.db.commit()
        return row.to_dict()

    async def mark_category_engine_required(self, category_id: uuid.UUID, engine_key: str,
                                             reason: str = "") -> dict:
        row = await self._get_category_engine_row(category_id, engine_key)
        old = row.to_dict()
        row.is_required = True
        row.recommendation_status = "required"
        row.updated_by_user_id = self.actor_id
        row.updated_at = _now()
        self._audit("engine.category_matrix.marked_required", engine_key=engine_key,
                    engine_id=row.engine_id, scope_type="category", scope_id=category_id,
                    old_value=old, new_value=row.to_dict(), reason=reason)
        await self.db.commit()
        return row.to_dict()

    async def mark_category_engine_optional(self, category_id: uuid.UUID, engine_key: str,
                                             reason: str = "") -> dict:
        row = await self._get_category_engine_row(category_id, engine_key)
        old = row.to_dict()
        row.is_required = False
        row.recommendation_status = "optional"
        row.updated_by_user_id = self.actor_id
        row.updated_at = _now()
        self._audit("engine.category_matrix.marked_optional", engine_key=engine_key,
                    engine_id=row.engine_id, scope_type="category", scope_id=category_id,
                    old_value=old, new_value=row.to_dict(), reason=reason)
        await self.db.commit()
        return row.to_dict()

    async def get_category_engine_package_usage(self, category_id: uuid.UUID, engine_key: str) -> dict:
        category = await self._get_category(category_id)
        packages = await self._packages_for_vertical(category.vertical_type)
        package_ids = [p.id for p in packages]
        entitlements = {}
        if package_ids:
            rows = (await self.db.execute(
                select(PackageEngineEntitlement).where(
                    PackageEngineEntitlement.engine_key == engine_key,
                    PackageEngineEntitlement.package_id.in_(package_ids))
            )).scalars().all()
            entitlements = {e.package_id: e for e in rows}

        from app.engines.package_commerce.models import TenantPackageAssignment
        result = []
        for p in packages:
            ent = entitlements.get(p.id)
            tenant_count = await self.db.scalar(
                select(func.count()).select_from(TenantPackageAssignment).where(
                    TenantPackageAssignment.package_id == p.id,
                    TenantPackageAssignment.status == "active")) or 0
            result.append({
                "package_id": str(p.id),
                "package_name": p.name,
                "package_type": p.package_type,
                "status": "active" if p.is_active else "inactive",
                "tenant_count": tenant_count,
                "engine_included": bool(ent and ent.is_included),
                "required": bool(ent and ent.is_included),
            })
        return {"packages": result, "total": len(result)}

    async def get_category_engine_tenant_impact(self, category_id: uuid.UUID, engine_key: str) -> dict:
        tenants = await self._tenants_for_category(category_id)
        result = []
        for t in tenants:
            override = await self.db.scalar(
                select(TenantEngineOverride).where(
                    TenantEngineOverride.tenant_id == t.id,
                    TenantEngineOverride.engine_key == engine_key,
                    TenantEngineOverride.status == "active")
                .order_by(TenantEngineOverride.created_at.desc()).limit(1))
            result.append({
                "tenant_id": str(t.id),
                "tenant_name": t.tenant_name,
                "status": t.status,
                "plan_type": t.plan_type,
                "runtime_access": (override.effective_status == "enabled") if override else None,
                "override": override.override_type if override else None,
                "risk": "low" if t.status == "active" else "none",
            })
        return {"tenants": result, "total": len(result)}

    # ── Package Entitlements ───────────────────────────────────────────────────

    async def get_package_entitlements(self, package_id: uuid.UUID | None = None,
                                        page: int = 1, limit: int = 100) -> dict:
        stmt = select(PackageEngineEntitlement).order_by(
            PackageEngineEntitlement.engine_key)
        if package_id:
            stmt = stmt.where(PackageEngineEntitlement.package_id == package_id)

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "entitlements": [r.to_dict() for r in rows],
            "meta": {"total": total or 0},
        }

    async def set_package_engine(self, package_id: uuid.UUID, engine_key: str,
                                  included: bool, limits: dict | None = None,
                                  feature_flags: dict | None = None,
                                  reason: str = "") -> dict:
        engine = await self._get_engine(engine_key)
        if included and engine.global_status not in ("enabled", "locked"):
            raise ServiceOSException("BLOCKED",
                f"Cannot include globally disabled engine '{engine_key}' in package.")

        existing = await self.db.scalar(
            select(PackageEngineEntitlement).where(
                PackageEngineEntitlement.package_id == package_id,
                PackageEngineEntitlement.engine_key == engine_key))

        action_type = "engine.package_entitlement_added" if included else "engine.package_entitlement_removed"

        if existing:
            existing.is_included = included
            existing.limits_json = limits or existing.limits_json
            existing.feature_flags_json = feature_flags or existing.feature_flags_json
            existing.updated_at = _now()
            row = existing
        else:
            row = PackageEngineEntitlement(
                package_id=package_id,
                engine_id=engine.id,
                engine_key=engine_key,
                is_included=included,
                limits_json=limits or {},
                feature_flags_json=feature_flags or {},
                added_by_admin_id=self.actor_id,
                created_at=_now(), updated_at=_now(),
            )
            self.db.add(row)

        self._audit(action_type, engine_key=engine_key, engine_id=engine.id,
                    scope_type="package", scope_id=package_id,
                    new_value={"is_included": included}, reason=reason)
        await self.db.commit()
        return row.to_dict()

    # ── Tenant Overrides ───────────────────────────────────────────────────────

    async def list_tenant_overrides(self, tenant_id: uuid.UUID | None = None,
                                     status: str | None = None,
                                     page: int = 1, limit: int = 50) -> dict:
        stmt = select(TenantEngineOverride).order_by(TenantEngineOverride.created_at.desc())
        if tenant_id:
            stmt = stmt.where(TenantEngineOverride.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(TenantEngineOverride.status == status)
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "overrides": [r.to_dict() for r in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit},
        }

    async def create_tenant_override(self, tenant_id: uuid.UUID, data: dict) -> dict:
        engine_key = data.get("engine_key", "")
        override_type = data.get("override_type", "")
        reason = data.get("reason", "").strip()

        if not reason:
            raise ServiceOSException("VALIDATION_ERROR", "reason is required for tenant overrides.")
        if override_type not in VALID_OVERRIDE_TYPES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"override_type must be one of: {sorted(VALID_OVERRIDE_TYPES)}")

        engine = await self._get_engine(engine_key)

        # Cannot enable globally disabled engine without emergency override
        if override_type in ("grant", "temporary_grant", "beta_access"):
            if engine.global_status == "disabled":
                raise ServiceOSException("BLOCKED",
                    f"Cannot grant '{engine_key}': engine is globally disabled. "
                    "Use force_disable override only.")

        effective_status = (
            "enabled" if override_type in ("grant", "temporary_grant", "beta_access") else "disabled"
        )
        expires_at = None
        if data.get("expires_at"):
            from datetime import datetime
            expires_at = datetime.fromisoformat(data["expires_at"])

        override = TenantEngineOverride(
            tenant_id=tenant_id,
            engine_id=engine.id,
            engine_key=engine_key,
            override_type=override_type,
            effective_status=effective_status,
            reason=reason,
            expires_at=expires_at,
            created_by_admin_id=self.actor_id,
            status="active",
            created_at=_now(), updated_at=_now(),
        )
        self.db.add(override)
        await self.db.flush()

        self._audit("engine.tenant_override_created",
                    engine_key=engine_key, engine_id=engine.id,
                    scope_type="tenant", scope_id=tenant_id,
                    new_value=override.to_dict(), reason=reason)
        await self.db.commit()
        return override.to_dict()

    async def revoke_tenant_override(self, override_id: uuid.UUID, reason: str = "") -> dict:
        override = await self.db.scalar(
            select(TenantEngineOverride).where(TenantEngineOverride.id == override_id))
        if not override:
            raise ServiceOSException("NOT_FOUND", f"Override {override_id} not found.")
        if override.status != "active":
            raise ServiceOSException("INVALID_STATE", "Override is not active.")
        override.status = "revoked"
        override.revoked_at = _now()
        override.revoked_by_admin_id = self.actor_id
        override.updated_at = _now()
        self._audit("engine.tenant_override_revoked",
                    engine_key=override.engine_key, engine_id=override.engine_id,
                    scope_type="tenant", scope_id=override.tenant_id, reason=reason)
        await self.db.commit()
        return override.to_dict()

    # ── Health Checks ──────────────────────────────────────────────────────────

    async def run_health_check(self, engine_key: str) -> dict:
        engine = await self._get_engine(engine_key)

        t0 = time.monotonic()
        result = {"engine_key": engine_key, "checks": []}
        errors = []

        # Check 1: Engine globally enabled
        if engine.global_status == "disabled":
            result["checks"].append({"name": "global_status", "passed": False,
                                      "detail": "Engine is globally disabled"})
            errors.append("Engine is globally disabled")
        else:
            result["checks"].append({"name": "global_status", "passed": True,
                                      "detail": f"Status: {engine.global_status}"})

        # Check 2: Dependencies enabled
        deps = (await self.db.execute(
            select(EngineDependency).where(
                EngineDependency.engine_key == engine_key,
                EngineDependency.status == "active",
                EngineDependency.dependency_type == "required")
        )).scalars().all()
        for dep in deps:
            dep_engine = await self.db.scalar(
                select(PlatformEngine).where(
                    PlatformEngine.engine_key == dep.depends_on_engine_key))
            if dep_engine and dep_engine.global_status in ("enabled", "locked"):
                result["checks"].append({"name": f"dep:{dep.depends_on_engine_key}",
                                          "passed": True, "detail": "Dependency enabled"})
            else:
                result["checks"].append({"name": f"dep:{dep.depends_on_engine_key}",
                                          "passed": False, "detail": "Dependency not enabled"})
                errors.append(f"Required dependency '{dep.depends_on_engine_key}' not enabled")

        # Check 3: DB reachability (fast check via engine table count)
        try:
            await self.db.scalar(
                select(func.count()).select_from(PlatformEngine).where(
                    PlatformEngine.engine_key == engine_key))
            result["checks"].append({"name": "db_access", "passed": True, "detail": "DB accessible"})
        except Exception as ex:
            result["checks"].append({"name": "db_access", "passed": False, "detail": str(ex)})
            errors.append(f"DB access error: {ex}")

        ms = int((time.monotonic() - t0) * 1000)
        health_status = "down" if len(errors) > 1 else ("degraded" if errors else "healthy")

        # Persist result
        check = EngineHealthCheck(
            engine_id=engine.id,
            engine_key=engine_key,
            health_status=health_status,
            check_type="manual",
            result_json=result,
            error_message="; ".join(errors) if errors else None,
            response_ms=ms,
            checked_at=_now(),
            checked_by_user_id=self.actor_id,
        )
        self.db.add(check)
        self._audit("engine.health_check_run", engine_key=engine_key, engine_id=engine.id,
                    new_value={"health_status": health_status, "ms": ms})
        await self.db.commit()

        return {
            "engine_key": engine_key,
            "health_status": health_status,
            "response_ms": ms,
            "checks": result["checks"],
            "errors": errors,
            "checked_at": check.checked_at.isoformat(),
        }

    async def get_health_overview(self) -> dict:
        engines = (await self.db.execute(select(PlatformEngine))).scalars().all()
        db_by_canonical: dict[str, list[PlatformEngine]] = {}
        for row in engines:
            db_by_canonical.setdefault(_canonical_engine_key(row.engine_key), []).append(row)

        latest_rows = (await self.db.execute(text("""
            SELECT DISTINCT ON (engine_key)
                   engine_key, health_status, checked_at, error_message
            FROM engine_health_checks
            ORDER BY engine_key, checked_at DESC
        """))).mappings().all()
        health_by_canonical: dict[str, dict] = {}
        for row in latest_rows:
            health_by_canonical[_canonical_engine_key(row["engine_key"])] = dict(row)

        result = []
        for definition in sorted(runtime_registry.all(), key=lambda item: item.name):
            matches = db_by_canonical.get(definition.engine_id, [])
            primary = next((row for row in matches if row.engine_key == definition.engine_id), None)
            primary = primary or (matches[0] if matches else None)
            latest = health_by_canonical.get(definition.engine_id)
            result.append({
                **(primary.to_dict() if primary else {
                    "id": None,
                    "engine_key": definition.engine_id,
                    "global_status": "not_configured",
                    "is_core": definition.engine_type == "core",
                    "is_locked": False,
                    "lifecycle_status": "registry_only",
                }),
                "display_name": definition.name,
                "canonical_engine_key": definition.engine_id,
                "health_status": latest["health_status"] if latest else "unknown",
                "last_check": latest["checked_at"].isoformat() if latest else None,
                "last_error": latest["error_message"] if latest else None,
            })

        healthy = sum(1 for r in result if r["health_status"] == "healthy")
        degraded = sum(1 for r in result if r["health_status"] == "degraded")
        down = sum(1 for r in result if r["health_status"] == "down")
        unknown = sum(1 for r in result if r["health_status"] == "unknown")

        return {
            "engines": result,
            "summary": {
                "healthy": healthy, "degraded": degraded, "down": down,
                "unknown": unknown, "total": len(result),
            },
        }

    # ── Permissions ────────────────────────────────────────────────────────────

    async def list_permissions(self, engine_key: str | None = None,
                                scope: str | None = None, q: str | None = None,
                                page: int = 1, limit: int = 100) -> dict:
        stmt = select(EnginePermission).order_by(
            EnginePermission.engine_key, EnginePermission.permission_key)
        if engine_key:
            stmt = stmt.where(EnginePermission.engine_key == engine_key)
        if scope:
            stmt = stmt.where(EnginePermission.scope == scope)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                EnginePermission.permission_key.ilike(like) |
                EnginePermission.label.ilike(like))
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "permissions": [r.to_dict() for r in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit},
        }

    async def update_permission(self, permission_id: uuid.UUID, data: dict) -> dict:
        perm = await self.db.scalar(
            select(EnginePermission).where(EnginePermission.id == permission_id))
        if not perm:
            raise ServiceOSException("NOT_FOUND", "Permission not found.")
        old = perm.to_dict()
        for field in ("label", "description", "scope", "is_sensitive", "requires_mfa", "status"):
            if field in data:
                setattr(perm, field, data[field])
        perm.updated_at = _now()
        self._audit("engine.permission_updated",
                    engine_key=perm.engine_key, engine_id=perm.engine_id,
                    old_value=old, new_value=perm.to_dict(), reason=data.get("reason"))
        await self.db.commit()
        return perm.to_dict()

    # ── Audit Logs ─────────────────────────────────────────────────────────────

    async def list_audit_logs(self, engine_key: str | None = None,
                               action_type: str | None = None,
                               scope_type: str | None = None,
                               scope_id: uuid.UUID | None = None,
                               exclude_health_checks: bool = False,
                               page: int = 1, limit: int = 50) -> dict:
        stmt = select(EngineAuditLog).order_by(EngineAuditLog.created_at.desc())
        if engine_key:
            stmt = stmt.where(EngineAuditLog.engine_key == engine_key)
        if action_type:
            stmt = stmt.where(EngineAuditLog.action_type == action_type)
        if scope_type:
            stmt = stmt.where(EngineAuditLog.scope_type == scope_type)
        if scope_id:
            stmt = stmt.where(EngineAuditLog.scope_id == scope_id)
        if exclude_health_checks:
            stmt = stmt.where(~EngineAuditLog.action_type.ilike("%health_check%"))

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "logs": [r.to_dict() for r in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit,
                     "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
        }

    # ── Runtime Access Resolver ────────────────────────────────────────────────

    async def resolve_access(self, engine_key: str, tenant_id: uuid.UUID | None = None,
                              category_id: uuid.UUID | None = None,
                              package_id: uuid.UUID | None = None) -> dict:
        engine = await self.db.scalar(
            select(PlatformEngine).where(PlatformEngine.engine_key == engine_key))
        if not engine:
            return {
                "engine_key": engine_key, "runtime_enabled": False,
                "resolution_path": [f"Engine '{engine_key}' not found in registry"],
                "blockers": [f"Engine '{engine_key}' does not exist"],
            }

        path = []
        blockers = []

        # Check 1: Global status
        if engine.global_status in ("enabled", "locked"):
            path.append(f"Global engine '{engine_key}' is {engine.global_status}")
        else:
            blockers.append(f"Engine is globally {engine.global_status}")
            return {"engine_key": engine_key, "runtime_enabled": False,
                    "resolution_path": path, "blockers": blockers}

        # Check 2: Dependencies
        deps = (await self.db.execute(
            select(EngineDependency).where(
                EngineDependency.engine_key == engine_key,
                EngineDependency.status == "active",
                EngineDependency.dependency_type == "required")
        )).scalars().all()
        for dep in deps:
            dep_engine = await self.db.scalar(
                select(PlatformEngine).where(
                    PlatformEngine.engine_key == dep.depends_on_engine_key))
            if dep_engine and dep_engine.global_status in ("enabled", "locked"):
                path.append(f"Dependency '{dep.depends_on_engine_key}' is enabled")
            else:
                blockers.append(f"Required dependency '{dep.depends_on_engine_key}' is not enabled")

        # Check 3: Category allows engine
        if category_id:
            cat_entry = await self.db.scalar(
                select(CategoryEngineMatrix).where(
                    CategoryEngineMatrix.category_id == category_id,
                    CategoryEngineMatrix.engine_key == engine_key))
            if cat_entry and cat_entry.is_enabled:
                path.append("Category allows this engine")
            elif cat_entry and not cat_entry.is_enabled:
                blockers.append("Category has engine disabled")
            else:
                path.append("Engine not in category matrix — assuming allowed")

        # Check 4: Package includes engine
        if package_id:
            pkg_entry = await self.db.scalar(
                select(PackageEngineEntitlement).where(
                    PackageEngineEntitlement.package_id == package_id,
                    PackageEngineEntitlement.engine_key == engine_key))
            if pkg_entry and pkg_entry.is_included:
                path.append("Package includes this engine")
            elif pkg_entry and not pkg_entry.is_included:
                blockers.append("Package has engine excluded")
            else:
                path.append("Engine not in package entitlements — checking tenant overrides")

        # Check 5: Tenant override
        if tenant_id:
            override = await self.db.scalar(
                select(TenantEngineOverride).where(
                    TenantEngineOverride.tenant_id == tenant_id,
                    TenantEngineOverride.engine_key == engine_key,
                    TenantEngineOverride.status == "active")
                .order_by(TenantEngineOverride.created_at.desc()).limit(1))
            if override:
                if override.effective_status == "enabled":
                    path.append(f"Tenant override grants access ({override.override_type})")
                    # Remove package blocker if override grants
                    blockers = [b for b in blockers if "Package" not in b]
                else:
                    blockers.append(f"Tenant override blocks access ({override.override_type})")
            else:
                path.append("No tenant override found")

        runtime_enabled = len(blockers) == 0
        return {
            "engine_key": engine_key,
            "runtime_enabled": runtime_enabled,
            "resolution_path": path,
            "blockers": blockers,
        }

    # ── Dependencies ───────────────────────────────────────────────────────────

    async def get_dependencies_graph(self) -> dict:
        engines = (await self.db.execute(
            select(PlatformEngine).order_by(PlatformEngine.display_name)
        )).scalars().all()
        deps = (await self.db.execute(
            select(EngineDependency).where(EngineDependency.status == "active")
        )).scalars().all()

        nodes = [{"id": e.engine_key, "label": e.display_name, "type": e.engine_type,
                  "status": e.global_status} for e in engines]
        edges = [{"from": d.engine_key, "to": d.depends_on_engine_key,
                  "type": d.dependency_type} for d in deps]

        # Compute blocked engines (has disabled required dep)
        enabled_keys = {e.engine_key for e in engines
                        if e.global_status in ("enabled", "locked")}
        blocked = []
        for dep in deps:
            if dep.dependency_type == "required" and dep.depends_on_engine_key not in enabled_keys:
                blocked.append({"engine_key": dep.engine_key,
                                 "blocked_by": dep.depends_on_engine_key})

        return {"nodes": nodes, "edges": edges, "blocked_enables": blocked}
