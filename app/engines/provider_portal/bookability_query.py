"""Reusable SQL expression for canonical provider bookability.

``provider_visibility_statuses`` deliberately has no ORM model. Keeping the
latest-row lookup here prevents customer discovery, serviceability, and
booking matching from disagreeing about whether a provider may be shown.
"""
from __future__ import annotations

from sqlalchemy import column, select, table


# Provider bookability is stored tenant-wide, while technician skill/capacity
# is resolved per exact service at match time. A historical snapshot blocked
# only by this coarse readiness code may therefore enter the exact matcher;
# that matcher must still prove the requested service has a qualified
# technician and a real slot. Every other blocker remains fail-closed.
EXACT_MATCH_SOFT_BLOCKERS = frozenset({"READY_TECHNICIAN_MISSING"})


def allows_exact_service_matching(
    is_bookable: bool,
    blockers: list[dict] | tuple[dict, ...] | None,
) -> bool:
    if is_bookable:
        return True
    codes = {
        str(item.get("code"))
        for item in (blockers or [])
        if isinstance(item, dict) and item.get("code")
    }
    return bool(codes) and codes.issubset(EXACT_MATCH_SOFT_BLOCKERS)


_PROVIDER_VISIBILITY_STATUSES = table(
    "provider_visibility_statuses",
    column("id"),
    column("tenant_id"),
    column("category_id"),
    column("is_bookable"),
    column("created_at"),
)


def latest_provider_bookable(tenant_id_column):
    """Correlated boolean expression for a tenant's latest status.

    Missing rows fail closed. Looking for any historical true row would be
    unsafe because a provider may subsequently lose a technician seat,
    credits, coverage, availability, or approval.
    """
    latest_value = (
        select(_PROVIDER_VISIBILITY_STATUSES.c.is_bookable)
        .where(
            _PROVIDER_VISIBILITY_STATUSES.c.tenant_id == tenant_id_column,
            _PROVIDER_VISIBILITY_STATUSES.c.category_id.is_(None),
        )
        .order_by(
            _PROVIDER_VISIBILITY_STATUSES.c.created_at.desc(),
            _PROVIDER_VISIBILITY_STATUSES.c.id.desc(),
        )
        .limit(1)
        .correlate_except(_PROVIDER_VISIBILITY_STATUSES)
        .scalar_subquery()
    )
    return latest_value.is_(True)
