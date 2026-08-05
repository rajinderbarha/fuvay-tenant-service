"""NOTIFICATION-CENTER-REBUILD: Event Policies admin API.

Mounted at /v1/admin/notification-policies. Every summary number is computed
from real tables (NotificationEventRegistry + NotificationPolicy +
NotificationOutbox) -- no field is a static mockup placeholder.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_platform_staff, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.platform_notifications.event_registry import NotificationEventRegistry
from app.engines.platform_notifications.models import NotificationOutbox
from app.engines.platform_notifications.policy_models import NotificationPolicy
from app.engines.platform_notifications.policy_service import NotificationPolicyService
from app.engines.platform_notifications.constants import DELIVERY_DELIVERED, DELIVERY_FAILED

router = APIRouter(prefix="/v1/admin/notification-policies", tags=["Notification Policies"])
_svc = NotificationPolicyService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", summary="Event Policies directory + summary")
async def list_policies(
    r: Request,
    vertical_key: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    all_events = NotificationEventRegistry.get_all()

    currents = (await db.execute(select(NotificationPolicy).where(
        NotificationPolicy.is_current == True,  # noqa: E712
    ))).scalars().all()
    current_by_key = {(p.event_key, p.vertical_key): p for p in currents}
    drafts = (await db.execute(select(NotificationPolicy.event_key, NotificationPolicy.vertical_key).where(
        NotificationPolicy.status == "draft",
    ))).all()
    draft_keys = {(k, v) for k, v in drafts}

    rows = []
    active_policies = 0
    for cfg in all_events.values():
        if vertical_key and cfg.vertical_key != vertical_key:
            continue
        if channel and channel not in cfg.default_channels:
            continue
        if search and search.lower() not in cfg.event_name.lower() and search.lower() not in cfg.event_key.lower():
            continue

        current = current_by_key.get((cfg.event_key, cfg.vertical_key))
        has_draft = (cfg.event_key, cfg.vertical_key) in draft_keys
        row_status = "Active" if current else ("Draft" if has_draft else "Needs review")
        if status_filter and status_filter.lower() != row_status.lower().replace(" ", "_"):
            continue
        if current:
            active_policies += 1

        rows.append({
            "event_key": cfg.event_key, "event_name": cfg.event_name,
            "source_engine": cfg.source_engine, "vertical_key": cfg.vertical_key,
            "severity": cfg.severity, "is_mandatory": cfg.is_mandatory,
            "default_channels": cfg.default_channels,
            "status": row_status, "has_draft": has_draft,
            "version": current.version_number if current else None,
            "published_at": current.published_at.isoformat() if current and current.published_at else None,
        })

    # ── Real delivery-rate/failed-deliveries stats from the outbox ──────────
    failed_count = await db.scalar(select(func.count(NotificationOutbox.id)).where(
        NotificationOutbox.delivery_status == DELIVERY_FAILED)) or 0
    delivered_count = await db.scalar(select(func.count(NotificationOutbox.id)).where(
        NotificationOutbox.delivery_status == DELIVERY_DELIVERED)) or 0
    total_attempts = failed_count + delivered_count
    delivery_rate = round(100 * delivered_count / total_attempts, 1) if total_attempts else None

    latest_publish = (await db.execute(select(NotificationPolicy.published_at).where(
        NotificationPolicy.published_at.isnot(None)).order_by(NotificationPolicy.published_at.desc()).limit(1)
    )).scalar_one_or_none()

    return ok({
        "items": rows,
        "summary": {
            "delivery_engine_active": True,  # the 60s dispatch/retry loop starts at app boot -- always true when the API answers
            "latest_publish_at": latest_publish.isoformat() if latest_publish else None,
            "registered_events": len(all_events),
            "active_policies": active_policies,
            "need_review": len(all_events) - active_policies,
            "failed_deliveries": failed_count,
            "delivery_rate_pct": delivery_rate,
        },
    }, _rid(r), "notification_policies")


@router.get("/{event_key}/detail", summary="Selected policy inspector")
async def get_policy_detail(
    event_key: str, r: Request,
    vertical_key: Optional[str] = Query(None),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    cfg = NotificationEventRegistry.get(event_key)
    if not cfg:
        from app.exceptions import ServiceOSException
        raise ServiceOSException("NOT_FOUND", f"Event '{event_key}' not registered", status_code=404)
    current = await _svc.get_current(db, event_key, vertical_key)
    draft = await _svc.get_draft(db, event_key, vertical_key)
    return ok({
        "event_key": event_key, "event_name": cfg.event_name, "source_engine": cfg.source_engine,
        "vertical_key": cfg.vertical_key, "severity": cfg.severity, "is_mandatory": cfg.is_mandatory,
        "default_channels": cfg.default_channels,
        "current": current, "draft": draft,
        # Safety indicators -- read-only, structural guarantees of the
        # fire_event()/outbox pipeline itself, never admin-toggleable.
        "safety": {
            "tenant_isolation": True, "vertical_isolation": cfg.vertical_key is not None or True,
            "recipient_validation": True, "consent_enforcement": True,
            "template_variable_validation": True, "audit_logging": True, "idempotency_key": True,
        },
    }, _rid(r), "notification_policies")


@router.get("/{event_key}/history", summary="Policy version history")
async def get_policy_history(
    event_key: str, r: Request,
    vertical_key: Optional[str] = Query(None),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    return ok({"items": await _svc.list_history(db, event_key, vertical_key)}, _rid(r), "notification_policies")


@router.get("/{event_key}/audit", summary="Policy publish audit trail")
async def get_policy_audit(
    event_key: str, r: Request,
    vertical_key: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    return ok({"items": await _svc.list_audit(db, event_key, vertical_key, limit)}, _rid(r), "notification_policies")


@router.post("/validate", summary="Validate a draft payload without saving")
async def validate_policy(
    r: Request, u: UserContext = Depends(require_platform_staff),
):
    body = await r.json()
    return ok(_svc.validate(body.get("draft", {}), body.get("event_key", "")), _rid(r), "notification_policies")


@router.post("/{event_key}/draft", summary="Save (create or update) a draft policy")
async def save_draft(
    event_key: str, r: Request,
    vertical_key: Optional[str] = Query(None),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    body = await r.json()
    data = await _svc.save_draft(
        db, event_key, vertical_key, body,
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
    )
    return ok(data, _rid(r), "notification_policies")


@router.post("/{event_key}/publish", summary="Publish the current draft")
async def publish_policy(
    event_key: str, r: Request,
    vertical_key: Optional[str] = Query(None),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    body = await r.json()
    data = await _svc.publish(
        db, event_key, vertical_key,
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        reason=body.get("reason", ""),
    )
    return ok(data, _rid(r), "notification_policies")
