"""HOME-SERVICES-FINANCE-POLICY-01 — policy resolution + qualifying
technician counting.

resolve_published_policy() is the single source of truth the activation
gate (activation.py) and any admin/tenant UI must call — never re-derive
amounts from hardcoded constants. Fails closed with a stable error code
when no published policy exists, or when more than one row is marked
is_current for the same vertical (should be impossible given the unique
partial index, but defended anyway since that index only prevents it going
forward, not against pre-existing bad data).
"""
from __future__ import annotations
import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.finance_policy_models import HomeServicesActivationFinancePolicy
from app.engines.home_service_assignment.constants import ELIGIBLE_DESIGNATIONS

ERR_NO_PUBLISHED_POLICY = "FINANCE_POLICY_NOT_PUBLISHED"
ERR_AMBIGUOUS_POLICY    = "FINANCE_POLICY_AMBIGUOUS"


class FinancePolicyResolutionError(Exception):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


async def resolve_published_policy(db: AsyncSession, vertical_id: uuid.UUID) -> HomeServicesActivationFinancePolicy:
    """Fail-closed resolution: exactly one is_current=true, status=published
    row for this vertical, or raise a stable, explained error."""
    rows = (await db.execute(
        select(HomeServicesActivationFinancePolicy).where(
            and_(
                HomeServicesActivationFinancePolicy.vertical_id == vertical_id,
                HomeServicesActivationFinancePolicy.is_current == True,   # noqa: E712
                HomeServicesActivationFinancePolicy.status == "published",
            )
        )
    )).scalars().all()

    if not rows:
        raise FinancePolicyResolutionError(
            ERR_NO_PUBLISHED_POLICY,
            "No published Home Services activation finance policy exists for this vertical.",
        )
    if len(rows) > 1:
        raise FinancePolicyResolutionError(
            ERR_AMBIGUOUS_POLICY,
            f"{len(rows)} current published policies found for this vertical — expected exactly 1.",
        )
    return rows[0]


async def resolve_qualifying_technician_count(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Technicians occupying a purchased seat.

    Shares ONE predicate with slot capacity — see
    `home_service_assignment.eligibility`. These were two separate queries
    that disagreed: this one ignored `can_receive_assignment`, missed
    `owner_technician`, and compared raw-lowercased designations against
    snake_case keys (so "Senior Technician" never matched), while capacity
    additionally demanded a supported offering and a per-staff weekday rule.
    A provider could therefore buy 3 seats, pass the activation gate, and be
    sold 1 booking per slot. Billing and capacity now count the same people.
    """
    from sqlalchemy import text as _text
    from app.engines.home_service_assignment.eligibility import active_technician_sql

    count = (await db.execute(
        _text(
            "SELECT count(*) FROM provider_team_members ptm "
            "WHERE ptm.tenant_id = CAST(:tid AS uuid) AND "
            + active_technician_sql("ptm")
        ),
        {"tid": str(tenant_id)},
    )).scalar()
    return int(count or 0)
