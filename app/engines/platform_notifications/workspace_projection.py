"""Tenant Notification Center — workspace projection.

Derives category / action-required / critical / "assigned to me" from the
REAL data already on InAppNotification (notification_type = the exact
event_key fire_event() stamped it with, severity = the registry's
backend-defined severity, read_status already supports 'archived' via
READ_ARCHIVED -- unused by any endpoint until this pass). Nothing here is
computed client-side or fabricated: every category/action mapping below is
keyed to an event_key that is actually registered in event_registry.py and
actually fired by real business logic (confirmed by audit before writing
this file) -- an event key with no live caller is deliberately left out of
ACTION_REQUIRED_EVENT_KEYS rather than listed speculatively.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import READ_UNREAD, READ_ARCHIVED, SEV_CRITICAL
from app.engines.platform_notifications.models import InAppNotification

# event_key prefix -> left-rail category label. Every prefix here corresponds
# to an event_key block actually present in event_registry.py.
_CATEGORY_PREFIXES: list[tuple[str, str]] = [
    ("booking.", "Jobs & bookings"),
    ("job.", "Jobs & bookings"),
    ("appointment.", "Jobs & bookings"),
    ("lead.", "Jobs & bookings"),
    ("quote.", "Customer approvals"),
    ("review.", "Customer approvals"),
    ("complaint.", "Complaints"),
    ("payment.", "Finance & credits"),
    ("invoice.", "Finance & credits"),
    ("commission.", "Finance & credits"),
    ("wallet.", "Finance & credits"),
    ("chat.", "Team & dispatch"),
    ("document.", "Documents & verification"),
    ("tenant.", "System"),
    ("auth.", "System"),
    ("engine.", "System"),
    ("category.", "System"),
]
ALL_CATEGORIES = ["Jobs & bookings", "Customer approvals", "Complaints", "Team & dispatch",
                   "Documents & verification", "Finance & credits", "System"]

# Real, currently-firing event keys that represent an unresolved tenant
# action -- NOT every event (e.g. "job.completed" needs no tenant action).
#
# IMPORTANT, found live while wiring this: event_registry.py registers
# "complaint.created"/"complaint.provider_responded"/etc, but the REAL
# complaints engine (complaint_service.py) never calls fire_event() at all
# for provider-facing complaint notifications -- it hand-rolls
# InAppNotification rows via notify_provider_complaint() using entirely
# DIFFERENT notification_type strings ("complaint.filed",
# "complaint.settlement_proposed", "complaint.ai_settlement_proposed").
# Similarly, job.quote_required / quote.* / wallet.* / commission.failed are
# registered in event_registry.py but have ZERO real callers anywhere in
# the codebase (confirmed by grep) -- listing them here would silently
# never populate. Only keys with a CONFIRMED real caller are listed.
ACTION_REQUIRED_EVENT_KEYS = {
    "booking.new",                        # assign a technician
    "complaint.filed",                    # respond to a new complaint
    "complaint.settlement_proposed",      # provider must act on settlement
    "complaint.ai_settlement_proposed",   # provider must act on AI settlement
    "payment.confirmation_requested",     # confirm direct payment
    "payment.mismatch_reported",          # resolve a payment mismatch
    "document.changes_requested",         # resubmit the document
    "document.rejected",                  # resubmit the document
    "document.expiring",                  # renew the document
}

# Trusted destination map: notification_type -> a frontend ROUTE TEMPLATE.
# The frontend must render this, never the raw action_url the outbox
# stored (spec: never redirect via an arbitrary backend URL). {entity_id}
# is substituted with source_record_id when present.
TRUSTED_DESTINATIONS: dict[str, str] = {
    "booking.new": "/home-services/dispatch",
    "job.assigned": "/service-jobs/{entity_id}",
    "job.quote_required": "/service-jobs/{entity_id}/quotes",
    "quote.sent_to_customer": "/service-jobs/{entity_id}/quotes",
    "quote.customer_approved": "/service-jobs/{entity_id}/quotes",
    "quote.customer_rejected": "/service-jobs/{entity_id}/quotes",
    "quote.revision_requested": "/service-jobs/{entity_id}/quotes",
    # Real, live notification_type strings the complaints engine actually
    # fires to the tenant owner (see complaint_service.py's calls to
    # notify_provider_complaint) -- NOT the aspirational registry keys.
    "complaint.filed": "/home-services/complaints/{entity_id}",
    "complaint.settlement_proposed": "/home-services/complaints/{entity_id}",
    "complaint.ai_settlement_proposed": "/home-services/complaints/{entity_id}",
    # Registry keys kept for forward-compat if these are ever wired through
    # fire_event() -- currently dead (no real caller), harmless if unused.
    "complaint.created": "/home-services/complaints/{entity_id}",
    "complaint.provider_responded": "/home-services/complaints/{entity_id}",
    "complaint.resolution_proposed": "/home-services/complaints/{entity_id}",
    "complaint.resolved": "/home-services/complaints/{entity_id}",
    "payment.confirmation_requested": "/home-services/bookings-jobs?job_id={entity_id}",
    "payment.mismatch_reported": "/home-services/bookings-jobs?job_id={entity_id}",
    "payment.confirmed_by_customer": "/home-services/bookings-jobs?job_id={entity_id}",
    "wallet.low_balance": "/finance/usage-credit-ledger",
    "wallet.exhausted": "/finance/usage-credit-ledger",
    "commission.failed": "/finance/usage-credit-ledger",
    "review.submitted": "/reviews",
    "review.flagged": "/reviews",
    "review.reply_submitted": "/reviews",
    # Real, live notification_type strings (customer_reviews/notifications.py,
    # quote_checklist/notifications.py) -- these bypass fire_event()/the
    # registry entirely, same class of finding as the complaints engine.
    # The real stored action_url for "review.new" is "/provider/reviews",
    # a route that doesn't exist -- exactly why destinations are never
    # taken from the raw backend value.
    "review.new": "/reviews",
    # "quote.decision" deliberately has NO destination mapping here: its
    # source_record_id is the QUOTE id (quote_checklist/notifications.py
    # stores source_id=quote.id), not the job id the real
    # "/service-jobs/{job_id}/quotes" route needs -- substituting the quote
    # id into that template would build a broken link. The notification's
    # own stored action_url happens to be correct for this one case (it has
    # job_id in scope when written), but trusting a stored action_url
    # per-event-type defeats the point of a trusted-destination map, so
    # this is left as a documented gap rather than a wrong link.
    "document.submitted": "/documents",
    "document.verified": "/documents",
    "document.changes_requested": "/documents",
    "document.rejected": "/documents",
    "document.expiring": "/documents",
}


def resolve_category(notification_type: str) -> str:
    for prefix, label in _CATEGORY_PREFIXES:
        if notification_type.startswith(prefix):
            return label
    return "System"


def resolve_destination(notification_type: str, source_record_id: uuid.UUID | None) -> str | None:
    template = TRUSTED_DESTINATIONS.get(notification_type)
    if not template:
        return None
    return template.format(entity_id=str(source_record_id) if source_record_id else "")


def is_action_required(n: InAppNotification) -> bool:
    return n.read_status == READ_UNREAD and n.notification_type in ACTION_REQUIRED_EVENT_KEYS


def project_item(n: InAppNotification) -> dict:
    d = n.to_dict()
    d["category"] = resolve_category(n.notification_type)
    d["is_action_required"] = is_action_required(n)
    d["is_critical"] = n.severity == SEV_CRITICAL
    d["destination"] = resolve_destination(n.notification_type, n.source_record_id)
    return d


async def get_workspace_summary(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Backend-authoritative summary cards + category counts. Every number
    is a real query against InAppNotification -- never a client-side count
    of the currently-loaded page."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    base = select(InAppNotification).where(
        InAppNotification.user_id == user_id,
        InAppNotification.read_status != READ_ARCHIVED,
    )
    rows = (await db.execute(base)).scalars().all()

    unread = sum(1 for n in rows if n.read_status == READ_UNREAD)
    action_required = sum(1 for n in rows if is_action_required(n))
    critical = sum(1 for n in rows if n.severity == SEV_CRITICAL and n.read_status == READ_UNREAD)
    today = sum(1 for n in rows if n.created_at and n.created_at >= today_start)
    # "Assigned to me" is only genuinely computable for the one entity type
    # where assignment is a real, checkable fact this pass (a job.assigned
    # notification IS the assignment) -- not fabricated for entity types
    # with no assignment concept wired here.
    assigned_to_me = sum(1 for n in rows if n.notification_type == "job.assigned")

    category_counts: dict[str, int] = {c: 0 for c in ALL_CATEGORIES}
    for n in rows:
        category_counts[resolve_category(n.notification_type)] += 1

    return {
        "summary": {
            "unread": unread, "action_required": action_required,
            "critical": critical, "today": today, "assigned_to_me": assigned_to_me,
        },
        "category_counts": category_counts,
        "total_active": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_workspace_items(db: AsyncSession, user_id: uuid.UUID,
                              limit: int = 30, offset: int = 0) -> dict:
    base = select(InAppNotification).where(
        InAppNotification.user_id == user_id,
        InAppNotification.read_status != READ_ARCHIVED,
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (await db.execute(base.order_by(InAppNotification.created_at.desc())
                             .limit(limit).offset(offset))).scalars().all()
    return {"items": [project_item(row) for row in rows], "total": int(total),
            "limit": limit, "offset": offset}
