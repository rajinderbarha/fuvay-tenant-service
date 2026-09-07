"""Home Services activation gate resolver + automatic activation orchestrator.

Runs after Admin approval (enrollment status "approved_pending_activation").
No client (tenant OR admin) can set an enrollment to "active" directly --
this module is the only code path that performs that transition, and only
after re-evaluating every gate against live data.

Gate sources are the SAME live queries already proven in
home_services_setup_service.get_setup_overview -- there is deliberately no
second, independently-computed notion of "services published" or "coverage
ready" that could drift from what the tenant saw during onboarding.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.vertical_catalog.pricing_readiness import PUBLISHED_PRICED_SERVICES_SQL

from app.engines.vertical_catalog.seat_enforcement import FREE_STARTER_SEATS
from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY
from app.engines.vertical_catalog.finance_policy_service import (
    resolve_published_policy, resolve_qualifying_technician_count, FinancePolicyResolutionError,
)

# Gate state vocabulary the frontend renders directly -- never a hardcoded
# checklist independent of this resolver.
GATE_STATES = {"not_required", "pending", "action_required", "processing", "ready", "failed", "blocked"}

_ACTIVATABLE_STATUSES = ("approved_pending_activation", "activation_requirements_pending")


async def evaluate_activation_gates(db: AsyncSession, tenant_id: uuid.UUID, vertical_id: uuid.UUID) -> list[dict]:
    """Real, live-data activation gates for one tenant's Home Services enrollment."""
    vertical_row = (await db.execute(
        text("SELECT is_enabled FROM verticals WHERE id=:vid"), {"vid": str(vertical_id)},
    )).fetchone()
    vertical_enabled = bool(vertical_row and vertical_row.is_enabled)

    billing_row = (await db.execute(
        text("SELECT credit_balance, entitled_seats "
             "FROM tenant_billing WHERE tenant_id=:tid"),
        {"tid": str(tenant_id)},
    )).fetchone()

    credit_balance = float(billing_row.credit_balance) if billing_row and billing_row.credit_balance else 0.0
    entitled_seats = int(billing_row.entitled_seats) if billing_row and billing_row.entitled_seats else 0

    published_count = (await db.execute(
        text("SELECT count(*) FROM tenant_services WHERE tenant_id=:tid "
             "AND setup_status='published' AND is_enabled=true AND is_active=true AND deleted_at IS NULL"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    # Kept in sync with home_services_setup_service.get_setup_overview's
    # identical priced_count query -- both must recognize the same set of
    # real price-bearing fields (including the inspection-workflow visit
    # fee for simple, no-type/brand services) or Setup Overview and this
    # activation gate would silently disagree about whether a tenant's
    # offerings are actually priced.
    priced_count = (await db.execute(
        text(PUBLISHED_PRICED_SERVICES_SQL),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    offerings_ready = published_count > 0 and priced_count > 0

    active_areas = (await db.execute(
        text("SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    availability_count = (await db.execute(
        text("SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    coverage_ready = active_areas > 0 and availability_count > 0

    # BUG FIX: this used to count EVERY active provider_team_members row
    # (owners/managers/dispatchers included) as a "technician" for both the
    # staff-readiness gate AND the legacy capacity calculation. Kept
    # `active_staff` (broad headcount) for the pre-existing staff_ready gate
    # (any operational person counts for "is someone staffed"), while
    # capacity uses resolve_qualifying_technician_count(), which is
    # role-filtered to real technicians only (see finance_policy_service.py).
    active_staff = (await db.execute(
        text("SELECT count(*) FROM provider_team_members WHERE tenant_id=:tid "
             "AND status='active' AND deleted_at IS NULL"),
        {"tid": str(tenant_id)},
    )).scalar() or 0
    staff_required = published_count > 0
    staff_ready = (not staff_required) or active_staff > 0

    qualifying_technician_count = await resolve_qualifying_technician_count(db, tenant_id)

    # BUG FIX (Guramrit "Finance policy unresolved"): this gate used to be
    # `billing_row is not None` -- i.e. it checked whether the TENANT
    # happened to already have a tenant_billing row, which conflates "does a
    # POLICY exist to resolve against" with "has this tenant's own billing
    # record been created yet" (a separate, per-tenant concern already
    # handled -- correctly failing closed -- by the billing/credit checks).
    # The finance_policy gate's actual job is "can we resolve a published
    # Home Services activation finance policy at all" -- root-caused and
    # fixed to call resolve_published_policy(), which fails closed with a
    # stable error code (FINANCE_POLICY_NOT_PUBLISHED /
    # FINANCE_POLICY_AMBIGUOUS) when it can't.
    policy = None
    policy_error: FinancePolicyResolutionError | None = None
    try:
        policy = await resolve_published_policy(db, vertical_id)
    except FinancePolicyResolutionError as exc:
        policy_error = exc
    finance_ready = policy is not None

    if policy is not None:
        required_credit_amount = float(
            (policy.credit_package_base_amount * (1 + policy.credit_package_gst_percent / 100))
            .quantize(__import__("decimal").Decimal("0.01"))
        )
    else:
        # No published policy resolvable — fail closed: nothing can be
        # confirmed "paid enough" against an amount we can't compute.
        required_credit_amount = float("inf")
    # BUG FIX (HOME-SERVICES-ACTIVATION-PAYMENT-01): this compared the
    # tenant's usable credit_balance against required_credit_amount, which
    # is the GST-INCLUSIVE gross the tenant pays (e.g. Rs.1,180) -- but
    # credit_balance only ever receives the base, usable portion (e.g.
    # Rs.1,000; GST is deliberately never blended into usable credit, see
    # activation_payment_service.py). That made this gate mathematically
    # impossible to satisfy: even a fully correct, confirmed payment would
    # never push credit_balance as high as the gross figure. The gate must
    # compare against the BASE (usable) amount the policy promises to credit.
    required_credit_base_amount = float(policy.credit_package_base_amount) if policy else float("inf")
    credit_purchased = credit_balance >= required_credit_base_amount

    gates: list[dict] = []

    def _add(key: str, label: str, required: bool, state: str, owner: str, action_type: str | None,
              blocking_reason: str | None = None, retryable: bool = False,
              tenant_visible_message: str | None = None, evidence: dict | None = None):
        gates.append({
            "key": key, "label": label, "required": required, "state": state, "owner": owner,
            "action_type": action_type, "blocking_reason": blocking_reason, "attempt_count": 0,
            "retryable": retryable, "tenant_visible_message": tenant_visible_message,
            "evidence": evidence or {},
        })

    _add("vertical_enabled", "Home Services availability", True,
         "ready" if vertical_enabled else "blocked", "system", None,
         blocking_reason=None if vertical_enabled else "Home Services is currently disabled platform-wide.",
         tenant_visible_message=None if vertical_enabled else "Home Services is temporarily unavailable. Contact support.")

    # Buying capacity no longer blocks activation. It is an
    # offer made during onboarding, not a toll on getting started: revenue is
    # commission on completed work, so a provider who cannot reach their first
    # job earns nothing for anyone. The gate stays in the list to advertise the
    # plan (`action_type` still drives the onboarding offer) but reports
    # `not_required`, which the readiness roll-up at the bottom of this file
    # treats as satisfied.
    _seats_covered = entitled_seats >= max(1, qualifying_technician_count)
    _add("technician_seats", "Technician seats", False,
         "ready" if _seats_covered else "not_required",
         "tenant", None if _seats_covered else "PURCHASE_TOPUP_PLAN",
         blocking_reason=None,
         retryable=False,
         tenant_visible_message="Verified" if _seats_covered
             else "No seat is needed for approval. Buy a top-up plan before adding a technician.",
         evidence={"entitled_seats": entitled_seats,
                   "free_starter_seats": FREE_STARTER_SEATS,
                   "qualifying_technicians": qualifying_technician_count})

    _credit_base = float(policy.credit_package_base_amount) if policy else None
    _credit_gst  = float(policy.credit_package_gst_percent) if policy else None
    # Also an offer rather than a toll, for the same reason. The credit floor
    # (`seat_enforcement.assert_booking_allowed`) is what actually protects the
    # platform: it stops NEW bookings once the balance runs low, at the point
    # where real money is at stake, instead of at the door.
    _add("category_wallet", "Usage credit wallet", False,
         "ready" if credit_purchased else "not_required",
         "tenant", None if credit_purchased else "PURCHASE_TOPUP_PLAN",
         blocking_reason=None,
         tenant_visible_message="Verified" if credit_purchased
             else (f"Optional: Rs.{required_credit_amount:,.2f} starter credit (Rs.{_credit_base:,.2f} + {_credit_gst:g}% GST) — "
                   f"top up before your balance reaches the booking floor"
                   if policy else "Optional — no published finance policy"),
         evidence={"required_amount": required_credit_amount if policy else None, "current_balance": credit_balance,
                   "policy_version": policy.version_number if policy else None})

    _add("approved_services", "Approved services", True,
         "ready" if offerings_ready else "blocked", "system", None,
         blocking_reason=None if offerings_ready else "No published, priced service offering.",
         tenant_visible_message=f"{published_count} service(s) validated for publication" if offerings_ready
             else "No services ready to publish")

    _add("coverage_availability", "Coverage & availability", True,
         "ready" if coverage_ready else "blocked", "system", None,
         blocking_reason=None if coverage_ready else "No active coverage area or weekly schedule.",
         tenant_visible_message=f"{active_areas} pincode(s) and weekly hours validated" if coverage_ready
             else "Coverage or schedule missing")

    # Staff capacity cannot be a hidden payment gate: starter seats are zero
    # and seats are explicitly an optional post-approval top-up.  Activation
    # therefore succeeds without staff; provider bookability remains blocked
    # until a real ready technician exists.
    _add("staff_capacity", "Staff capacity", False,
         "ready" if staff_ready else "not_required", "system", None,
         blocking_reason=None,
         tenant_visible_message=f"{active_staff} technician(s) available for required services" if staff_ready
             else "Add a technician seat and ready technician before receiving bookings")

    _add("finance_policy", "Finance policy", True,
         "ready" if finance_ready else "blocked", "system", None,
         blocking_reason=None if finance_ready else (
             f"{policy_error.code}: {policy_error.detail}" if policy_error else "Finance policy unresolved."),
         tenant_visible_message="Resolved" if finance_ready else "Finance policy unresolved",
         evidence={"policy_version": policy.version_number if policy else None,
                   "error_code": policy_error.code if policy_error else None})

    return gates


def gates_all_clear(gates: list[dict]) -> bool:
    return all(g["state"] in ("ready", "not_required") for g in gates)


async def try_auto_activate(db: AsyncSession, tenant_id: uuid.UUID,
                              vertical_key: str = HOME_SERVICES_VERTICAL_KEY,
                              actor_id: uuid.UUID | None = None) -> dict:
    """Idempotent: safe to call repeatedly (after approval, after funding or
    capacity changes, on a manual admin retry). No-ops unless the enrollment is
    currently sitting in an activatable, gate-pending state."""
    svc = VerticalCatalogService()
    enrollment = await svc.get_or_create_enrollment(db, tenant_id, vertical_key)
    if enrollment["status"] not in _ACTIVATABLE_STATUSES:
        return enrollment  # not our turn -- no-op, not an error

    v = await svc._by_key(db, vertical_key)
    gates = await evaluate_activation_gates(db, tenant_id, v.id)

    if gates_all_clear(gates):
        # "activating" is a same-transaction marker, not a durable pause --
        # a real cross-system saga (publish/enable-matching/etc.) would sit
        # here; today those steps are already true the moment gates are
        # clear (offerings are published at submission time, coverage/staff
        # already live), so the orchestrator's remaining job is the state
        # transition + audit + notification, done atomically.
        await svc.transition_enrollment(db, uuid.UUID(enrollment["id"]), "activating", actor_id=actor_id)
        result = await svc.transition_enrollment(db, uuid.UUID(enrollment["id"]), "active", actor_id=actor_id)
        # Activation can happen later than approval, after a missing gate is
        # resolved. Keep the account projection used by access checks in sync.
        await db.execute(text(
            "UPDATE tenants SET status='active', activated_at=COALESCE(activated_at, NOW()), updated_at=NOW() "
            "WHERE id=:tid AND verification_status='approved' "
            "AND status IN ('pending_activation', 'under_review', 'active')"
        ), {"tid": str(tenant_id)})
        return result

    if enrollment["status"] != "activation_requirements_pending":
        return await svc.transition_enrollment(
            db, uuid.UUID(enrollment["id"]), "activation_requirements_pending", actor_id=actor_id)

    return enrollment


async def approve_and_evaluate(db: AsyncSession, enrollment_id: uuid.UUID, tenant_id: uuid.UUID,
                                 vertical_key: str = HOME_SERVICES_VERTICAL_KEY,
                                 actor_id: uuid.UUID | None = None, reason: str | None = None) -> dict:
    """Canonical Admin 'approve' action: under_review -> approved_pending_activation,
    then immediately attempt automatic activation (never lets Admin jump straight
    to active -- only this orchestrator can)."""
    svc = VerticalCatalogService()
    await svc.transition_enrollment(db, enrollment_id, "approved_pending_activation",
                                     actor_id=actor_id, reason=reason)
    return await try_auto_activate(db, tenant_id, vertical_key, actor_id=actor_id)
