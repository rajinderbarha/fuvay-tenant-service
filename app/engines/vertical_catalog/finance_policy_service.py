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
    """Qualifying technician = tenant member, Home-Services-assigned (this
    table is already category/vertical-scoped per tenant), employment-active
    (status='active', not deleted), and an actual technician role — NOT an
    owner/manager/dispatcher.

    BUG FIX: the previous gate query
    (`SELECT count(*) FROM provider_team_members WHERE tenant_id=:tid AND
    status='active' AND deleted_at IS NULL`) counted EVERY active team
    member regardless of role — live-reproduced against tenant Guramrit
    (244beeec-fedc-452e-8054-317e45557d4d): its one team member has
    designation='' (blank, an owner-type placeholder row, not a
    technician) and was still being counted as 1 qualifying technician.
    Restricting to ELIGIBLE_DESIGNATIONS (the same technician-role set
    home_service_assignment/service.py already uses to gate real job
    assignment eligibility — reused, not reinvented) makes Guramrit's real
    qualifying count 0, not 1.
    """
    from sqlalchemy import text as _text
    rows = (await db.execute(
        _text(
            "SELECT designation, member_type FROM provider_team_members "
            "WHERE tenant_id=:tid AND status='active' AND deleted_at IS NULL"
        ),
        {"tid": str(tenant_id)},
    )).fetchall()

    count = 0
    for r in rows:
        designation = (r.designation or "").lower()
        member_type = (r.member_type or "").lower()
        if designation in ELIGIBLE_DESIGNATIONS or member_type == "technician":
            count += 1
    return count
