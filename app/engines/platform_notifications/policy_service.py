"""NOTIFICATION-CENTER-REBUILD: Event Policies draft/validate/publish/history.

Same controlled workflow as VerticalMonetizationPolicyService: Edit Draft ->
Validate -> Review -> Publish. A published version is immutable -- editing
always creates a new draft version, never mutates a published row in place.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.event_registry import NotificationEventRegistry
from app.engines.platform_notifications.constants import ALL_CHANNELS, CHANNEL_IN_APP
from app.engines.platform_notifications.channel_providers import CHANNEL_PROVIDERS
from app.engines.platform_notifications.provider_status_service import _LIVE_CHANNELS
from app.engines.platform_notifications.policy_models import (
    NotificationPolicy, NotificationPolicyRecipientRule, NotificationPolicyAuditLog,
    DELIVERY_MODES, RECIPIENT_ROLES,
)
from app.exceptions import ServiceOSException

_DRAFT_FIELDS = {
    "delivery_mode", "required_channels", "primary_channels", "fallback_channels",
    "escalation_delay_minutes", "consent_required", "retry_interval_seconds",
    "max_attempts", "dedup_window_seconds", "rate_limit_per_hour",
    "quiet_hours_start", "quiet_hours_end", "severity_override_bypasses_quiet_hours",
    "expiry_minutes", "change_summary",
}


class NotificationPolicyService:

    def _event(self, event_key: str):
        cfg = NotificationEventRegistry.get(event_key)
        if not cfg:
            raise ServiceOSException("NOT_FOUND", f"Event '{event_key}' not registered", status_code=404)
        return cfg

    async def get_current(self, db: AsyncSession, event_key: str, vertical_key: str | None) -> dict | None:
        self._event(event_key)
        p = (await db.execute(select(NotificationPolicy).where(
            NotificationPolicy.event_key == event_key,
            NotificationPolicy.vertical_key == vertical_key,
            NotificationPolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        if not p:
            return None
        d = p.to_dict()
        d["recipient_rules"] = [r.to_dict() for r in await self._rules(db, p.id)]
        return d

    async def get_draft(self, db: AsyncSession, event_key: str, vertical_key: str | None) -> dict | None:
        self._event(event_key)
        p = (await db.execute(select(NotificationPolicy).where(
            NotificationPolicy.event_key == event_key,
            NotificationPolicy.vertical_key == vertical_key,
            NotificationPolicy.status == "draft",
        ).order_by(NotificationPolicy.version_number.desc()))).scalars().first()
        if not p:
            return None
        d = p.to_dict()
        d["recipient_rules"] = [r.to_dict() for r in await self._rules(db, p.id)]
        return d

    async def _rules(self, db: AsyncSession, policy_id: uuid.UUID) -> list[NotificationPolicyRecipientRule]:
        return (await db.execute(select(NotificationPolicyRecipientRule).where(
            NotificationPolicyRecipientRule.policy_id == policy_id))).scalars().all()

    async def list_history(self, db: AsyncSession, event_key: str, vertical_key: str | None) -> list[dict]:
        self._event(event_key)
        rows = (await db.execute(select(NotificationPolicy).where(
            NotificationPolicy.event_key == event_key, NotificationPolicy.vertical_key == vertical_key,
        ).order_by(NotificationPolicy.version_number.desc()))).scalars().all()
        return [p.to_dict() for p in rows]

    def _validate(self, payload: dict, event_key: str) -> list[str]:
        errors = []
        cfg = NotificationEventRegistry.get(event_key)
        if cfg is None:
            errors.append(f"'{event_key}' is not a registered event")
            return errors

        required = set(payload.get("required_channels") or [])
        primary = set(payload.get("primary_channels") or [])
        fallback = set(payload.get("fallback_channels") or [])
        for label, chset in (("required_channels", required), ("primary_channels", primary), ("fallback_channels", fallback)):
            bad = chset - set(ALL_CHANNELS)
            if bad:
                errors.append(f"{label} contains unknown channel(s): {sorted(bad)}")

        if cfg.is_mandatory and CHANNEL_IN_APP not in required:
            errors.append("in_app must be a required channel for a mandatory event")

        # DELIVERY-READINESS-BLOCKER: a policy cannot require or make
        # primary a channel with no working provider (real Twilio/SMTP
        # code exists, but in a different, unwired engine -- see
        # provider_status_service.py). Fallback channels are exempt: they
        # exist precisely to degrade to something that DOES work.
        not_ready = (required | primary) - _LIVE_CHANNELS
        if not_ready:
            errors.append(f"channel(s) {sorted(not_ready)} have no working provider configured -- "
                          f"cannot be required or primary (see Delivery & Providers)")

        recipient_roles = {r.get("recipient_role") for r in payload.get("recipient_rules") or []}
        bad_roles = recipient_roles - RECIPIENT_ROLES
        if bad_roles:
            errors.append(f"recipient_rules contains unknown role(s): {sorted(bad_roles)}")

        dm = payload.get("delivery_mode", "immediate")
        if dm not in DELIVERY_MODES:
            errors.append(f"delivery_mode must be one of {sorted(DELIVERY_MODES)}")

        max_attempts = payload.get("max_attempts", 3)
        if max_attempts is not None and max_attempts < 1:
            errors.append("max_attempts must be at least 1")

        qs, qe = payload.get("quiet_hours_start"), payload.get("quiet_hours_end")
        if bool(qs) != bool(qe):
            errors.append("quiet_hours_start and quiet_hours_end must both be set or both be empty")

        return errors

    def validate(self, payload: dict, event_key: str) -> dict:
        errors = self._validate(payload, event_key)
        return {"valid": len(errors) == 0, "errors": errors}

    async def save_draft(self, db: AsyncSession, event_key: str, vertical_key: str | None,
                         payload: dict, *, actor_id: uuid.UUID | None) -> dict:
        errors = self._validate(payload, event_key)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        existing_draft = (await db.execute(select(NotificationPolicy).where(
            NotificationPolicy.event_key == event_key, NotificationPolicy.vertical_key == vertical_key,
            NotificationPolicy.status == "draft",
        ))).scalar_one_or_none()

        if existing_draft:
            policy = existing_draft
            for k in _DRAFT_FIELDS:
                if k in payload:
                    setattr(policy, k, payload[k])
            await db.flush()
        else:
            max_version = (await db.execute(select(func.max(NotificationPolicy.version_number)).where(
                NotificationPolicy.event_key == event_key, NotificationPolicy.vertical_key == vertical_key,
            ))).scalar() or 0
            policy = NotificationPolicy(
                event_key=event_key, vertical_key=vertical_key,
                version_number=max_version + 1, status="draft", is_current=False,
                created_by_user_id=actor_id,
                **{k: payload[k] for k in _DRAFT_FIELDS if k in payload},
            )
            db.add(policy)
            await db.flush()

        if "recipient_rules" in payload:
            await db.execute(NotificationPolicyRecipientRule.__table__.delete().where(
                NotificationPolicyRecipientRule.policy_id == policy.id))
            for rule in payload["recipient_rules"]:
                db.add(NotificationPolicyRecipientRule(
                    policy_id=policy.id, recipient_role=rule["recipient_role"],
                    is_required=rule.get("is_required", True), notes=rule.get("notes"),
                ))
            await db.flush()

        await db.commit()
        d = policy.to_dict()
        d["recipient_rules"] = [r.to_dict() for r in await self._rules(db, policy.id)]
        return d

    async def publish(self, db: AsyncSession, event_key: str, vertical_key: str | None, *,
                      actor_id: uuid.UUID | None, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to publish a policy change.", status_code=422)

        draft = (await db.execute(select(NotificationPolicy).where(
            NotificationPolicy.event_key == event_key, NotificationPolicy.vertical_key == vertical_key,
            NotificationPolicy.status == "draft",
        ))).scalar_one_or_none()
        if not draft:
            raise ServiceOSException("NOT_FOUND", "No draft policy to publish.", status_code=404)

        draft_dict = draft.to_dict()
        errors = self._validate(draft_dict, event_key)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        prior = (await db.execute(select(NotificationPolicy).where(
            NotificationPolicy.event_key == event_key, NotificationPolicy.vertical_key == vertical_key,
            NotificationPolicy.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()
        before = prior.to_dict() if prior else None
        if prior:
            # Two flushes, never one -- avoids a transient unique-index
            # violation on ix_notif_policy_current (same reasoning as
            # VerticalMonetizationPolicyService.publish()).
            prior.is_current = False
            prior.status = "superseded"
            await db.flush()

        draft.status = "published"
        draft.is_current = True
        draft.published_by_user_id = actor_id
        draft.published_at = datetime.now(timezone.utc)
        await db.flush()

        db.add(NotificationPolicyAuditLog(
            policy_id=draft.id, event_key=event_key, vertical_key=vertical_key,
            actor_user_id=actor_id, action_type="notification_policy.publish",
            before_state=before, after_state=draft.to_dict(), notes=reason,
        ))
        await db.commit()
        await db.refresh(draft)
        d = draft.to_dict()
        d["recipient_rules"] = [r.to_dict() for r in await self._rules(db, draft.id)]
        return d

    async def list_audit(self, db: AsyncSession, event_key: str | None, vertical_key: str | None,
                         limit: int = 50) -> list[dict]:
        q = select(NotificationPolicyAuditLog)
        if event_key:
            q = q.where(NotificationPolicyAuditLog.event_key == event_key)
        if vertical_key is not None:
            q = q.where(NotificationPolicyAuditLog.vertical_key == vertical_key)
        rows = (await db.execute(q.order_by(NotificationPolicyAuditLog.created_at.desc()).limit(limit))).scalars().all()
        return [r.to_dict() for r in rows]
