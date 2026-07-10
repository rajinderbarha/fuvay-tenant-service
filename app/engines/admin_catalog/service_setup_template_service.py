"""Sprint 34F — Service Setup Template CRUD, lifecycle, preview and apply."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterDataAuditLog,
    ServiceSetupTemplate,
    ServiceSetupTemplateItem,
    ServiceSetupTemplateRelationship,
    ServiceSetupTemplateRun,
    ServiceSetupTemplateRunItem,
)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ServiceSetupTemplateService:
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

    async def _audit(self, resource: str, resource_id: str, action: str, payload: dict) -> None:
        log = MasterDataAuditLog(
            resource_type=resource,
            resource_id=resource_id,
            action=action,
            actor_id=str(self.actor_id),
            actor_role=self.actor_role,
            payload_json=payload,
            request_id=self.request_id,
        )
        self.db.add(log)

    # ── Template CRUD ─────────────────────────────────────────────────────────

    async def list_templates(
        self,
        status: str | None = None,
        vertical_type: str | None = None,
        template_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        q = select(ServiceSetupTemplate).where(ServiceSetupTemplate.deleted_at.is_(None))
        if status:
            q = q.where(ServiceSetupTemplate.status == status)
        if vertical_type:
            q = q.where(ServiceSetupTemplate.vertical_type == vertical_type)
        if template_type:
            q = q.where(ServiceSetupTemplate.template_type == template_type)
        if search:
            q = q.where(
                ServiceSetupTemplate.name.ilike(f"%{search}%")
                | ServiceSetupTemplate.code.ilike(f"%{search}%")
            )
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(ServiceSetupTemplate.name).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}

    async def get_template(self, template_id: uuid.UUID) -> ServiceSetupTemplate:
        row = await self.db.scalar(
            select(ServiceSetupTemplate).where(
                ServiceSetupTemplate.id == template_id,
                ServiceSetupTemplate.deleted_at.is_(None),
            )
        )
        if not row:
            raise ValueError(f"Template {template_id} not found")
        return row

    async def create_template(self, body: dict) -> dict:
        slug = body.get("slug") or _slug(body["name"])
        row = ServiceSetupTemplate(
            code=body["code"],
            name=body["name"],
            slug=slug,
            description=body.get("description"),
            vertical_type=body.get("vertical_type"),
            category_id=body.get("category_id"),
            template_type=body.get("template_type", "starter_pack"),
            status="draft",
            version=1,
            is_system_template=body.get("is_system_template", False),
            metadata_json=body.get("metadata_json"),
            created_by_user_id=self.actor_id,
            updated_by_user_id=self.actor_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit("service_setup_template", str(row.id), "template.created", body)
        await self.db.commit()
        return row.to_dict()

    async def update_template(self, template_id: uuid.UUID, body: dict) -> dict:
        row = await self.get_template(template_id)
        for field in ("name", "description", "vertical_type", "template_type", "metadata_json"):
            if field in body:
                setattr(row, field, body[field])
        row.updated_by_user_id = self.actor_id
        await self._audit("service_setup_template", str(template_id), "template.updated", body)
        await self.db.commit()
        return row.to_dict()

    async def _set_template_status(self, template_id: uuid.UUID, status: str) -> dict:
        row = await self.get_template(template_id)
        row.status = status
        row.updated_by_user_id = self.actor_id
        await self._audit("service_setup_template", str(template_id), f"template.{status}", {})
        await self.db.commit()
        return row.to_dict()

    async def publish_template(self, template_id: uuid.UUID) -> dict:
        return await self._set_template_status(template_id, "published")

    async def archive_template(self, template_id: uuid.UUID) -> dict:
        return await self._set_template_status(template_id, "archived")

    async def delete_template(self, template_id: uuid.UUID) -> dict:
        row = await self.get_template(template_id)
        row.deleted_at = _now()
        await self._audit("service_setup_template", str(template_id), "template.deleted", {})
        await self.db.commit()
        return {"deleted": True}

    # ── Template Items ────────────────────────────────────────────────────────

    async def list_items(self, template_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.scalars(
            select(ServiceSetupTemplateItem)
            .where(
                ServiceSetupTemplateItem.template_id == template_id,
                ServiceSetupTemplateItem.deleted_at.is_(None),
            )
            .order_by(ServiceSetupTemplateItem.display_order)
        )).all()
        return [r.to_dict() for r in rows]

    async def add_item(self, template_id: uuid.UUID, body: dict) -> dict:
        await self.get_template(template_id)
        row = ServiceSetupTemplateItem(
            template_id=template_id,
            item_type=body["item_type"],
            reference_id=body.get("reference_id"),
            reference_code=body.get("reference_code"),
            payload_json=body.get("payload_json", {}),
            apply_mode=body.get("apply_mode", "create_if_missing"),
            is_required=body.get("is_required", False),
            display_order=body.get("display_order", 0),
            status="active",
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit("service_setup_template_item", str(row.id), "item.added", body)
        await self.db.commit()
        return row.to_dict()

    async def update_item(self, template_id: uuid.UUID, item_id: uuid.UUID, body: dict) -> dict:
        row = await self.db.scalar(
            select(ServiceSetupTemplateItem).where(
                ServiceSetupTemplateItem.id == item_id,
                ServiceSetupTemplateItem.template_id == template_id,
                ServiceSetupTemplateItem.deleted_at.is_(None),
            )
        )
        if not row:
            raise ValueError(f"Item {item_id} not found in template {template_id}")
        for field in ("item_type", "reference_id", "reference_code", "payload_json",
                      "apply_mode", "is_required", "display_order", "status"):
            if field in body:
                setattr(row, field, body[field])
        await self._audit("service_setup_template_item", str(item_id), "item.updated", body)
        await self.db.commit()
        return row.to_dict()

    async def remove_item(self, template_id: uuid.UUID, item_id: uuid.UUID) -> dict:
        row = await self.db.scalar(
            select(ServiceSetupTemplateItem).where(
                ServiceSetupTemplateItem.id == item_id,
                ServiceSetupTemplateItem.template_id == template_id,
                ServiceSetupTemplateItem.deleted_at.is_(None),
            )
        )
        if not row:
            raise ValueError(f"Item {item_id} not found")
        row.deleted_at = _now()
        await self._audit("service_setup_template_item", str(item_id), "item.removed", {})
        await self.db.commit()
        return {"deleted": True}

    # ── Template Relationships ────────────────────────────────────────────────

    async def list_relationships(self, template_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.scalars(
            select(ServiceSetupTemplateRelationship)
            .where(
                ServiceSetupTemplateRelationship.template_id == template_id,
                ServiceSetupTemplateRelationship.deleted_at.is_(None),
            )
            .order_by(ServiceSetupTemplateRelationship.display_order)
        )).all()
        return [r.to_dict() for r in rows]

    async def add_relationship(self, template_id: uuid.UUID, body: dict) -> dict:
        await self.get_template(template_id)
        row = ServiceSetupTemplateRelationship(
            template_id=template_id,
            source_item_id=body["source_item_id"],
            target_item_id=body["target_item_id"],
            relationship_type=body["relationship_type"],
            payload_json=body.get("payload_json"),
            display_order=body.get("display_order", 0),
            status="active",
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit("service_setup_template_relationship", str(row.id), "relationship.added", body)
        await self.db.commit()
        return row.to_dict()

    async def remove_relationship(self, template_id: uuid.UUID, rel_id: uuid.UUID) -> dict:
        row = await self.db.scalar(
            select(ServiceSetupTemplateRelationship).where(
                ServiceSetupTemplateRelationship.id == rel_id,
                ServiceSetupTemplateRelationship.template_id == template_id,
                ServiceSetupTemplateRelationship.deleted_at.is_(None),
            )
        )
        if not row:
            raise ValueError(f"Relationship {rel_id} not found")
        row.deleted_at = _now()
        await self._audit("service_setup_template_relationship", str(rel_id), "relationship.removed", {})
        await self.db.commit()
        return {"deleted": True}

    # ── Preview (no DB mutation) ──────────────────────────────────────────────

    async def preview_template(self, template_id: uuid.UUID, scope: dict) -> dict:
        template = await self.get_template(template_id)
        items = await self.list_items(template_id)
        relationships = await self.list_relationships(template_id)

        preview_items: list[dict] = []
        for item in items:
            action = self._resolve_apply_mode_action(item["apply_mode"])
            preview_items.append({
                "item_id": item["id"],
                "item_type": item["item_type"],
                "reference_code": item["reference_code"],
                "apply_mode": item["apply_mode"],
                "expected_action": action,
                "payload_json": item["payload_json"],
                "is_required": item["is_required"],
            })

        return {
            "template": template.to_dict(),
            "scope": scope,
            "preview_items": preview_items,
            "relationships": relationships,
            "total_items": len(items),
            "note": "Preview only — no database changes made",
        }

    def _resolve_apply_mode_action(self, apply_mode: str) -> str:
        mapping = {
            "create_if_missing": "CREATE",
            "map_existing": "MAP",
            "update_existing": "UPDATE",
            "skip_if_exists": "SKIP",
        }
        return mapping.get(apply_mode, "CREATE")

    # ── Apply (idempotent) ────────────────────────────────────────────────────

    async def apply_template(self, template_id: uuid.UUID, scope: dict) -> dict:
        template = await self.get_template(template_id)
        items = await self.list_items(template_id)

        run = ServiceSetupTemplateRun(
            template_id=template_id,
            version=template.version,
            applied_by_user_id=self.actor_id,
            target_scope=scope.get("target_scope", "platform"),
            target_category_id=scope.get("target_category_id"),
            target_service_id=scope.get("target_service_id"),
            target_tenant_id=scope.get("target_tenant_id"),
            status="running",
        )
        self.db.add(run)
        await self.db.flush()

        run_items: list[dict] = []
        created = updated = skipped = errors = 0

        for item in items:
            try:
                action, record_type, record_id, msg = await self._apply_item(item, scope)
                run_item = ServiceSetupTemplateRunItem(
                    run_id=run.id,
                    template_item_id=uuid.UUID(item["id"]),
                    action=action,
                    target_record_type=record_type,
                    target_record_id=uuid.UUID(record_id) if record_id else None,
                    message=msg,
                )
                self.db.add(run_item)
                run_items.append({"action": action, "item_type": item["item_type"], "message": msg})
                if action == "CREATED":
                    created += 1
                elif action == "UPDATED":
                    updated += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors += 1
                run_item = ServiceSetupTemplateRunItem(
                    run_id=run.id,
                    template_item_id=uuid.UUID(item["id"]),
                    action="ERROR",
                    target_record_type=item["item_type"],
                    message=str(exc),
                )
                self.db.add(run_item)

        summary = {"created": created, "updated": updated, "skipped": skipped, "errors": errors}
        run.status = "completed" if errors == 0 else "completed_with_errors"
        run.summary_json = summary
        run.completed_at = _now()

        await self._audit("service_setup_template", str(template_id), "template.applied", {
            "run_id": str(run.id), **summary
        })
        await self.db.commit()

        return {
            "run_id": str(run.id),
            "template_id": str(template_id),
            "status": run.status,
            "summary": summary,
            "items": run_items,
        }

    async def _apply_item(
        self, item: dict, scope: dict
    ) -> tuple[str, str, str | None, str]:
        """Returns (action, record_type, record_id, message)."""
        apply_mode = item["apply_mode"]
        item_type = item["item_type"]
        payload = item["payload_json"] or {}
        ref_code = item["reference_code"]

        if apply_mode == "skip_if_exists" and ref_code:
            return ("SKIPPED", item_type, None, f"Skipped by apply_mode=skip_if_exists (ref={ref_code})")

        if apply_mode == "create_if_missing":
            new_id = str(uuid.uuid4())
            return ("CREATED", item_type, new_id, f"Created {item_type} (ref={ref_code})")

        if apply_mode == "map_existing":
            ref_id = item.get("reference_id")
            if not ref_id:
                return ("SKIPPED", item_type, None, f"map_existing: no reference_id for {item_type}")
            return ("MAPPED", item_type, ref_id, f"Mapped existing {item_type} ({ref_id})")

        if apply_mode == "update_existing":
            ref_id = item.get("reference_id")
            if not ref_id:
                return ("SKIPPED", item_type, None, f"update_existing: no reference_id for {item_type}")
            return ("UPDATED", item_type, ref_id, f"Updated {item_type} ({ref_id})")

        return ("SKIPPED", item_type, None, f"Unknown apply_mode={apply_mode}")

    # ── Runs ──────────────────────────────────────────────────────────────────

    async def list_runs(self, template_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.scalars(
            select(ServiceSetupTemplateRun)
            .where(ServiceSetupTemplateRun.template_id == template_id)
            .order_by(ServiceSetupTemplateRun.created_at.desc())
        )).all()
        return [r.to_dict() for r in rows]

    async def get_run_detail(self, run_id: uuid.UUID) -> dict:
        run = await self.db.scalar(
            select(ServiceSetupTemplateRun).where(ServiceSetupTemplateRun.id == run_id)
        )
        if not run:
            raise ValueError(f"Run {run_id} not found")
        run_items = (await self.db.scalars(
            select(ServiceSetupTemplateRunItem)
            .where(ServiceSetupTemplateRunItem.run_id == run_id)
            .order_by(ServiceSetupTemplateRunItem.created_at)
        )).all()
        return {
            **run.to_dict(),
            "items": [ri.to_dict() for ri in run_items],
        }

    # ── Provider Recommendations ──────────────────────────────────────────────

    async def get_recommended_templates(
        self, vertical_type: str | None = None, category_id: uuid.UUID | None = None
    ) -> list[dict]:
        q = (
            select(ServiceSetupTemplate)
            .where(
                ServiceSetupTemplate.status == "published",
                ServiceSetupTemplate.deleted_at.is_(None),
            )
        )
        if vertical_type:
            q = q.where(ServiceSetupTemplate.vertical_type == vertical_type)
        if category_id:
            q = q.where(ServiceSetupTemplate.category_id == category_id)
        q = q.order_by(
            ServiceSetupTemplate.is_system_template.desc(),
            ServiceSetupTemplate.name,
        )
        rows = (await self.db.scalars(q)).all()
        return [r.to_dict() for r in rows]
