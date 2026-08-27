"""One definition of "an active technician", shared by billing and capacity.

WHY THIS MODULE EXISTS

Two independent predicates used to answer the same question, and they
disagreed:

  billing  (`finance_policy_service.resolve_qualifying_technician_count`)
           counted a member whose designation or member_type looked like a
           technician.

  capacity (`provider_slot_service.assignable_technician_count`)
           additionally demanded `can_receive_assignment`, a supported
           offering for the requested service, AND a personal weekday rule
           in `provider_availability_rules`.

So a provider could buy 3 seats, add 3 technicians, satisfy the activation
gate — and still be offered ONE booking per slot, because the other two had
no per-staff availability rows. They paid for capacity the slot search would
never sell. Billing and capacity now share the predicate below, so the seat
a provider buys is the capacity they actually get.

CAPACITY IS HEADCOUNT

Availability is published by the PROVIDER (`provider_availability_rules`
with `scope_type='provider'`) and is what the customer picks a slot from.
Team members have no separate schedule — they are simply active or not — so
neither a per-staff weekday rule nor a service skill narrows capacity here.
Skills remain advisory at assignment time (a warning, never a block), which
is why they play no part in this predicate.

THE ROSTER ROW IS NOT THE LOGIN

A member can sit at status='active' while their user account is
deactivated -- confirmed live on a real technician. They can never open
the app, so they must not occupy a seat or create a bookable slot. A
member with NO login yet is a different case (not provisioned rather than
revoked) and still counts, matching what the assign path already allows.
"""
from __future__ import annotations

from app.engines.home_service_assignment.constants import ELIGIBLE_DESIGNATIONS

#: `member_type` values that do field work. An owner who also carries a
#: toolbag occupies a seat and creates capacity exactly like a hired
#: technician; an owner who only dispatches does neither.
TECHNICIAN_MEMBER_TYPES = ("technician", "owner_technician")


def normalise_designation(value: str | None) -> str:
    """Fold a human-entered designation onto the ELIGIBLE_DESIGNATIONS keys.

    Designations are stored as people type them ("Senior Technician", "Field
    Engineer") while the eligibility set uses snake_case. Lowercasing alone
    leaves every MULTI-WORD designation unmatched, so "Senior Technician"
    reads as ineligible while a plain "Technician" passes.
    """
    return "_".join((value or "").strip().lower().replace("-", " ").split())


def is_technician_role(designation: str | None, member_type: str | None) -> bool:
    """True when this roster row is a field technician.

    Either signal is enough: `member_type` is the structured field, while
    `designation` is free text a provider typed. Requiring both would drop
    real technicians whose provider filled in only one.
    """
    if (member_type or "").strip().lower() in TECHNICIAN_MEMBER_TYPES:
        return True
    return normalise_designation(designation) in ELIGIBLE_DESIGNATIONS


# ── SQL form of the same predicate ───────────────────────────────────────────
# Built from ELIGIBLE_DESIGNATIONS so the Python and SQL forms can never drift.
# The set is a code-defined constant of bare identifiers; the assertion below
# keeps it that way, so inlining the literals cannot introduce injection.
assert all(d.replace("_", "").isalnum() for d in ELIGIBLE_DESIGNATIONS), \
    "ELIGIBLE_DESIGNATIONS must contain bare identifiers only"

_DESIGNATIONS_SQL = ", ".join(f"'{d}'" for d in sorted(ELIGIBLE_DESIGNATIONS))
_MEMBER_TYPES_SQL = ", ".join(f"'{t}'" for t in TECHNICIAN_MEMBER_TYPES)


def active_technician_sql(alias: str = "ptm") -> str:
    """WHERE-clause fragment selecting active technicians for `alias`.

    Mirrors `is_technician_role` exactly, including the designation
    normalisation — `regexp_replace` collapses runs of whitespace and hyphens
    to single underscores, the SQL twin of the Python `split()`/join.
    """
    return rf"""
        {alias}.deleted_at IS NULL
        AND {alias}.status = 'active'
        AND COALESCE({alias}.can_receive_assignment, true) = true
        AND NOT EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = {alias}.user_id AND u.is_active = false
        )
        AND (
            lower(btrim(COALESCE({alias}.member_type, ''))) IN ({_MEMBER_TYPES_SQL})
            OR regexp_replace(
                   btrim(lower(COALESCE({alias}.designation, ''))),
                   '[\s-]+', '_', 'g'
               ) IN ({_DESIGNATIONS_SQL})
        )
    """.strip()
