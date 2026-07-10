"""Workflow Templates Enterprise Router — migration 106.

Prefix: /v1/admin/workflows/templates
Static paths MUST be before parameterized paths.
"""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import require_super_admin
from app.schemas.base import ok, ApiResponse
from app.engines.workflows.workflow_service import WorkflowTemplateService

logger = structlog.get_logger("workflows.router")
router = APIRouter(prefix="/v1/admin/workflows/templates", tags=["Workflow Templates Enterprise"])
_svc = WorkflowTemplateService()


def _rid(r: Request) -> str:
    return r.headers.get("x-request-id", "")


def _uid(r: Request) -> str | None:
    user = getattr(r.state, "user", None)
    if user:
        return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "")
    return None


# ── Static paths first ────────────────────────────────────────────────────────

@router.get("/summary", response_model=ApiResponse[dict])
async def get_summary(r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_summary(db), _rid(r))


@router.post("/seed-defaults/preview", response_model=ApiResponse[list])
async def seed_defaults_preview(r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.seed_defaults_preview(db), _rid(r))


@router.post("/seed-defaults", response_model=ApiResponse[dict])
async def seed_defaults(r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.seed_defaults(db, _uid(r)), _rid(r))


@router.get("", response_model=ApiResponse[dict])
async def list_templates(
    r: Request,
    q: str | None = None,
    vertical: str | None = None,
    workflow_type: str | None = None,
    status: str | None = None,
    readiness: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    return ok(await _svc.list_templates(db, q, vertical, workflow_type, status, readiness, page, page_size), _rid(r))


@router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_template(r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.create_template(db, payload, _uid(r)), _rid(r))


# ── Parameterized paths ───────────────────────────────────────────────────────

@router.get("/{wid}", response_model=ApiResponse[dict])
async def get_template(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_template(db, wid), _rid(r))


@router.put("/{wid}", response_model=ApiResponse[dict])
async def update_template(wid: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.update_template(db, wid, payload, _uid(r)), _rid(r))


@router.post("/{wid}/clone", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def clone_template(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.clone_template(db, wid, _uid(r)), _rid(r))


@router.post("/{wid}/archive", response_model=ApiResponse[dict])
async def archive_template(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.archive_template(db, wid, _uid(r)), _rid(r))


# Steps
@router.post("/{wid}/steps", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def add_step(wid: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.add_step(db, wid, payload, _uid(r)), _rid(r))


@router.put("/{wid}/steps/{step_id}", response_model=ApiResponse[dict])
async def update_step(wid: str, step_id: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.update_step(db, wid, step_id, payload, _uid(r)), _rid(r))


@router.delete("/{wid}/steps/{step_id}", response_model=ApiResponse[dict])
async def delete_step(wid: str, step_id: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    await _svc.delete_step(db, wid, step_id, _uid(r))
    return ok({"deleted": True}, _rid(r))


# Transitions
@router.post("/{wid}/transitions", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def add_transition(wid: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.add_transition(db, wid, payload, _uid(r)), _rid(r))


@router.put("/{wid}/transitions/{trans_id}", response_model=ApiResponse[dict])
async def update_transition(wid: str, trans_id: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.update_transition(db, wid, trans_id, payload, _uid(r)), _rid(r))


@router.delete("/{wid}/transitions/{trans_id}", response_model=ApiResponse[dict])
async def delete_transition(wid: str, trans_id: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    await _svc.delete_transition(db, wid, trans_id, _uid(r))
    return ok({"deleted": True}, _rid(r))


# SLA
@router.get("/{wid}/sla", response_model=ApiResponse[list])
async def get_sla(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_sla(db, wid), _rid(r))


@router.put("/{wid}/sla", response_model=ApiResponse[list])
async def update_sla(wid: str, r: Request, payload: list, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.update_sla(db, wid, payload, _uid(r)), _rid(r))


# Approvals
@router.get("/{wid}/approvals", response_model=ApiResponse[list])
async def get_approvals(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_approvals(db, wid), _rid(r))


@router.put("/{wid}/approvals", response_model=ApiResponse[list])
async def update_approvals(wid: str, r: Request, payload: list, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.update_approvals(db, wid, payload, _uid(r)), _rid(r))


# Automation
@router.get("/{wid}/automation", response_model=ApiResponse[list])
async def get_automation(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_automation(db, wid), _rid(r))


@router.put("/{wid}/automation", response_model=ApiResponse[list])
async def update_automation(wid: str, r: Request, payload: list, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.update_automation(db, wid, payload, _uid(r)), _rid(r))


# Service Mapping
@router.get("/{wid}/service-mapping", response_model=ApiResponse[list])
async def get_service_mapping(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_service_mapping(db, wid), _rid(r))


@router.post("/{wid}/service-mapping", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def add_service_mapping(wid: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.add_service_mapping(db, wid, payload, _uid(r)), _rid(r))


@router.delete("/{wid}/service-mapping/{mapping_id}", response_model=ApiResponse[dict])
async def delete_service_mapping(wid: str, mapping_id: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    await _svc.delete_service_mapping(db, wid, mapping_id, _uid(r))
    return ok({"deleted": True}, _rid(r))


# Validate / Simulate / Publish / Rollback
@router.post("/{wid}/validate", response_model=ApiResponse[dict])
async def validate_template(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.validate_template(db, wid, _uid(r)), _rid(r))


@router.post("/{wid}/simulate", response_model=ApiResponse[dict])
async def simulate_template(wid: str, r: Request, payload: dict[str, Any] = {}, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    scenario = payload.get("scenario", "normal_completion")
    role = payload.get("role", "system")
    start_step = payload.get("start_step")
    return ok(await _svc.simulate_template(db, wid, scenario, role, start_step, _uid(r)), _rid(r))


@router.post("/{wid}/publish", response_model=ApiResponse[dict])
async def publish_template(wid: str, r: Request, payload: dict[str, Any] = {}, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.publish_template(db, wid, payload.get("reason"), _uid(r)), _rid(r))


@router.post("/{wid}/rollback", response_model=ApiResponse[dict])
async def rollback_template(wid: str, r: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.rollback_template(db, wid, payload["version_number"], payload.get("reason"), _uid(r)), _rid(r))


# Versions / Analytics / Audit
@router.get("/{wid}/versions", response_model=ApiResponse[list])
async def get_versions(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_versions(db, wid), _rid(r))


@router.get("/{wid}/runtime-analytics", response_model=ApiResponse[dict])
async def get_runtime_analytics(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_runtime_analytics(db, wid), _rid(r))


@router.get("/{wid}/runtime-jobs", response_model=ApiResponse[dict])
async def get_runtime_jobs(wid: str, r: Request, page: int = 1, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_runtime_jobs(db, wid, page), _rid(r))


@router.get("/{wid}/audit-logs", response_model=ApiResponse[list])
async def get_audit_logs(wid: str, r: Request, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    return ok(await _svc.get_audit_logs(db, wid), _rid(r))
