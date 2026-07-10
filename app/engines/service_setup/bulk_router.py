"""Service Setup Bulk Wizard — Admin Router."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.schemas.base import ok, ApiResponse
from app.engines.service_setup.bulk_service import BulkSetupService

router = APIRouter(prefix="/v1/admin/service-setup/bulk-wizard", tags=["admin-bulk-wizard"])

_svc = BulkSetupService()


def _rid() -> str:
    return str(uuid.uuid4())


# ── Summary (MUST be before /{draft_id}) ──────────────────────────────────────

@router.get("/summary", response_model=ApiResponse)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    data = await _svc.get_summary(db)
    return ok(data, _rid())


# ── Drafts list ───────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse)
async def list_drafts(
    q: Optional[str] = Query(None),
    vertical: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    template_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    data = await _svc.list_drafts(
        db, q=q, vertical=vertical, status=status, template_id=template_id,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
    )
    return ok(data, _rid())


# ── Create draft ─────────────────────────────────────────────────────────────

@router.post("/drafts", response_model=ApiResponse)
async def create_draft(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.BULK_WIZARD_WRITE)),
):
    try:
        data = await _svc.create_draft(db, payload, user_id=str(user.user_id) if user else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


# ── Get / update / delete draft ───────────────────────────────────────────────

@router.get("/drafts/{draft_id}", response_model=ApiResponse)
async def get_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    try:
        data = await _svc.get_draft(db, draft_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.put("/drafts/{draft_id}", response_model=ApiResponse)
async def update_draft(
    draft_id: str,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_WRITE)),
):
    try:
        data = await _svc.update_draft(db, draft_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


@router.delete("/drafts/{draft_id}", response_model=ApiResponse)
async def delete_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_WRITE)),
):
    try:
        await _svc.delete_draft(db, draft_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok({"deleted": True}, _rid())


# ── Draft actions ─────────────────────────────────────────────────────────────

@router.post("/drafts/{draft_id}/validate", response_model=ApiResponse)
async def validate_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_WRITE)),
):
    try:
        data = await _svc.validate_draft(db, draft_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.post("/drafts/{draft_id}/preview", response_model=ApiResponse)
async def preview_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    try:
        data = await _svc.preview_draft(db, draft_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.post("/drafts/{draft_id}/dry-run", response_model=ApiResponse)
async def dry_run(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.BULK_WIZARD_EXECUTE)),
):
    try:
        data = await _svc.dry_run(db, draft_id, user_id=str(user.user_id) if user else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


@router.post("/drafts/{draft_id}/execute", response_model=ApiResponse)
async def execute_draft(
    draft_id: str,
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.BULK_WIZARD_EXECUTE)),
):
    reason = payload.get("reason", "")
    try:
        data = await _svc.execute_draft(db, draft_id, user_id=str(user.user_id) if user else None, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


@router.post("/drafts/{draft_id}/clone", response_model=ApiResponse)
async def clone_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.BULK_WIZARD_WRITE)),
):
    try:
        data = await _svc.clone_draft(db, draft_id, user_id=str(user.user_id) if user else None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


# ── Runs ─────────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=ApiResponse)
async def list_runs(
    draft_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    data = await _svc.list_runs(db, draft_id=draft_id, page=page, page_size=page_size)
    return ok(data, _rid())


@router.get("/runs/{run_id}", response_model=ApiResponse)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    try:
        data = await _svc.get_run(db, run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.post("/runs/{run_id}/rollback", response_model=ApiResponse)
async def rollback_run(
    run_id: str,
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.BULK_WIZARD_EXECUTE)),
):
    reason = payload.get("reason", "")
    try:
        data = await _svc.rollback_run(db, run_id, user_id=str(user.user_id) if user else None, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


@router.get("/runs/{run_id}/logs", response_model=ApiResponse)
async def get_run_logs(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.BULK_WIZARD_READ)),
):
    try:
        data = await _svc.get_run_logs(db, run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())
