"""Generic Catalog Dimension Engine -- service layer (migration 154).

Admin-side CRUD for dimension definitions/values and the per-(master_service,
job_type) structural blueprint config. Backs the approved Admin Catalog
page's Dimensions tab. All write ops are super-admin only (enforced at the
router). NO monetary fields anywhere (structure only).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    CatalogDimension, CatalogDimensionValue, ServiceJobDimension,
    ServiceType, Brand, MasterServiceType, MasterServiceBrand,
    MasterService, MasterIssueType, TenantService,
)
from app.engines.admin_catalog.cross_scope import cross_scoped_ids
from app.exceptions import ServiceOSException, NotFoundException

DATA_TYPES = {"single_select", "multi_select", "boolean", "number", "text"}
# Structural flags an admin may set on a service-job dimension. Explicitly
# enumerated so a stray monetary key can never be written through here.
SJD_FLAGS = {
    "enabled", "required", "ask_customer", "show_during_tenant_setup",
    "use_for_matching", "affects_price", "allow_tenant_override",
    "allow_all_coverage", "allow_selected_coverage", "allow_exclusion_coverage",
    "display_order",
}


class CatalogDimensionService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None):
        self.db = db
        self.actor_id = actor_id

    # ── Dimension definitions ─────────────────────────────────────────────────
    async def list_dimensions(self, include_inactive: bool = False) -> list[dict]:
        q = select(CatalogDimension).order_by(CatalogDimension.display_order)
        if not include_inactive:
            q = q.where(CatalogDimension.is_active == True)  # noqa: E712
        rows = (await self.db.execute(q)).scalars().all()
        return [d.to_dict() for d in rows]

    async def create_dimension(self, data: dict) -> dict:
        key = (data.get("key") or "").strip().lower()
        name = (data.get("name") or "").strip()
        dtype = (data.get("data_type") or "single_select").strip()
        if not key or not name:
            raise ServiceOSException("DIMENSION_KEY_NAME_REQUIRED", "key and name are required.", status_code=422)
        if dtype not in DATA_TYPES:
            raise ServiceOSException("INVALID_DATA_TYPE", f"data_type must be one of {sorted(DATA_TYPES)}.", status_code=422)
        existing = (await self.db.execute(select(CatalogDimension).where(CatalogDimension.key == key))).scalar_one_or_none()
        if existing:
            raise ServiceOSException("DIMENSION_KEY_EXISTS", f"A dimension with key '{key}' already exists.", status_code=409)
        d = CatalogDimension(key=key, name=name, description=data.get("description"),
                             data_type=dtype, display_order=int(data.get("display_order", 0)))
        self.db.add(d)
        await self.db.commit()
        await self.db.refresh(d)
        return d.to_dict()

    async def update_dimension(self, dimension_id: uuid.UUID, data: dict) -> dict:
        d = await self._load_dimension(dimension_id)
        for field in ("name", "description", "display_order", "is_active"):
            if field in data and data[field] is not None:
                setattr(d, field, data[field])
        if "data_type" in data and data["data_type"]:
            if data["data_type"] not in DATA_TYPES:
                raise ServiceOSException("INVALID_DATA_TYPE", "Invalid data_type.", status_code=422)
            d.data_type = data["data_type"]
        await self.db.commit()
        await self.db.refresh(d)
        return d.to_dict()

    async def delete_dimension(self, dimension_id: uuid.UUID) -> dict:
        """Soft-delete a custom dimension definition. Type and Brand are
        platform-structural (legacy_source set) and are never deletable
        through here -- they're managed in Types & Brands."""
        d = await self._load_dimension(dimension_id)
        if d.legacy_source:
            raise ServiceOSException("LEGACY_DIMENSION_NOT_DELETABLE",
                f"'{d.name}' is a platform-structural dimension and cannot be deleted.", status_code=422)
        if not d.is_active:
            return {"deleted": True, "id": str(dimension_id)}
        d.is_active = False
        await self.db.commit()
        return {"deleted": True, "id": str(dimension_id)}

    # ── Dimension values ──────────────────────────────────────────────────────
    async def list_values(self, dimension_id: uuid.UUID, master_service_id: uuid.UUID | None = None) -> dict:
        """Reads generic values, OR proxies to the legacy service_types/brands
        tables for the two seeded legacy dimensions -- so the UI has ONE way
        to fetch a dimension's values regardless of storage. When
        master_service_id is given, values already attached to a DIFFERENT
        service are excluded (see cross_scoped_ids), so a service's Type/
        Brand picker doesn't offer choices that only make sense for an
        unrelated service (e.g. AC types while editing a microwave).
        Never-used values still show for everyone."""
        d = await self._load_dimension(dimension_id)
        if d.legacy_source == "service_types":
            excluded = await cross_scoped_ids(self.db, MasterServiceType, MasterServiceType.service_type_id, master_service_id)
            stmt = select(ServiceType.id, ServiceType.name).where(ServiceType.is_active == True)  # noqa: E712
            if excluded:
                stmt = stmt.where(ServiceType.id.notin_(excluded))
            rows = (await self.db.execute(stmt)).all()
            return {"dimension": d.to_dict(), "legacy": True,
                    "values": [{"id": str(i), "code": None, "label": n} for i, n in rows]}
        if d.legacy_source == "brands":
            excluded = await cross_scoped_ids(self.db, MasterServiceBrand, MasterServiceBrand.brand_id, master_service_id)
            stmt = select(Brand.id, Brand.name).where(Brand.is_active == True)  # noqa: E712
            if excluded:
                stmt = stmt.where(Brand.id.notin_(excluded))
            rows = (await self.db.execute(stmt)).all()
            return {"dimension": d.to_dict(), "legacy": True,
                    "values": [{"id": str(i), "code": None, "label": n} for i, n in rows]}
        rows = (await self.db.execute(
            select(CatalogDimensionValue).where(
                CatalogDimensionValue.dimension_id == dimension_id,
                CatalogDimensionValue.is_active == True,  # noqa: E712
            ).order_by(CatalogDimensionValue.display_order))).scalars().all()
        return {"dimension": d.to_dict(), "legacy": False, "values": [v.to_dict() for v in rows]}

    async def add_value(self, dimension_id: uuid.UUID, data: dict) -> dict:
        d = await self._load_dimension(dimension_id)
        if d.legacy_source:
            raise ServiceOSException("LEGACY_DIMENSION_VALUE_READONLY",
                f"Values for '{d.key}' are managed in the {d.legacy_source} catalog, not here.", status_code=422)
        code = (data.get("code") or "").strip()
        label = (data.get("label") or "").strip()
        if not code or not label:
            raise ServiceOSException("VALUE_CODE_LABEL_REQUIRED", "code and label are required.", status_code=422)
        v = CatalogDimensionValue(dimension_id=dimension_id, code=code, label=label,
                                  meta=data.get("metadata"), display_order=int(data.get("display_order", 0)))
        self.db.add(v)
        await self.db.commit()
        await self.db.refresh(v)
        return v.to_dict()

    async def update_value(self, dimension_id: uuid.UUID, value_id: uuid.UUID, data: dict) -> dict:
        v = await self._load_value(dimension_id, value_id)
        for field in ("label", "display_order", "is_active"):
            if field in data and data[field] is not None:
                setattr(v, field, data[field])
        if "metadata" in data:
            v.meta = data["metadata"]
        await self.db.commit()
        await self.db.refresh(v)
        return v.to_dict()

    async def delete_value(self, dimension_id: uuid.UUID, value_id: uuid.UUID) -> dict:
        v = await self._load_value(dimension_id, value_id)
        if not v.is_active:
            return {"deleted": True, "id": str(value_id)}
        v.is_active = False
        await self.db.commit()
        return {"deleted": True, "id": str(value_id)}

    # ── Service-job dimension blueprint config ────────────────────────────────
    async def get_service_job_dimensions(self, master_service_id: uuid.UUID,
                                          job_type_id: uuid.UUID | None) -> dict:
        """Returns every dimension definition merged with its per-service-job
        config (or defaults if not yet configured) + a value COUNT per
        dimension -- the exact shape the Dimensions-tab grid needs."""
        dims = (await self.db.execute(
            select(CatalogDimension).where(CatalogDimension.is_active == True)  # noqa: E712
            .order_by(CatalogDimension.display_order))).scalars().all()

        cfg_rows = (await self.db.execute(
            select(ServiceJobDimension).where(
                ServiceJobDimension.master_service_id == master_service_id,
                or_(ServiceJobDimension.job_type_id == job_type_id, ServiceJobDimension.job_type_id.is_(None))
                if job_type_id else ServiceJobDimension.job_type_id.is_(None)))).scalars().all()
        by_dim = {str(c.dimension_id): c for c in sorted(cfg_rows, key=lambda c: c.job_type_id is not None)}

        # Batch all value counts. This replaces one COUNT query per dimension,
        # which made readiness latency grow linearly with the platform schema.
        generic_ids = [d.id for d in dims if not d.legacy_source]
        generic_counts: dict[uuid.UUID, int] = {}
        if generic_ids:
            generic_counts = dict((await self.db.execute(
                select(CatalogDimensionValue.dimension_id, func.count(CatalogDimensionValue.id))
                .where(
                    CatalogDimensionValue.dimension_id.in_(generic_ids),
                    CatalogDimensionValue.is_active == True,  # noqa: E712
                )
                .group_by(CatalogDimensionValue.dimension_id)
            )).all())
        # Type and Brand are global libraries, but the values usable by a
        # tenant are the active mappings for THIS master service. Counting
        # every global value made a blueprint look ready even when the tenant
        # API correctly returned no options for the service.
        needs_types = any(d.legacy_source == "service_types" for d in dims)
        needs_brands = any(d.legacy_source == "brands" for d in dims)
        type_count = int(await self.db.scalar(
            select(func.count(MasterServiceType.id))
            .join(ServiceType, ServiceType.id == MasterServiceType.service_type_id)
            .where(
                MasterServiceType.master_service_id == master_service_id,
                MasterServiceType.is_active.is_(True),
                ServiceType.is_active.is_(True),
                ServiceType.deleted_at.is_(None),
            )
        ) or 0) if needs_types else 0
        brand_count = int(await self.db.scalar(
            select(func.count(MasterServiceBrand.id))
            .join(Brand, Brand.id == MasterServiceBrand.brand_id)
            .where(
                MasterServiceBrand.master_service_id == master_service_id,
                MasterServiceBrand.is_active.is_(True),
                MasterServiceBrand.status == "active",
                Brand.is_active.is_(True),
                Brand.deleted_at.is_(None),
            )
        ) or 0) if needs_brands else 0

        items = []
        for d in dims:
            cfg = by_dim.get(str(d.id))
            value_count = (
                type_count if d.legacy_source == "service_types"
                else brand_count if d.legacy_source == "brands"
                else int(generic_counts.get(d.id, 0))
            )
            base = {"dimension": d.to_dict(), "value_count": value_count}
            base["config"] = cfg.to_dict() if cfg else {
                "enabled": False, "required": False, "ask_customer": False,
                "show_during_tenant_setup": True, "use_for_matching": False,
                "affects_price": False, "allow_tenant_override": True,
                "allow_all_coverage": True, "allow_selected_coverage": True,
                "allow_exclusion_coverage": True, "display_order": d.display_order,
            }
            items.append(base)
        return {"dimensions": items}

    async def set_service_job_dimension(self, master_service_id: uuid.UUID,
                                        job_type_id: uuid.UUID | None,
                                        dimension_id: uuid.UUID, flags: dict) -> dict:
        await self._load_dimension(dimension_id)
        # Reject any key that isn't a known structural flag -- fail closed so
        # a monetary field can never be persisted through this path.
        unknown = set(flags) - SJD_FLAGS
        if unknown:
            raise ServiceOSException("INVALID_DIMENSION_FLAGS",
                f"Unknown or disallowed flags: {sorted(unknown)}.", status_code=422)

        existing = (await self.db.execute(
            select(ServiceJobDimension).where(
                ServiceJobDimension.master_service_id == master_service_id,
                ServiceJobDimension.dimension_id == dimension_id,
                ServiceJobDimension.job_type_id == job_type_id
                if job_type_id else ServiceJobDimension.job_type_id.is_(None)))).scalar_one_or_none()

        changed = existing is None or any(getattr(existing, key) != value for key, value in flags.items())
        if existing:
            for k, v in flags.items():
                setattr(existing, k, v)
            row = existing
        else:
            row = ServiceJobDimension(master_service_id=master_service_id, job_type_id=job_type_id,
                                      dimension_id=dimension_id, **flags)
            self.db.add(row)
        if changed:
            from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
            await bump_tenant_setup_revision(self.db, master_service_id, job_type_id)
        await self.db.commit()
        await self.db.refresh(row)
        return row.to_dict()

    # ── Blueprint readiness (the right-panel checklist + percentage) ──────────
    async def get_blueprint_readiness(self, master_service_id: uuid.UUID,
                                      job_type_id: uuid.UUID | None) -> dict:
        """Canonical readiness for a (master_service, job_type) blueprint, as
        the approved mockup's right panel shows: a checklist of pass/fail
        checks + a derived percentage + affected-tenant count. The frontend
        must NOT compute this itself -- it renders exactly what this returns."""
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == master_service_id))).scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(master_service_id))

        checks: list[dict] = []

        # Current job-type workflow owns behavior, not the retired master field.
        from app.engines.admin_catalog.models import ServiceJobWorkflow, MasterServiceJobType
        workflow_query = select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == master_service_id,
            ServiceJobWorkflow.is_current.is_(True), ServiceJobWorkflow.status == "published",
        )
        if job_type_id:
            workflow_query = workflow_query.where(ServiceJobWorkflow.job_type_id == job_type_id)
        workflows = (await self.db.execute(workflow_query)).scalars().all()
        linked_query = select(MasterServiceJobType.job_type_id).where(
            MasterServiceJobType.master_service_id == master_service_id, MasterServiceJobType.is_active.is_(True))
        if job_type_id:
            linked_query = linked_query.where(MasterServiceJobType.job_type_id == job_type_id)
        linked = set((await self.db.execute(linked_query)).scalars().all())
        from app.engines.admin_catalog.job_type_blueprint_service import PRICING_BEHAVIORS
        configured = {w.job_type_id for w in workflows if w.pricing_behavior in PRICING_BEHAVIORS}
        workflow_ready = bool(linked) and linked.issubset(configured)
        checks.append({
            "key": "workflow", "label": "Workflow configured",
            "passed": workflow_ready,
            "detail": None if workflow_ready else "Configure and save a valid workflow for every active job type.",
        })

        # 2. Dimensions valid: every enabled dimension has at least one value.
        dim_grid = await self.get_service_job_dimensions(master_service_id, job_type_id)
        enabled_dims = [d for d in dim_grid["dimensions"] if d["config"]["enabled"]]
        dims_valid = all(d["value_count"] > 0 for d in enabled_dims)
        checks.append({
            "key": "dimensions", "label": "Dimensions valid",
            "passed": dims_valid,
            "detail": None if dims_valid else "An enabled dimension has no values configured.",
        })

        # 3. Count usable mappings, not unrelated legacy issue definitions.
        from app.engines.admin_catalog.models import ServiceIssueMapping
        issue_query = select(func.count(ServiceIssueMapping.id)).join(
            MasterIssueType, MasterIssueType.id == ServiceIssueMapping.issue_type_id).where(
            ServiceIssueMapping.master_service_id == master_service_id,
            ServiceIssueMapping.status == 'active', ServiceIssueMapping.deleted_at.is_(None),
            ServiceIssueMapping.customer_visible.is_(True), MasterIssueType.is_active.is_(True),
            MasterIssueType.status == 'active', MasterIssueType.customer_visible.is_(True))
        if job_type_id:
            issue_query = issue_query.where(or_(ServiceIssueMapping.job_type_id == job_type_id,
                                                ServiceIssueMapping.job_type_id.is_(None)))
        issue_count = (await self.db.execute(
            issue_query)).scalar() or 0
        checks.append({
            "key": "problems", "label": "Problems mapped",
            "passed": issue_count > 0,
            "detail": None if issue_count > 0 else "No customer problems mapped to this service yet.",
            "count": issue_count,
        })

        # 4. Tenant rules complete: requires_type/brand flags are internally
        # consistent with the enabled dimensions (a required dimension that
        # isn't enabled is a contradiction).
        contradictions = [d["dimension"]["key"] for d in dim_grid["dimensions"]
                          if d["config"]["required"] and not d["config"]["enabled"]]
        checks.append({
            "key": "tenant_rules", "label": "Tenant rules complete",
            "passed": len(contradictions) == 0,
            "detail": None if not contradictions
            else f"Dimension(s) required but not enabled: {', '.join(contradictions)}.",
        })

        passed = sum(1 for c in checks if c["passed"])
        percent = round(passed / len(checks) * 100) if checks else 0

        affected = (await self.db.execute(
            select(func.count(TenantService.id)).where(
                TenantService.master_service_id == master_service_id,
                TenantService.deleted_at.is_(None)))).scalar() or 0

        actions = [{"key": c["key"], "label": c["label"], "detail": c["detail"]}
                   for c in checks if not c["passed"]]

        return {
            "master_service_id": str(master_service_id),
            "job_type_id": str(job_type_id) if job_type_id else None,
            "percent": percent,
            "ready": len(actions) == 0,
            "checks": checks,
            "actions_required": actions,
            "tenant_setups_affected": affected,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def _load_dimension(self, dimension_id: uuid.UUID) -> CatalogDimension:
        d = (await self.db.execute(
            select(CatalogDimension).where(CatalogDimension.id == dimension_id))).scalar_one_or_none()
        if not d:
            raise NotFoundException("CatalogDimension", str(dimension_id))
        return d

    async def _load_value(self, dimension_id: uuid.UUID, value_id: uuid.UUID) -> CatalogDimensionValue:
        v = (await self.db.execute(select(CatalogDimensionValue).where(
            CatalogDimensionValue.id == value_id,
            CatalogDimensionValue.dimension_id == dimension_id))).scalar_one_or_none()
        if not v:
            raise NotFoundException("CatalogDimensionValue", str(value_id))
        return v
