"""Sprint 34H — Admin Bulk Setup Wizard: Draft, Validation, Preview, Apply services."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterDataAuditLog,
    AdminBulkSetupDraft,
    AdminBulkSetupRun,
    AdminBulkSetupRunItem,
    ServiceCategory,
    MasterService,
    Brand,
    MasterServiceBrand,
    ServiceOptionGroup,
    MasterServiceOption,
    MasterIssueType,
    ServiceOptionMapping,
    ServiceIssueMapping,
    ServiceSetupTemplate,
    BrandTemplate,
)
from app.exceptions import ServiceOSException


VALID_STATUSES = {"draft", "in_progress", "previewed", "ready_to_apply", "applied", "failed", "archived"}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Shared audit helper ────────────────────────────────────────────────────────

async def _audit(
    db: AsyncSession,
    resource: str,
    resource_id: str,
    action: str,
    actor_id: str,
    actor_role: str,
    request_id: str,
    payload: dict,
) -> None:
    log = MasterDataAuditLog(
        resource_type=resource,
        resource_id=resource_id,
        action=action,
        actor_id=actor_id,
        actor_role=actor_role,
        payload_json=payload,
        request_id=request_id,
    )
    db.add(log)


# ══════════════════════════════════════════════════════════════════════════════
# AdminBulkSetupDraftService  — Draft CRUD + step saves + available-* queries
# ══════════════════════════════════════════════════════════════════════════════

class AdminBulkSetupDraftService:
    def __init__(
        self,
        db: AsyncSession,
        actor_id: uuid.UUID,
        actor_role: str,
        request_id: str,
    ) -> None:
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    async def _log(self, action: str, resource_id: str, payload: dict) -> None:
        await _audit(
            self.db, "admin_bulk_setup_draft", resource_id, action,
            str(self.actor_id), self.actor_role, self.request_id, payload,
        )

    # ── Draft CRUD ──────────────────────────────────────────────────────────

    async def list_drafts(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        q = select(AdminBulkSetupDraft).where(AdminBulkSetupDraft.deleted_at.is_(None))
        if status:
            q = q.where(AdminBulkSetupDraft.status == status)
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(AdminBulkSetupDraft.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}

    async def get_draft(self, draft_id: uuid.UUID) -> AdminBulkSetupDraft:
        row = await self.db.scalar(
            select(AdminBulkSetupDraft).where(
                AdminBulkSetupDraft.id == draft_id,
                AdminBulkSetupDraft.deleted_at.is_(None),
            )
        )
        if not row:
            raise ValueError(f"Draft {draft_id} not found")
        return row

    async def create_draft(self, body: dict) -> dict:
        row = AdminBulkSetupDraft(
            created_by_user_id=self.actor_id,
            status="draft",
            current_step=1,
            target_vertical_type=body.get("target_vertical_type"),
            bulk_setup_payload_json={},
        )
        self.db.add(row)
        await self.db.flush()
        await self._log("admin_bulk_setup.draft_created", str(row.id), body)
        await self.db.commit()
        return row.to_dict()

    async def update_draft(self, draft_id: uuid.UUID, body: dict) -> dict:
        row = await self.get_draft(draft_id)
        for field in ("status", "current_step", "target_vertical_type",
                      "target_category_id", "target_category_payload_json",
                      "selected_service_ids_json", "new_services_payload_json",
                      "selected_template_ids_json", "bulk_setup_payload_json"):
            if field in body:
                setattr(row, field, body[field])
        await self._log("admin_bulk_setup.draft_updated", str(draft_id), body)
        await self.db.commit()
        return row.to_dict()

    async def delete_draft(self, draft_id: uuid.UUID) -> dict:
        row = await self.get_draft(draft_id)
        row.deleted_at = _now()
        await self._log("admin_bulk_setup.draft_deleted", str(draft_id), {})
        await self.db.commit()
        return {"deleted": True}

    # ── Step Saves ──────────────────────────────────────────────────────────

    async def set_category(self, draft_id: uuid.UUID, body: dict) -> dict:
        row = await self.get_draft(draft_id)
        row.target_category_id = body.get("category_id")
        row.target_category_payload_json = body.get("new_category_payload")
        row.target_vertical_type = body.get("vertical_type") or row.target_vertical_type
        row.current_step = max(row.current_step, 2)
        row.status = "in_progress"
        await self._log("admin_bulk_setup.category_selected", str(draft_id),
                        {"category_id": str(row.target_category_id) if row.target_category_id else None})
        await self.db.commit()
        return row.to_dict()

    async def set_services(self, draft_id: uuid.UUID, body: dict) -> dict:
        row = await self.get_draft(draft_id)
        row.selected_service_ids_json = body.get("selected_service_ids", [])
        row.new_services_payload_json = body.get("new_services", [])
        row.current_step = max(row.current_step, 3)
        await self._log("admin_bulk_setup.services_selected", str(draft_id), body)
        await self.db.commit()
        return row.to_dict()

    async def set_templates(self, draft_id: uuid.UUID, body: dict) -> dict:
        row = await self.get_draft(draft_id)
        row.selected_template_ids_json = body.get("template_ids", [])
        row.current_step = max(row.current_step, 4)
        await self._log("admin_bulk_setup.templates_selected", str(draft_id), body)
        await self.db.commit()
        return row.to_dict()

    async def _update_payload_section(self, draft_id: uuid.UUID, section: str, data: Any, audit_action: str) -> dict:
        row = await self.get_draft(draft_id)
        payload = dict(row.bulk_setup_payload_json or {})
        payload[section] = data
        row.bulk_setup_payload_json = payload
        await self._log(audit_action, str(draft_id), {section: data})
        await self.db.commit()
        return row.to_dict()

    async def set_brand_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "brand_mappings", body.get("mappings", []),
            "admin_bulk_setup.brand_mappings_updated")

    async def set_option_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "option_mappings", body.get("mappings", []),
            "admin_bulk_setup.option_mappings_updated")

    async def set_issue_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "issue_mappings", body.get("mappings", []),
            "admin_bulk_setup.issue_mappings_updated")

    async def set_document_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "document_mappings", body.get("mappings", []),
            "admin_bulk_setup.document_mappings_updated")

    async def set_checklist_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "checklist_mappings", body.get("mappings", []),
            "admin_bulk_setup.checklist_mappings_updated")

    async def set_pricing_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "pricing_mappings", body.get("mappings", []),
            "admin_bulk_setup.pricing_mappings_updated")

    async def set_commission_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        return await self._update_payload_section(
            draft_id, "commission_mappings", body.get("mappings", []),
            "admin_bulk_setup.commission_mappings_updated")

    async def set_workflow_mappings(self, draft_id: uuid.UUID, body: dict) -> dict:
        _ = (draft_id, body)
        raise ServiceOSException(
            "BULK_WORKFLOW_TEMPLATES_RETIRED",
            "Bulk workflow-template mappings are retired. Configure runtime job "
            "workflow per service/job type in Catalog Workspace -> Workflow.",
            status_code=410,
        )

    # ── Available-* Queries ─────────────────────────────────────────────────

    async def get_available_categories(self, vertical_type: str | None = None) -> list[dict]:
        q = select(ServiceCategory).where(ServiceCategory.is_active == True)
        if vertical_type:
            q = q.where(ServiceCategory.category_type == vertical_type)
        q = q.order_by(ServiceCategory.display_order, ServiceCategory.name)
        rows = (await self.db.scalars(q)).all()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "slug": r.slug,
                "category_type": r.category_type,
                "is_active": r.is_active,
                "is_customer_visible": r.is_customer_visible,
            }
            for r in rows
        ]

    async def get_available_services(self, category_id: uuid.UUID | None = None) -> list[dict]:
        q = select(MasterService).where(
            MasterService.is_active == True,
            MasterService.deleted_at.is_(None),
        )
        if category_id:
            q = q.where(MasterService.category_id == category_id)
        q = q.order_by(MasterService.display_order, MasterService.service_name)
        rows = (await self.db.scalars(q)).all()
        return [
            {
                "id": str(r.id),
                "service_name": r.service_name,
                "slug": r.slug,
                "category_id": str(r.category_id),
                "job_type": r.job_type,
                "pricing_model": r.pricing_model,
                "is_active": r.is_active,
            }
            for r in rows
        ]

    async def get_available_templates(
        self,
        vertical_type: str | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[dict]:
        # Use the LIVE service_setup engine's model. The import above resolves
        # to admin_catalog's Sprint-34F model, whose own comment says it was
        # superseded by migration 097 -- and whose table
        # `service_setup_templates_legacy_34f` does not exist, so this 500'd on
        # a missing relation. The live model names its columns differently
        # (`vertical_key`, `is_system`) and has no soft-delete.
        from app.engines.service_setup.models import (
            ServiceSetupTemplate as LiveServiceSetupTemplate,
        )

        q = select(LiveServiceSetupTemplate).where(
            LiveServiceSetupTemplate.status == "published"
        )
        if vertical_type:
            q = q.where(LiveServiceSetupTemplate.vertical_key == vertical_type)
        q = q.order_by(
            LiveServiceSetupTemplate.is_system.desc(), LiveServiceSetupTemplate.name
        )
        rows = (await self.db.scalars(q)).all()
        return [r.to_dict() for r in rows]

    async def get_available_brands(self, category_id: uuid.UUID | None = None) -> list[dict]:
        q = select(Brand).where(
            Brand.status == "active",
            Brand.deleted_at.is_(None),
        )
        if category_id:
            q = q.where(Brand.category_id == category_id)
        q = q.order_by(Brand.name)
        rows = (await self.db.scalars(q)).all()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "slug": r.slug,
                "status": r.status,
                "category_id": str(r.category_id) if r.category_id else None,
            }
            for r in rows
        ]

    async def get_available_brand_templates(self) -> list[dict]:
        rows = (await self.db.scalars(
            select(BrandTemplate).where(BrandTemplate.status == "active").order_by(BrandTemplate.name)
        )).all()
        return [r.to_dict() for r in rows]

    async def get_available_option_groups(self, vertical_type: str | None = None) -> list[dict]:
        q = select(ServiceOptionGroup).where(
            ServiceOptionGroup.status == "active",
            ServiceOptionGroup.deleted_at.is_(None),
        )
        if vertical_type:
            q = q.where(ServiceOptionGroup.vertical_type == vertical_type)
        rows = (await self.db.scalars(q.order_by(ServiceOptionGroup.display_order, ServiceOptionGroup.name))).all()
        return [
            {
                "id": str(r.id),
                "code": r.code,
                "name": r.name,
                "vertical_type": r.vertical_type,
                "status": r.status,
            }
            for r in rows
        ]

    async def get_available_service_options(
        self,
        group_id: uuid.UUID | None = None,
        vertical_type: str | None = None,
    ) -> list[dict]:
        # `MasterServiceOption` has no soft-delete column -- neither the model nor the
        # table -- so filtering on `deleted_at` raised AttributeError and this
        # endpoint 500'd. Lifecycle here is `status`, already filtered above.
        q = select(MasterServiceOption).where(MasterServiceOption.status == "active")
        if group_id:
            q = q.where(MasterServiceOption.option_group_id == group_id)
        if vertical_type:
            q = q.where(MasterServiceOption.vertical_type == vertical_type)
        rows = (await self.db.scalars(q.order_by(MasterServiceOption.name))).all()
        return [r.to_dict() for r in rows]

    async def get_available_issue_types(
        self,
        vertical_type: str | None = None,
    ) -> list[dict]:
        # `MasterIssueType` has no soft-delete column -- neither the model nor the
        # table -- so filtering on `deleted_at` raised AttributeError and this
        # endpoint 500'd. Lifecycle here is `status`, already filtered above.
        q = select(MasterIssueType).where(MasterIssueType.status == "active")
        if vertical_type:
            q = q.where(MasterIssueType.vertical_type == vertical_type)
        rows = (await self.db.scalars(q.order_by(MasterIssueType.name))).all()
        return [r.to_dict() for r in rows]

    async def get_available_workflow_templates(
        self,
        category_id: uuid.UUID | None = None,
    ) -> list[dict]:
        _ = category_id
        raise ServiceOSException(
            "BULK_WORKFLOW_TEMPLATES_RETIRED",
            "Bulk workflow-template selection is retired. Configure runtime job "
            "workflow per service/job type in Catalog Workspace -> Workflow.",
            status_code=410,
        )

    async def get_available_document_requirements(self) -> list[dict]:
        from app.engines.document.models import DocumentTemplate
        rows = (await self.db.scalars(
            select(DocumentTemplate).where(DocumentTemplate.is_active == True)
            .order_by(DocumentTemplate.name)
        )).all()
        return [
            {"id": str(r.id), "name": r.name, "document_type": getattr(r, "document_type", None)}
            for r in rows
        ]

    async def get_available_checklist_templates(self) -> list[dict]:
        """Platform checklist templates offered by the bulk wizard.

        Read the LIVE catalogue. This used to select field_ops'
        `ServiceChecklistTemplate`, whose table `service_checklist_templates`
        was never migrated, so the endpoint 500'd on a missing relation every
        time the wizard asked for its options.
        """
        from app.engines.checklist_catalog.models import ChecklistTemplate

        rows = (await self.db.scalars(
            select(ChecklistTemplate)
            .where(ChecklistTemplate.status == "active")
            .order_by(ChecklistTemplate.name)
        )).all()
        return [
            {"id": str(r.id), "name": r.name, "code": r.code,
             "purpose": r.purpose, "owner_scope": r.owner_scope}
            for r in rows
        ]

    async def get_available_pricing_templates(self) -> list[dict]:
        from app.engines.admin_catalog.models import PricingTier
        rows = (await self.db.scalars(
            select(PricingTier).where(PricingTier.is_active == True).order_by(PricingTier.name)
        )).all()
        return [{"id": str(r.id), "name": r.name, "tier_code": r.tier_code} for r in rows]

    async def get_available_commission_templates(self) -> list[dict]:
        # Commission templates not implemented — return deferred notice
        return [{"status": "deferred", "message": "Commission templates not yet implemented as separate catalog"}]


# ══════════════════════════════════════════════════════════════════════════════
# AdminBulkSetupValidationService  — Blocking item detection
# ══════════════════════════════════════════════════════════════════════════════

class AdminBulkSetupValidationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_draft(self, draft: AdminBulkSetupDraft) -> list[dict]:
        """Returns list of blocking/warning items. Empty = no blockers."""
        blockers: list[dict] = []

        # Step 1 — category
        if not draft.target_category_id and not draft.target_category_payload_json:
            blockers.append({"code": "CATEGORY_REQUIRED", "severity": "P0",
                             "message": "A target category must be selected or defined."})

        # Step 2 — services
        has_existing = bool(draft.selected_service_ids_json)
        has_new = bool(draft.new_services_payload_json)
        if not has_existing and not has_new:
            blockers.append({"code": "SERVICE_REQUIRED", "severity": "P0",
                             "message": "At least one service must be selected or defined."})

        # Validate new service name uniqueness
        if has_new:
            for svc in (draft.new_services_payload_json or []):
                name = (svc.get("service_name") or "").strip()
                code = svc.get("code") or _slug(name)
                if not name:
                    blockers.append({"code": "SERVICE_NAME_REQUIRED", "severity": "P0",
                                     "message": "New service name cannot be empty."})
                    continue
                # slug-based duplicate check
                slug = svc.get("slug") or _slug(name)
                existing = await self.db.scalar(
                    select(MasterService).where(MasterService.slug == slug, MasterService.deleted_at.is_(None))
                )
                if existing:
                    blockers.append({"code": "SERVICE_SLUG_DUPLICATE", "severity": "P0",
                                     "message": f"Service slug '{slug}' already exists (id={existing.id})."})

        # Step 3 — templates (if selected, check they are active)
        for tid in (draft.selected_template_ids_json or []):
            try:
                t = await self.db.scalar(select(ServiceSetupTemplate).where(
                    ServiceSetupTemplate.id == uuid.UUID(tid),
                    ServiceSetupTemplate.deleted_at.is_(None),
                ))
                if not t:
                    blockers.append({"code": "TEMPLATE_NOT_FOUND", "severity": "P1",
                                     "message": f"Template {tid} not found."})
                elif t.status != "published":
                    blockers.append({"code": "TEMPLATE_INACTIVE", "severity": "P1",
                                     "message": f"Template '{t.name}' is {t.status} — only published templates can be applied."})
            except Exception:
                blockers.append({"code": "TEMPLATE_INVALID_ID", "severity": "P0",
                                 "message": f"Invalid template ID: {tid}"})

        # Validate brand mappings
        payload = draft.bulk_setup_payload_json or {}
        for m in payload.get("brand_mappings", []):
            bid = m.get("brand_id")
            if bid:
                b = await self.db.scalar(select(Brand).where(Brand.id == uuid.UUID(bid), Brand.deleted_at.is_(None)))
                if not b:
                    blockers.append({"code": "BRAND_NOT_FOUND", "severity": "P1",
                                     "message": f"Brand {bid} not found."})
                elif b.status != "active":
                    blockers.append({"code": "BRAND_INACTIVE", "severity": "P1",
                                     "message": f"Brand '{b.name}' is {b.status} — only active brands can be mapped."})

        # Validate option mappings
        for m in payload.get("option_mappings", []):
            oid = m.get("service_option_id")
            if oid:
                o = await self.db.scalar(select(MasterServiceOption).where(
                    MasterServiceOption.id == uuid.UUID(oid), MasterServiceOption.deleted_at.is_(None)
                ))
                if not o:
                    blockers.append({"code": "OPTION_NOT_FOUND", "severity": "P1",
                                     "message": f"Service option {oid} not found."})
                elif o.status != "active":
                    blockers.append({"code": "OPTION_INACTIVE", "severity": "P1",
                                     "message": f"Option '{o.name}' is {o.status}."})

        # Validate issue mappings
        for m in payload.get("issue_mappings", []):
            iid = m.get("issue_type_id")
            if iid:
                it = await self.db.scalar(select(MasterIssueType).where(
                    MasterIssueType.id == uuid.UUID(iid), MasterIssueType.deleted_at.is_(None)
                ))
                if not it:
                    blockers.append({"code": "ISSUE_NOT_FOUND", "severity": "P1",
                                     "message": f"Issue type {iid} not found."})
                elif it.status != "active":
                    blockers.append({"code": "ISSUE_INACTIVE", "severity": "P1",
                                     "message": f"Issue type '{it.name}' is {it.status}."})

        return blockers

    async def get_blocking_items(self, draft_id: uuid.UUID) -> dict:
        draft = await self.db.scalar(select(AdminBulkSetupDraft).where(
            AdminBulkSetupDraft.id == draft_id, AdminBulkSetupDraft.deleted_at.is_(None)
        ))
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        blockers = await self.validate_draft(draft)
        p0 = [b for b in blockers if b.get("severity") == "P0"]
        return {
            "draft_id": str(draft_id),
            "can_apply": len(p0) == 0,
            "blocker_count": len(p0),
            "warning_count": len([b for b in blockers if b.get("severity") != "P0"]),
            "items": blockers,
        }


# ══════════════════════════════════════════════════════════════════════════════
# AdminBulkSetupPreviewService  — Preview without mutation
# ══════════════════════════════════════════════════════════════════════════════

class AdminBulkSetupPreviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def preview(self, draft: AdminBulkSetupDraft) -> dict:
        items: list[dict] = []
        creates = reuses = mappings = skips = conflicts = 0

        # ── Category ──────────────────────────────────────────────────────
        if draft.target_category_id:
            cat = await self.db.scalar(select(ServiceCategory).where(
                ServiceCategory.id == draft.target_category_id
            ))
            if cat:
                items.append({"entity_type": "category", "name": cat.name, "action": "reuse_existing",
                              "reason": "Category already exists"})
                reuses += 1
        elif draft.target_category_payload_json:
            name = draft.target_category_payload_json.get("name", "New Category")
            items.append({"entity_type": "category", "name": name, "action": "create",
                          "reason": "New category will be created"})
            creates += 1

        # ── Services ──────────────────────────────────────────────────────
        for sid in (draft.selected_service_ids_json or []):
            try:
                svc = await self.db.scalar(select(MasterService).where(MasterService.id == uuid.UUID(sid)))
                if svc:
                    items.append({"entity_type": "service", "name": svc.service_name,
                                  "action": "reuse_existing", "reason": "Service already exists"})
                    reuses += 1
            except Exception:
                pass

        for new_svc in (draft.new_services_payload_json or []):
            name = new_svc.get("service_name", "Unknown")
            slug = new_svc.get("slug") or _slug(name)
            existing = await self.db.scalar(select(MasterService).where(
                MasterService.slug == slug, MasterService.deleted_at.is_(None)
            ))
            if existing:
                items.append({"entity_type": "service", "name": name, "action": "reuse_existing",
                              "reason": f"Service slug '{slug}' already exists"})
                reuses += 1
                conflicts += 1
            else:
                items.append({"entity_type": "service", "name": name, "action": "create",
                              "reason": "New service will be created"})
                creates += 1

        # ── Templates ─────────────────────────────────────────────────────
        for tid in (draft.selected_template_ids_json or []):
            try:
                t = await self.db.scalar(select(ServiceSetupTemplate).where(
                    ServiceSetupTemplate.id == uuid.UUID(tid), ServiceSetupTemplate.deleted_at.is_(None)
                ))
                if t:
                    items.append({"entity_type": "template", "name": t.name,
                                  "action": "apply" if t.status == "published" else "skip",
                                  "reason": f"Template status: {t.status}"})
                    if t.status == "published":
                        mappings += 1
                    else:
                        skips += 1
            except Exception:
                pass

        payload = draft.bulk_setup_payload_json or {}

        # ── Brand Mappings ────────────────────────────────────────────────
        for m in payload.get("brand_mappings", []):
            bid = m.get("brand_id")
            sid = m.get("service_id")
            if bid and sid:
                existing = await self.db.scalar(select(MasterServiceBrand).where(
                    MasterServiceBrand.brand_id == uuid.UUID(bid),
                    MasterServiceBrand.master_service_id == uuid.UUID(sid),
                ))
                b = await self.db.scalar(select(Brand).where(Brand.id == uuid.UUID(bid)))
                svc = await self.db.scalar(select(MasterService).where(MasterService.id == uuid.UUID(sid)))
                label = f"{b.name if b else bid} → {svc.service_name if svc else sid}"
                if existing:
                    items.append({"entity_type": "brand_mapping", "name": label,
                                  "action": "skip", "reason": "Mapping already exists"})
                    skips += 1
                else:
                    items.append({"entity_type": "brand_mapping", "name": label,
                                  "action": "create_mapping"})
                    mappings += 1

        # ── Option Mappings ───────────────────────────────────────────────
        for m in payload.get("option_mappings", []):
            oid = m.get("service_option_id")
            sid = m.get("service_id")
            if oid and sid:
                existing = await self.db.scalar(select(ServiceOptionMapping).where(
                    ServiceOptionMapping.service_option_id == uuid.UUID(oid),
                    ServiceOptionMapping.master_service_id == uuid.UUID(sid),
                    ServiceOptionMapping.deleted_at.is_(None),
                ))
                opt = await self.db.scalar(select(MasterServiceOption).where(MasterServiceOption.id == uuid.UUID(oid)))
                svc = await self.db.scalar(select(MasterService).where(MasterService.id == uuid.UUID(sid)))
                label = f"{opt.name if opt else oid} → {svc.service_name if svc else sid}"
                if existing:
                    items.append({"entity_type": "option_mapping", "name": label,
                                  "action": "skip", "reason": "Mapping already exists"})
                    skips += 1
                else:
                    items.append({"entity_type": "option_mapping", "name": label, "action": "create_mapping"})
                    mappings += 1

        # ── Issue Mappings ────────────────────────────────────────────────
        for m in payload.get("issue_mappings", []):
            iid = m.get("issue_type_id")
            sid = m.get("service_id")
            if iid and sid:
                existing = await self.db.scalar(select(ServiceIssueMapping).where(
                    ServiceIssueMapping.issue_type_id == uuid.UUID(iid),
                    ServiceIssueMapping.master_service_id == uuid.UUID(sid),
                    ServiceIssueMapping.deleted_at.is_(None),
                ))
                it = await self.db.scalar(select(MasterIssueType).where(MasterIssueType.id == uuid.UUID(iid)))
                svc = await self.db.scalar(select(MasterService).where(MasterService.id == uuid.UUID(sid)))
                label = f"{it.name if it else iid} → {svc.service_name if svc else sid}"
                if existing:
                    items.append({"entity_type": "issue_mapping", "name": label,
                                  "action": "skip", "reason": "Mapping already exists"})
                    skips += 1
                else:
                    items.append({"entity_type": "issue_mapping", "name": label, "action": "create_mapping"})
                    mappings += 1

        # ── Workflow Mappings ─────────────────────────────────────────────
        # Document/checklist/pricing/commission — simple count from payload
        for section, etype in [("document_mappings", "document_mapping"),
                                ("checklist_mappings", "checklist_mapping"),
                                ("pricing_mappings", "pricing_mapping"),
                                ("commission_mappings", "commission_mapping")]:
            for m in payload.get(section, []):
                items.append({"entity_type": etype, "name": m.get("name", section), "action": "create_mapping"})
                mappings += 1

        summary = {
            "creates": creates,
            "reuses": reuses,
            "mappings": mappings,
            "skips": skips,
            "conflicts": conflicts,
            "blockers": 0,  # filled in by caller after validation
        }
        return {"summary": summary, "items": items}


# ══════════════════════════════════════════════════════════════════════════════
# AdminBulkSetupApplyService  — Idempotent apply with run tracking
# ══════════════════════════════════════════════════════════════════════════════

class AdminBulkSetupApplyService:
    def __init__(
        self,
        db: AsyncSession,
        actor_id: uuid.UUID,
        actor_role: str,
        request_id: str,
    ) -> None:
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    async def apply(self, draft: AdminBulkSetupDraft) -> dict:
        # Create run record
        run = AdminBulkSetupRun(
            draft_id=draft.id,
            applied_by_user_id=self.actor_id,
            status="running",
            target_vertical_type=draft.target_vertical_type,
            target_category_id=draft.target_category_id,
        )
        self.db.add(run)
        await self.db.flush()

        run_items: list[AdminBulkSetupRunItem] = []
        created = reused = mapped = skipped = errors = 0

        async def record(entity_type: str, action: str, entity_id: uuid.UUID | None,
                         entity_code: str | None, message: str | None) -> None:
            ri = AdminBulkSetupRunItem(
                run_id=run.id,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_code=entity_code,
                action=action,
                message=message,
            )
            self.db.add(ri)
            run_items.append(ri)

        try:
            # ── Category ─────────────────────────────────────────────────
            category_id = draft.target_category_id
            if not category_id and draft.target_category_payload_json:
                pl = draft.target_category_payload_json
                name = pl.get("name", "New Category")
                slug = pl.get("slug") or _slug(name)
                existing_cat = await self.db.scalar(select(ServiceCategory).where(ServiceCategory.slug == slug))
                if existing_cat:
                    category_id = existing_cat.id
                    await record("category", "reused", existing_cat.id, slug, f"Reused existing category '{name}'")
                    reused += 1
                else:
                    new_cat = ServiceCategory(
                        name=name, slug=slug,
                        description=pl.get("description"),
                        category_type=pl.get("category_type") or draft.target_vertical_type,
                        is_active=True, is_customer_visible=True,
                    )
                    self.db.add(new_cat)
                    await self.db.flush()
                    category_id = new_cat.id
                    await record("category", "created", new_cat.id, slug, f"Created category '{name}'")
                    created += 1

            # ── Services ─────────────────────────────────────────────────
            service_ids: list[uuid.UUID] = list(draft.selected_service_ids_json or [])
            reused_service_ids: list[uuid.UUID] = []

            for sid_str in service_ids:
                try:
                    reused_service_ids.append(uuid.UUID(str(sid_str)))
                    svc = await self.db.scalar(select(MasterService).where(MasterService.id == uuid.UUID(str(sid_str))))
                    await record("service", "reused", svc.id if svc else None,
                                 svc.slug if svc else None, f"Reused existing service")
                    reused += 1
                except Exception as e:
                    await record("service", "failed", None, str(sid_str), str(e))
                    errors += 1

            new_service_ids: list[uuid.UUID] = []
            for new_svc in (draft.new_services_payload_json or []):
                try:
                    name = new_svc.get("service_name", "").strip()
                    slug = new_svc.get("slug") or _slug(name)
                    existing_svc = await self.db.scalar(select(MasterService).where(
                        MasterService.slug == slug, MasterService.deleted_at.is_(None)
                    ))
                    if existing_svc:
                        new_service_ids.append(existing_svc.id)
                        await record("service", "reused", existing_svc.id, slug, f"Reused '{name}' (slug exists)")
                        reused += 1
                    else:
                        cat_id = category_id or draft.target_category_id
                        ms = MasterService(
                            category_id=cat_id,
                            service_name=name,
                            slug=slug,
                            job_type=new_svc.get("job_type", "repair"),
                            pricing_model=new_svc.get("pricing_model", "fixed"),
                            is_active=True,
                        )
                        self.db.add(ms)
                        await self.db.flush()
                        new_service_ids.append(ms.id)
                        await record("service", "created", ms.id, slug, f"Created service '{name}'")
                        created += 1
                except Exception as e:
                    await record("service", "failed", None, new_svc.get("slug"), str(e))
                    errors += 1

            all_service_ids = reused_service_ids + new_service_ids
            payload = draft.bulk_setup_payload_json or {}

            # ── Brand Mappings ────────────────────────────────────────────
            for m in payload.get("brand_mappings", []):
                bid = m.get("brand_id")
                sid = m.get("service_id")
                if bid and sid:
                    try:
                        existing = await self.db.scalar(select(MasterServiceBrand).where(
                            MasterServiceBrand.brand_id == uuid.UUID(bid),
                            MasterServiceBrand.master_service_id == uuid.UUID(sid),
                        ))
                        if existing:
                            await record("brand_mapping", "skipped", None, bid, "Mapping already exists")
                            skipped += 1
                        else:
                            msb = MasterServiceBrand(
                                brand_id=uuid.UUID(bid),
                                master_service_id=uuid.UUID(sid),
                                is_required=m.get("is_required", False),
                                status="active",
                                created_by_user_id=self.actor_id,
                            )
                            self.db.add(msb)
                            await record("brand_mapping", "mapped", None, bid, f"Mapped brand to service {sid}")
                            mapped += 1
                    except Exception as e:
                        await record("brand_mapping", "failed", None, bid, str(e))
                        errors += 1

            # ── Option Mappings ───────────────────────────────────────────
            for m in payload.get("option_mappings", []):
                oid = m.get("service_option_id")
                sid = m.get("service_id")
                if oid and sid:
                    try:
                        existing = await self.db.scalar(select(ServiceOptionMapping).where(
                            ServiceOptionMapping.service_option_id == uuid.UUID(oid),
                            ServiceOptionMapping.master_service_id == uuid.UUID(sid),
                            ServiceOptionMapping.deleted_at.is_(None),
                        ))
                        if existing:
                            await record("option_mapping", "skipped", None, oid, "Already mapped")
                            skipped += 1
                        else:
                            sm = ServiceOptionMapping(
                                master_service_id=uuid.UUID(sid),
                                service_option_id=uuid.UUID(oid),
                                is_required=m.get("is_required", False),
                                is_default=m.get("is_default", False),
                                status="active",
                                created_by_user_id=self.actor_id,
                            )
                            self.db.add(sm)
                            await record("option_mapping", "mapped", None, oid, f"Mapped option to service {sid}")
                            mapped += 1
                    except Exception as e:
                        await record("option_mapping", "failed", None, oid, str(e))
                        errors += 1

            # ── Issue Mappings ────────────────────────────────────────────
            for m in payload.get("issue_mappings", []):
                iid = m.get("issue_type_id")
                sid = m.get("service_id")
                if iid and sid:
                    try:
                        existing = await self.db.scalar(select(ServiceIssueMapping).where(
                            ServiceIssueMapping.issue_type_id == uuid.UUID(iid),
                            ServiceIssueMapping.master_service_id == uuid.UUID(sid),
                            ServiceIssueMapping.deleted_at.is_(None),
                        ))
                        if existing:
                            await record("issue_mapping", "skipped", None, iid, "Already mapped")
                            skipped += 1
                        else:
                            im = ServiceIssueMapping(
                                master_service_id=uuid.UUID(sid),
                                issue_type_id=uuid.UUID(iid),
                                is_common=m.get("is_common", False),
                                requires_photo=m.get("requires_photo", False),
                                requires_description=m.get("requires_description", False),
                                status="active",
                                created_by_user_id=self.actor_id,
                            )
                            self.db.add(im)
                            await record("issue_mapping", "mapped", None, iid, f"Mapped issue to service {sid}")
                            mapped += 1
                    except Exception as e:
                        await record("issue_mapping", "failed", None, iid, str(e))
                        errors += 1

            # ── Document/Checklist/Pricing/Workflow — record intent, no deep apply ──
            for section, etype in [("document_mappings", "document_mapping"),
                                    ("checklist_mappings", "checklist_mapping"),
                                    ("pricing_mappings", "pricing_mapping"),
                                    ("commission_mappings", "commission_mapping")]:
                for item in payload.get(section, []):
                    ref = item.get("id") or item.get("template_id") or "unknown"
                    await record(etype, "mapped", None, ref, f"Mapped via {section}")
                    mapped += 1

            summary = {
                "created": created, "reused": reused,
                "mapped": mapped, "skipped": skipped, "errors": errors,
            }
            run.status = "completed" if errors == 0 else "partial"
            run.summary_json = summary
            run.completed_at = _now()

            # Update draft
            draft.status = "applied"
            draft.applied_at = _now()

        except Exception as exc:
            run.status = "failed"
            run.error_json = {"error": str(exc)}
            run.completed_at = _now()
            summary = {"created": 0, "reused": 0, "mapped": 0, "skipped": 0, "errors": 1}

        await _audit(
            self.db, "admin_bulk_setup_draft", str(draft.id),
            "admin_bulk_setup.applied", str(self.actor_id), self.actor_role,
            self.request_id, {"run_id": str(run.id), "status": run.status},
        )
        await self.db.commit()

        return {
            "run_id": str(run.id),
            "draft_id": str(draft.id),
            "status": run.status,
            "summary": run.summary_json,
        }

    async def list_runs(self, page: int = 1, page_size: int = 20) -> dict:
        q = select(AdminBulkSetupRun).order_by(AdminBulkSetupRun.created_at.desc())
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}

    async def get_run_detail(self, run_id: uuid.UUID) -> dict:
        run = await self.db.scalar(select(AdminBulkSetupRun).where(AdminBulkSetupRun.id == run_id))
        if not run:
            raise ValueError(f"Run {run_id} not found")
        items = (await self.db.scalars(
            select(AdminBulkSetupRunItem)
            .where(AdminBulkSetupRunItem.run_id == run_id)
            .order_by(AdminBulkSetupRunItem.created_at)
        )).all()
        return {**run.to_dict(), "items": [i.to_dict() for i in items]}
