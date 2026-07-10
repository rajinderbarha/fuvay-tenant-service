"""Notification Template Center — enterprise admin router (migration 102).

Distinct from the basic `router.py` (which stays untouched for the existing
NotificationService.send() runtime path) — this router adds the full
create/edit/validate/preview/test-send/override/version/analytics/audit
surface for admin template management under /v1/admin/notifications/templates.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.engines.notification.service import NotificationService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/notifications/templates", tags=["admin-notification-templates"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession, r: Request, u) -> NotificationService:
    return NotificationService(db, _rid(r), uuid.UUID(u.user_id) if u.user_id else None, u.role)


# ── Summary + List (static routes before /{template_id}) ────────────────────

@router.get("/summary")
async def get_summary(
    r: Request, db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.NOTIF_TEMPLATES_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).get_summary(), _rid(r))


@router.get("")
async def list_templates(
    r: Request,
    channel: Optional[str] = Query(None), event_type: Optional[str] = Query(None),
    audience: Optional[str] = Query(None), app_scope: Optional[str] = Query(None),
    scope_type: Optional[str] = Query(None), vertical_key: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None), language: Optional[str] = Query(None),
    status: Optional[str] = Query(None), search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.NOTIF_TEMPLATES_READ)),
) -> ApiResponse[dict]:
    svc = _svc(db, r, u)
    return ok(await svc.list_templates_admin({
        "channel": channel, "event_type": event_type, "audience": audience, "app_scope": app_scope,
        "scope_type": scope_type, "vertical_key": vertical_key,
        "tenant_id": uuid.UUID(tenant_id) if tenant_id else None,
        "language": language, "status": status, "search": search,
    }), _rid(r))


@router.post("")
async def create_template(
    r: Request, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_CREATE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).create_template_admin(body), _rid(r))


@router.post("/seed-defaults/preview")
async def seed_defaults_preview(
    r: Request, db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.NOTIF_TEMPLATES_SEED_DEFAULTS)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).seed_defaults_preview(), _rid(r))


@router.post("/seed-defaults")
async def seed_defaults(
    r: Request, db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.NOTIF_TEMPLATES_SEED_DEFAULTS)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).seed_defaults(), _rid(r))


@router.post("/resolve-effective-template")
async def resolve_effective_template(
    r: Request, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_READ)),
) -> ApiResponse[dict]:
    svc = _svc(db, r, u)
    return ok(await svc.resolve_effective_template(
        body["event_type"], body["channel"], body["audience"],
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body.get("vertical_key")), _rid(r))


@router.get("/audit-logs")
async def list_all_audit_logs(
    r: Request, db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.NOTIF_TEMPLATES_AUDIT_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).list_audit_logs(), _rid(r))


# ── Template detail + actions ────────────────────────────────────────────────

@router.get("/{template_id}")
async def get_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_READ)),
) -> ApiResponse[dict]:
    svc = _svc(db, r, u)
    t = await svc._get_template(template_id)
    return ok(t.to_admin_dict(), _rid(r))


@router.put("/{template_id}")
async def update_template(
    r: Request, template_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_UPDATE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).update_template_admin(template_id, body, body.get("reason")), _rid(r))


@router.post("/{template_id}/activate")
async def activate_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_ACTIVATE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).activate_template(template_id), _rid(r))


@router.post("/{template_id}/deactivate")
async def deactivate_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_ACTIVATE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).deactivate_template(template_id), _rid(r))


@router.post("/{template_id}/archive")
async def archive_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_ARCHIVE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).archive_template(template_id), _rid(r))


@router.delete("/{template_id}")
async def delete_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_DELETE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).delete_template_admin(template_id), _rid(r))


@router.post("/{template_id}/clone")
async def clone_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_CLONE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).clone_template(template_id), _rid(r))


@router.post("/{template_id}/create-override")
async def create_override(
    r: Request, template_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_OVERRIDE)),
) -> ApiResponse[dict]:
    svc = _svc(db, r, u)
    return ok(await svc.create_override(
        template_id, body["scope_type"],
        uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        body.get("vertical_key")), _rid(r))


# ── Validate / Preview / Test Send ──────────────────────────────────────────

@router.post("/{template_id}/validate")
async def validate_template(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_PREVIEW)),
) -> ApiResponse[dict]:
    svc = _svc(db, r, u)
    t = await svc._get_template(template_id)
    return ok(svc.validate_variables(t.event_type, t.audience, t.title, t.body, t.subject, t.html_body), _rid(r))


@router.post("/{template_id}/render-preview")
async def render_preview(
    r: Request, template_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_PREVIEW)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).render_preview(template_id, body.get("sample_data", {})), _rid(r))


@router.post("/{template_id}/test-send")
async def test_send(
    r: Request, template_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_TEST_SEND)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).test_send(template_id, body["recipient"], body.get("sample_data", {})), _rid(r))


# ── Versions ──────────────────────────────────────────────────────────────

@router.get("/{template_id}/versions")
async def list_versions(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).list_versions(template_id), _rid(r))


@router.post("/{template_id}/rollback")
async def rollback_template(
    r: Request, template_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_VERSION_ROLLBACK)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).rollback_template(template_id, body["version_number"], body.get("reason", "")), _rid(r))


# ── Delivery Analytics + Audit ───────────────────────────────────────────────

@router.get("/{template_id}/delivery-analytics")
async def delivery_analytics(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_ANALYTICS_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).delivery_analytics(template_id), _rid(r))


@router.get("/{template_id}/audit-logs")
async def template_audit_logs(
    r: Request, template_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.NOTIF_TEMPLATES_AUDIT_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, r, u).list_audit_logs(template_id), _rid(r))
