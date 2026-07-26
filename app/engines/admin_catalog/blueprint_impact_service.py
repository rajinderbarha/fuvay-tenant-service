"""Admin Blueprint Impact Report -- service layer.

Backs the approved Admin Catalog page's right-panel "Version & impact" +
"Impact Report". Produces a STRUCTURED diff of the pending (unpublished)
structural changes to a master service's blueprint vs the last published
version, plus the count of tenant setups that would need review.

Built on the real service_blueprint_versions table (migration 153) +
service_job_dimensions (migration 154). No monetary data. The frontend
renders exactly what this returns -- it does not recompute impact.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterService, ServiceBlueprintVersion, ServiceJobDimension,
    CatalogDimension, TenantService,
)
from app.exceptions import NotFoundException, ServiceOSException

# Human labels for the structural fields a blueprint snapshot tracks.
_FIELD_LABELS = {
    "job_type": "Job type",
    "requires_type": "Type required",
    "requires_brand": "Brand required",
    "pricing_model": "Pricing model",
    "is_active": "Active",
}


class BlueprintImpactService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_impact_report(self, master_service_id: uuid.UUID) -> dict:
        """NOTE on the draft model (surfaced honestly): the current backend
        auto-publishes a new blueprint version on every structural admin edit
        (migration 153) -- there is no accumulating "draft changes" staging
        layer yet. So this report describes the delta of the MOST RECENT
        publish (latest version vs the one before it) -- real, useful "what
        changed last" impact -- rather than a forward-looking pending diff
        that has no backing store. `has_pending_changes` is therefore always
        derived from that last-publish delta, and the mockup's "Draft changes
        · N" counter is a genuine remaining gap (no draft layer exists)."""
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == master_service_id))).scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(master_service_id))

        versions = (await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == master_service_id,
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(2))).scalars().all()

        latest = versions[0] if versions else None
        previous = versions[1] if len(versions) > 1 else None

        # ── Structural field changes: latest published vs the prior version ──
        changed_requirements: list[dict] = []
        added_dimensions: list[str] = []
        removed_dimensions: list[str] = []
        if latest and previous:
            cur_snap, prev_snap = latest.snapshot, previous.snapshot
            for field in _FIELD_LABELS:
                cur_val, prev_val = cur_snap.get(field), prev_snap.get(field)
                if prev_val != cur_val:
                    changed_requirements.append({
                        "field": field, "label": _FIELD_LABELS.get(field, field),
                        "from": prev_val, "to": cur_val,
                    })
                    # Type/Brand being newly required/unrequired == a dimension
                    # appearing/disappearing from the tenant setup wizard.
                    if field == "requires_type":
                        (added_dimensions if cur_val else removed_dimensions).append("Type")
                    if field == "requires_brand":
                        (added_dimensions if cur_val else removed_dimensions).append("Brand")

        # ── Tenant setups needing review ────────────────────────────────────
        # A setup needs review if its recorded blueprint version isn't the
        # latest published one, OR (fail closed) has no recorded version.
        affected_total = (await self.db.execute(
            select(func.count(TenantService.id)).where(
                TenantService.master_service_id == master_service_id,
                TenantService.deleted_at.is_(None)))).scalar() or 0

        if latest:
            need_review = (await self.db.execute(
                select(func.count(TenantService.id)).where(
                    TenantService.master_service_id == master_service_id,
                    TenantService.deleted_at.is_(None),
                    (TenantService.blueprint_version_id != latest.id)
                    | (TenantService.blueprint_version_id.is_(None))))).scalar() or 0
        else:
            need_review = affected_total  # no baseline -> all need review

        return {
            "master_service_id": str(master_service_id),
            "current_version": latest.version_number if latest else None,
            "previous_version": previous.version_number if previous else None,
            "last_change_summary": latest.change_summary if latest else None,
            "added_dimensions": added_dimensions,
            "removed_dimensions": removed_dimensions,
            "changed_requirements": changed_requirements,
            "tenants_affected": affected_total,
            "setups_need_review": need_review,
            "last_published_at": latest.published_at.isoformat() if latest and latest.published_at else None,
        }

    # ── Draft status + explicit publish ─────────────────────────────────────
    # As of this method, structural MasterService edits (update_master_service)
    # no longer auto-publish a new ServiceBlueprintVersion. This diffs the
    # LIVE row against the latest PUBLISHED snapshot to compute a real
    # "Draft changes · N" count, and publish_draft() below is the only thing
    # that turns a draft into a new published version.
    async def get_draft_status(self, master_service_id: uuid.UUID) -> dict:
        from app.engines.admin_catalog.service import AdminCatalogService
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == master_service_id))).scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(master_service_id))

        admin_svc = AdminCatalogService(self.db)
        live = admin_svc._blueprint_snapshot(svc)  # noqa: SLF001 -- same engine, shared snapshot logic
        latest = (await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == master_service_id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1))).scalar_one_or_none()
        published = latest.snapshot if latest else {}

        changed_fields = [
            {"field": k, "label": _FIELD_LABELS.get(k, k), "from": published.get(k), "to": live[k]}
            for k in live if published.get(k) != live[k]
        ]
        return {
            "master_service_id": str(master_service_id),
            "has_pending_changes": len(changed_fields) > 0,
            "pending_change_count": len(changed_fields),
            "changed_fields": changed_fields,
            "current_published_version": latest.version_number if latest else None,
        }

    async def publish_draft(self, master_service_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> dict:
        from app.engines.admin_catalog.service import AdminCatalogService
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == master_service_id))).scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(master_service_id))

        admin_svc = AdminCatalogService(self.db)
        latest = (await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == master_service_id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1))).scalar_one_or_none()
        before = latest.snapshot if latest else {}

        new_version = await admin_svc._publish_new_blueprint_version_if_structural_change(  # noqa: SLF001
            svc, before, actor_id)
        if new_version is None:
            raise ServiceOSException("NO_PENDING_CHANGES",
                "There are no pending structural changes to publish.", status_code=409)
        await self.db.commit()
        return {"published": True, "version_number": new_version.version_number,
                "change_summary": new_version.change_summary}
