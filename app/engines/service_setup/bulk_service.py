"""Service Setup Bulk Wizard — BulkSetupService."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, delete, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.service_setup.models import (
    BulkDraft, BulkPreviewItem, BulkValidationResult, BulkRun, BulkRunItem,
)

ALLOWED_VERTICALS = [
    "home_services", "coaching_ielts", "real_estate", "beauty_wellness",
    "restaurant_food", "product_marketplace", "professional_services",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _draft_dict(d: BulkDraft) -> dict:
    return d.to_dict()


def _run_dict(r: BulkRun) -> dict:
    return r.to_dict()


class BulkSetupService:

    # ── Drafts ────────────────────────────────────────────────────────────────

    async def list_drafts(
        self, db: AsyncSession, *,
        q: str | None = None,
        vertical: str | None = None,
        status: str | None = None,
        template_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
    ) -> dict:
        stmt = select(BulkDraft)
        if q:
            stmt = stmt.where(BulkDraft.name.ilike(f"%{q}%") | BulkDraft.draft_code.ilike(f"%{q}%"))
        if vertical:
            stmt = stmt.where(BulkDraft.vertical_key == vertical)
        if status:
            stmt = stmt.where(BulkDraft.status == status)
        if template_id:
            stmt = stmt.where(BulkDraft.template_id == uuid.UUID(template_id))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        col = getattr(BulkDraft, sort_by, BulkDraft.updated_at)
        stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()
        return {"items": [_draft_dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}

    async def get_summary(self, db: AsyncSession) -> dict:
        rows = (await db.execute(
            select(BulkDraft.status, func.count().label("cnt")).group_by(BulkDraft.status)
        )).all()
        by_status = {r.status: r.cnt for r in rows}

        run_rows = (await db.execute(
            select(BulkRun.status, func.count().label("cnt")).where(BulkRun.is_dry_run == False).group_by(BulkRun.status)  # noqa
        )).all()
        run_by_status = {r.status: r.cnt for r in run_rows}

        rollback_count = (await db.execute(
            select(func.count()).where(BulkRun.rollback_available == True)  # noqa
        )).scalar() or 0

        total_drafts = sum(by_status.values())
        return {
            "total_drafts": total_drafts,
            "ready_to_run": by_status.get("ready_to_run", 0),
            "running": by_status.get("running", 0),
            "completed_runs": run_by_status.get("completed", 0),
            "failed_runs": run_by_status.get("failed", 0),
            "rollback_available": rollback_count,
        }

    async def create_draft(self, db: AsyncSession, payload: dict, user_id: str | None = None) -> dict:
        name = (payload.get("name") or "").strip()
        vertical = (payload.get("vertical_key") or "").strip()
        if not name:
            raise ValueError("name is required")
        if not vertical or vertical not in ALLOWED_VERTICALS:
            raise ValueError(f"vertical_key must be one of: {ALLOWED_VERTICALS}")

        ts = int(_now().timestamp())
        draft_code = f"bulk_{_slug(vertical)}_{ts}"
        d = BulkDraft(
            draft_code=draft_code,
            name=name,
            description=payload.get("description"),
            vertical_key=vertical,
            setup_mode=payload.get("setup_mode", "manual"),
            template_id=uuid.UUID(payload["template_id"]) if payload.get("template_id") else None,
            status="draft",
            current_step=1,
            config_json=payload.get("config_json", {}),
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(d)
        await db.commit()
        await db.refresh(d)
        return _draft_dict(d)

    async def get_draft(self, db: AsyncSession, draft_id: str) -> dict:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")
        return _draft_dict(d)

    async def update_draft(self, db: AsyncSession, draft_id: str, payload: dict) -> dict:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")
        for field in ("name", "description", "setup_mode", "status", "current_step", "config_json"):
            if field in payload:
                setattr(d, field, payload[field])
        if "vertical_key" in payload:
            v = payload["vertical_key"]
            if v not in ALLOWED_VERTICALS:
                raise ValueError(f"invalid vertical_key: {v}")
            d.vertical_key = v
        if "template_id" in payload:
            d.template_id = uuid.UUID(payload["template_id"]) if payload["template_id"] else None
        d.updated_at = _now()
        await db.commit()
        await db.refresh(d)
        return _draft_dict(d)

    async def validate_draft(self, db: AsyncSession, draft_id: str) -> dict:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")

        # Clear old results
        await db.execute(delete(BulkValidationResult).where(BulkValidationResult.draft_id == d.id))

        results: list[BulkValidationResult] = []
        config = d.config_json or {}
        modules = config.get("modules", [])
        content = config.get("content", {})

        # Check coaching + issue_types
        if d.vertical_key == "coaching_ielts" and "issue_types" in modules:
            results.append(BulkValidationResult(
                draft_id=d.id,
                severity="error",
                module_key="issue_types",
                message="Coaching vertical cannot include issue_types",
                blocking=True,
            ))

        # Check for duplicate codes within modules
        for module_key, items in content.items():
            codes = [i.get("code") or i.get("item_key") or "" for i in items if isinstance(i, dict)]
            codes = [c for c in codes if c]
            seen: set[str] = set()
            for code in codes:
                if code in seen:
                    results.append(BulkValidationResult(
                        draft_id=d.id,
                        severity="error",
                        module_key=module_key,
                        message=f"Duplicate code '{code}' in module {module_key}",
                        blocking=True,
                    ))
                seen.add(code)

        if not modules and not content:
            results.append(BulkValidationResult(
                draft_id=d.id,
                severity="warning",
                message="No modules or content configured",
                blocking=False,
            ))

        for vr in results:
            db.add(vr)

        blocking_count = sum(1 for r in results if r.blocking)
        new_status = "ready_to_run" if blocking_count == 0 else "validation_failed"
        d.status = new_status
        d.updated_at = _now()
        await db.commit()

        errors = [{"severity": r.severity, "module_key": r.module_key, "message": r.message, "blocking": r.blocking}
                  for r in results if r.severity == "error"]
        warnings = [{"severity": r.severity, "module_key": r.module_key, "message": r.message}
                    for r in results if r.severity == "warning"]
        return {"valid": blocking_count == 0, "errors": errors, "warnings": warnings, "blocking_count": blocking_count}

    async def preview_draft(self, db: AsyncSession, draft_id: str) -> dict:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")

        config = d.config_json or {}
        content = config.get("content", {})

        # Clear old preview items
        await db.execute(delete(BulkPreviewItem).where(BulkPreviewItem.draft_id == d.id))

        items: list[dict] = []
        summary: dict[str, int] = {"create": 0, "update": 0, "skip": 0, "conflict": 0}

        for module_key, module_items in content.items():
            if not isinstance(module_items, list):
                continue
            for item in module_items:
                if not isinstance(item, dict):
                    continue
                record_name = item.get("name") or item.get("item_name") or ""
                record_code = item.get("code") or item.get("item_key") or _slug(record_name)
                action = "create"
                pi = BulkPreviewItem(
                    draft_id=d.id,
                    module_key=module_key,
                    record_type=module_key,
                    record_name=record_name,
                    record_code=record_code,
                    action=action,
                    payload_json=item,
                )
                db.add(pi)
                items.append({
                    "module_key": module_key,
                    "record_type": module_key,
                    "record_name": record_name,
                    "record_code": record_code,
                    "action": action,
                })
                summary[action] = summary.get(action, 0) + 1

        await db.commit()
        return {"items": items, "summary": summary}

    async def dry_run(self, db: AsyncSession, draft_id: str, user_id: str | None = None) -> dict:
        return await self.execute_draft(db, draft_id, user_id, reason="dry_run", is_dry_run=True)

    async def execute_draft(
        self, db: AsyncSession, draft_id: str, user_id: str | None = None,
        reason: str = "", is_dry_run: bool = False,
    ) -> dict:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")

        ts = int(_now().timestamp())
        prefix = "dryrun" if is_dry_run else "run"
        run_code = f"{prefix}_{d.vertical_key}_{ts}"
        config = d.config_json or {}
        content = config.get("content", {})

        all_items: list[dict] = []
        for module_key, module_items in content.items():
            if isinstance(module_items, list):
                for item in module_items:
                    if isinstance(item, dict):
                        all_items.append({"module_key": module_key, "item": item})

        run = BulkRun(
            run_code=run_code,
            draft_id=d.id,
            vertical_key=d.vertical_key,
            template_id=d.template_id,
            status="running" if not is_dry_run else "queued",
            is_dry_run=is_dry_run,
            total_items=len(all_items),
            execution_reason=reason,
            started_by_user_id=uuid.UUID(user_id) if user_id else None,
            started_at=_now(),
        )
        db.add(run)
        await db.flush()

        if is_dry_run:
            run.status = "completed"
            run.created_count = len(all_items)
            run.completed_at = _now()
            run.rollback_available = False
        else:
            created = 0
            skipped = 0
            failed = 0
            run_items: list[BulkRunItem] = []

            for entry in all_items:
                module_key = entry["module_key"]
                item = entry["item"]
                record_name = item.get("name") or item.get("item_name") or ""
                record_code = item.get("code") or item.get("item_key") or _slug(record_name)

                item_status = "created"
                target_id: uuid.UUID | None = None
                error_msg: str | None = None

                try:
                    if module_key == "service_groups":
                        # Try insert into service_groups if table exists
                        existing = (await db.execute(
                            sa_text("SELECT id FROM service_groups WHERE code = :code LIMIT 1"),
                            {"code": record_code},
                        )).fetchone()
                        if existing:
                            item_status = "skipped"
                            target_id = existing[0]
                            skipped += 1
                        else:
                            new_id = uuid.uuid4()
                            await db.execute(
                                sa_text(
                                    "INSERT INTO service_groups (id, code, name, vertical_key, is_active, created_at, updated_at) "
                                    "VALUES (:id, :code, :name, :vk, true, now(), now()) ON CONFLICT (code) DO NOTHING"
                                ),
                                {"id": new_id, "code": record_code, "name": record_name, "vk": d.vertical_key},
                            )
                            target_id = new_id
                            created += 1
                    elif module_key == "master_services":
                        existing = (await db.execute(
                            sa_text("SELECT id FROM master_services WHERE code = :code LIMIT 1"),
                            {"code": record_code},
                        )).fetchone()
                        if existing:
                            item_status = "skipped"
                            target_id = existing[0]
                            skipped += 1
                        else:
                            new_id = uuid.uuid4()
                            await db.execute(
                                sa_text(
                                    "INSERT INTO master_services (id, code, name, vertical_key, is_active, created_at, updated_at) "
                                    "VALUES (:id, :code, :name, :vk, true, now(), now()) ON CONFLICT (code) DO NOTHING"
                                ),
                                {"id": new_id, "code": record_code, "name": record_name, "vk": d.vertical_key},
                            )
                            target_id = new_id
                            created += 1
                    else:
                        # Generic — mark as created (placeholder for future modules)
                        created += 1
                except Exception as exc:
                    item_status = "failed"
                    error_msg = str(exc)
                    failed += 1

                run_items.append(BulkRunItem(
                    run_id=run.id,
                    module_key=module_key,
                    record_type=module_key,
                    record_name=record_name,
                    record_code=record_code,
                    action="create",
                    status=item_status,
                    target_record_id=target_id,
                    error_message=error_msg,
                ))

            for ri in run_items:
                db.add(ri)

            run.created_count = created
            run.skipped_count = skipped
            run.failed_count = failed
            run.status = "completed" if failed == 0 else "partially_completed"
            run.completed_at = _now()
            run.rollback_available = created > 0

            d.status = "completed"
            d.updated_at = _now()

        await db.commit()
        await db.refresh(run)
        return _run_dict(run)

    async def clone_draft(self, db: AsyncSession, draft_id: str, user_id: str | None = None) -> dict:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")
        ts = int(_now().timestamp())
        new_draft = BulkDraft(
            draft_code=f"bulk_{_slug(d.vertical_key)}_{ts}_clone",
            name=f"{d.name} (Clone)",
            description=d.description,
            vertical_key=d.vertical_key,
            setup_mode=d.setup_mode,
            template_id=d.template_id,
            status="draft",
            current_step=1,
            config_json=d.config_json or {},
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(new_draft)
        await db.commit()
        await db.refresh(new_draft)
        return _draft_dict(new_draft)

    async def delete_draft(self, db: AsyncSession, draft_id: str) -> None:
        d = await db.get(BulkDraft, uuid.UUID(draft_id))
        if not d:
            raise ValueError(f"Draft {draft_id} not found")
        if d.status not in ("draft", "validation_failed"):
            raise ValueError(f"Cannot delete draft with status '{d.status}'")
        await db.delete(d)
        await db.commit()

    # ── Runs ──────────────────────────────────────────────────────────────────

    async def list_runs(
        self, db: AsyncSession, *,
        draft_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        stmt = select(BulkRun)
        if draft_id:
            stmt = stmt.where(BulkRun.draft_id == uuid.UUID(draft_id))
        stmt = stmt.order_by(BulkRun.created_at.desc())
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()
        return {"items": [_run_dict(r) for r in rows], "total": total}

    async def get_run(self, db: AsyncSession, run_id: str) -> dict:
        r = await db.get(BulkRun, uuid.UUID(run_id))
        if not r:
            raise ValueError(f"Run {run_id} not found")
        return _run_dict(r)

    async def get_run_logs(self, db: AsyncSession, run_id: str) -> dict:
        r = await db.get(BulkRun, uuid.UUID(run_id))
        if not r:
            raise ValueError(f"Run {run_id} not found")
        items = (await db.execute(
            select(BulkRunItem).where(BulkRunItem.run_id == r.id).order_by(BulkRunItem.created_at)
        )).scalars().all()
        return {"items": [i.to_dict() for i in items]}

    async def rollback_run(self, db: AsyncSession, run_id: str, user_id: str | None = None, reason: str = "") -> dict:
        r = await db.get(BulkRun, uuid.UUID(run_id))
        if not r:
            raise ValueError(f"Run {run_id} not found")
        if not r.rollback_available:
            raise ValueError("Rollback not available for this run")
        r.status = "rolled_back"
        r.rollback_available = False
        await db.commit()
        await db.refresh(r)
        return _run_dict(r)
