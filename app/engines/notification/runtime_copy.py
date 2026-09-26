"""Safe runtime rendering for administrator-managed notification copy.

Operational workflows must not fail because a template is missing, inactive,
or contains an incomplete variable set.  Callers therefore supply the current
production wording as a fallback.  An active admin template takes precedence
only when it can be rendered completely.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import case, select

from app.engines.notification.models import NotificationTemplate

logger = structlog.get_logger(__name__)
_VARIABLE = re.compile(r"\{\{(\w+)\}\}")


@dataclass(frozen=True)
class RenderedCopy:
    title: str
    body: str
    action_label: str | None = None
    template_id: uuid.UUID | None = None
    used_fallback: bool = True


def _render(value: str | None, data: dict[str, object]) -> tuple[str, set[str]]:
    if not value:
        return "", set()
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in data or data[key] is None:
            missing.add(key)
            return match.group(0)
        return str(data[key])

    return _VARIABLE.sub(replace, value), missing


async def render_runtime_copy(
    db,
    *,
    event_type: str,
    channel: str,
    audience: str,
    data: dict[str, object],
    fallback_title: str,
    fallback_body: str,
    tenant_id: uuid.UUID | None = None,
    vertical_key: str | None = None,
) -> RenderedCopy:
    """Resolve tenant -> vertical -> platform copy and render it safely."""
    try:
        scope_rank = case(
            (NotificationTemplate.tenant_id == tenant_id, 0),
            (
                (NotificationTemplate.tenant_id.is_(None))
                & (NotificationTemplate.vertical == vertical_key),
                1,
            ),
            else_=2,
        )
        conditions = [
            NotificationTemplate.event_type == event_type,
            NotificationTemplate.channel == channel,
            NotificationTemplate.audience == audience,
            NotificationTemplate.status == "active",
            NotificationTemplate.is_active.is_(True),
            NotificationTemplate.archived_at.is_(None),
        ]
        if tenant_id is None:
            conditions.append(NotificationTemplate.tenant_id.is_(None))
        else:
            conditions.append(
                (NotificationTemplate.tenant_id == tenant_id)
                | (NotificationTemplate.tenant_id.is_(None))
            )
        if vertical_key:
            conditions.append(
                (NotificationTemplate.vertical == vertical_key)
                | (NotificationTemplate.vertical.is_(None))
            )
        else:
            conditions.append(NotificationTemplate.vertical.is_(None))

        template = (
            await db.execute(
                select(NotificationTemplate)
                .where(*conditions)
                .order_by(scope_rank, NotificationTemplate.updated_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if template is None:
            return RenderedCopy(fallback_title, fallback_body)

        title, missing_title = _render(template.title, data)
        body, missing_body = _render(template.body, data)
        action_label, missing_action = _render(template.action_label, data)
        missing = missing_title | missing_body | missing_action
        if missing or not body.strip():
            logger.warning(
                "notification.runtime_copy_fallback",
                event_type=event_type,
                template_id=str(template.id),
                missing_variables=sorted(missing),
            )
            return RenderedCopy(fallback_title, fallback_body)
        return RenderedCopy(
            title=title.strip() or fallback_title,
            body=body,
            action_label=action_label.strip() or None,
            template_id=template.id,
            used_fallback=False,
        )
    except Exception as exc:  # Template administration must never stop field work.
        logger.warning(
            "notification.runtime_copy_error",
            event_type=event_type,
            error=str(exc),
        )
        return RenderedCopy(fallback_title, fallback_body)
