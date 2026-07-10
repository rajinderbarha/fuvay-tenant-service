"""Sprint 34H — Admin Bulk Setup Wizard router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.db import get_db
from app.dependencies.auth import UserContext, require_super_admin
from app.engines.admin_catalog.bulk_setup_service import (
    AdminBulkSetupDraftService,
    AdminBulkSetupValidationService,
    AdminBulkSetupPreviewService,
    AdminBulkSetupApplyService,
)
from app.engines.admin_catalog.models import AdminBulkSetupDraft

router = APIRouter(prefix="/v1/admin/bulk-setup", tags=["Admin Bulk Setup Wizard"])


def _draft_svc(r: Request, db: AsyncSession, u: UserContext) -> AdminBulkSetupDraftService:
    return AdminBulkSetupDraftService(
        db=db,
        actor_id=uuid.UUID(u.user_id) if u.user_id else uuid.uuid4(),
        actor_role=u.role,
        request_id=getattr(r.state, "request_id", str(uuid.uuid4())),
    )


def _apply_svc(r: Request, db: AsyncSession, u: UserContext) -> AdminBulkSetupApplyService:
    return AdminBulkSetupApplyService(
        db=db,
        actor_id=uuid.UUID(u.user_id) if u.user_id else uuid.uuid4(),
        actor_role=u.role,
        request_id=getattr(r.state, "request_id", str(uuid.uuid4())),
    )


async def _get_draft(draft_id: uuid.UUID, db: AsyncSession) -> AdminBulkSetupDraft:
    draft = await db.scalar(select(AdminBulkSetupDraft).where(
        AdminBulkSetupDraft.id == draft_id,
        AdminBulkSetupDraft.deleted_at.is_(None),
    ))
    if not draft:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
    return draft


# ── Draft CRUD ────────────────────────────────────────────────────────────────

@router.post("/drafts")
async def create_draft(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).create_draft(body)


@router.get("/drafts")
async def list_drafts(
    r: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).list_drafts(status=status, page=page, page_size=page_size)


@router.get("/drafts/{draft_id}")
async def get_draft(
    r: Request,
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    draft = await _get_draft(draft_id, db)
    return draft.to_dict()


@router.put("/drafts/{draft_id}")
async def update_draft(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).update_draft(draft_id, body)


@router.delete("/drafts/{draft_id}")
async def delete_draft(
    r: Request,
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).delete_draft(draft_id)


# ── Available-* Queries ───────────────────────────────────────────────────────

@router.get("/available-categories")
async def get_available_categories(
    r: Request,
    vertical_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_categories(vertical_type=vertical_type)


@router.get("/available-services")
async def get_available_services(
    r: Request,
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_services(category_id=category_id)


@router.get("/available-templates")
async def get_available_templates(
    r: Request,
    vertical_type: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_templates(
        vertical_type=vertical_type, category_id=category_id
    )


@router.get("/available-brands")
async def get_available_brands(
    r: Request,
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_brands(category_id=category_id)


@router.get("/available-brand-templates")
async def get_available_brand_templates(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_brand_templates()


@router.get("/available-option-groups")
async def get_available_option_groups(
    r: Request,
    vertical_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_option_groups(vertical_type=vertical_type)


@router.get("/available-service-options")
async def get_available_service_options(
    r: Request,
    group_id: uuid.UUID | None = Query(None),
    vertical_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_service_options(
        group_id=group_id, vertical_type=vertical_type
    )


@router.get("/available-issue-types")
async def get_available_issue_types(
    r: Request,
    vertical_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_issue_types(vertical_type=vertical_type)


@router.get("/available-document-requirements")
async def get_available_document_requirements(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_document_requirements()


@router.get("/available-checklist-templates")
async def get_available_checklist_templates(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_checklist_templates()


@router.get("/available-pricing-templates")
async def get_available_pricing_templates(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_pricing_templates()


@router.get("/available-commission-templates")
async def get_available_commission_templates(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_commission_templates()


@router.get("/available-workflow-templates")
async def get_available_workflow_templates(
    r: Request,
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).get_available_workflow_templates(category_id=category_id)


# ── Wizard Step Saves ─────────────────────────────────────────────────────────

@router.post("/drafts/{draft_id}/category")
async def set_category(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_category(draft_id, body)


@router.post("/drafts/{draft_id}/services")
async def set_services(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_services(draft_id, body)


@router.post("/drafts/{draft_id}/templates")
async def set_templates(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_templates(draft_id, body)


@router.post("/drafts/{draft_id}/brand-mappings")
async def set_brand_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_brand_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/option-mappings")
async def set_option_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_option_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/issue-mappings")
async def set_issue_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_issue_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/document-mappings")
async def set_document_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_document_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/checklist-mappings")
async def set_checklist_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_checklist_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/pricing-mappings")
async def set_pricing_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_pricing_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/commission-mappings")
async def set_commission_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_commission_mappings(draft_id, body)


@router.post("/drafts/{draft_id}/workflow-mappings")
async def set_workflow_mappings(
    r: Request,
    draft_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _draft_svc(r, db, u).set_workflow_mappings(draft_id, body)


# ── Validate + Preview + Apply ────────────────────────────────────────────────

@router.post("/drafts/{draft_id}/validate")
async def validate_draft(
    r: Request,
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    draft = await _get_draft(draft_id, db)
    svc = AdminBulkSetupValidationService(db)
    return await svc.get_blocking_items(draft_id)


@router.post("/drafts/{draft_id}/preview")
async def preview_draft(
    r: Request,
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    from datetime import datetime, timezone
    draft = await _get_draft(draft_id, db)

    # Run validation
    val_svc = AdminBulkSetupValidationService(db)
    blockers = await val_svc.validate_draft(draft)
    p0_count = len([b for b in blockers if b.get("severity") == "P0"])

    # Run preview
    preview_svc = AdminBulkSetupPreviewService(db)
    result = await preview_svc.preview(draft)
    result["summary"]["blockers"] = p0_count

    # Persist preview summary to draft
    draft.preview_summary_json = result["summary"]
    draft.blocking_items_json = blockers
    draft.last_previewed_at = datetime.now(timezone.utc)
    if not blockers:
        draft.status = "previewed"
    await db.commit()

    return {
        "draft_id": str(draft_id),
        "can_apply": p0_count == 0,
        "summary": result["summary"],
        "items": result["items"],
        "blockers": blockers,
    }


@router.get("/drafts/{draft_id}/review")
async def review_draft(
    r: Request,
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    draft = await _get_draft(draft_id, db)
    return {
        "draft": draft.to_dict(),
        "preview_summary": draft.preview_summary_json,
        "blocking_items": draft.blocking_items_json or [],
        "can_apply": not any(
            b.get("severity") == "P0" for b in (draft.blocking_items_json or [])
        ),
        "last_previewed_at": draft.last_previewed_at.isoformat() if draft.last_previewed_at else None,
    }


@router.post("/drafts/{draft_id}/apply")
async def apply_draft(
    r: Request,
    draft_id: uuid.UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    from fastapi import HTTPException
    draft = await _get_draft(draft_id, db)

    # Block apply if P0 blockers exist
    if draft.blocking_items_json:
        p0 = [b for b in draft.blocking_items_json if b.get("severity") == "P0"]
        if p0:
            raise HTTPException(status_code=422, detail={
                "error": "APPLY_BLOCKED_BY_P0_ERRORS",
                "message": f"{len(p0)} blocking error(s) must be resolved before applying.",
                "blockers": p0,
            })

    svc = _apply_svc(r, db, u)
    return await svc.apply(draft)


# ── Run History ───────────────────────────────────────────────────────────────

@router.get("/runs")
async def list_runs(
    r: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _apply_svc(r, db, u)
    return await svc.list_runs(page=page, page_size=page_size)


@router.get("/runs/{run_id}")
async def get_run(
    r: Request,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    svc = _apply_svc(r, db, u)
    return await svc.get_run_detail(run_id)
