"""CustomerOperationalAccessPolicy — canonical, single-source field/action
authorization for tenant-side access to customer contact/address data.

Business requirement (marketplace anti-disintermediation): customers must
book through the Fuvay customer app; providers/technicians must not
receive permanent reusable contact info that lets them route future bookings
off-platform. This module is the ONE place that decides — given tenant,
staff, customer, job, job status, assignment and purpose — which fields and
actions are allowed right now. Nothing about this should be re-decided in a
React component; routers/services call `evaluate()` and project only what it
returns.

Job-state vocabulary reused verbatim from the real execution-engine status
machine (app.engines.execution.constants / bookings_jobs_stage_mapping) —
this file does not invent a parallel status system.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.engines.execution.constants import (
    JS_PENDING_ASSIGNMENT, JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED,
    JS_ON_THE_WAY, JS_REACHED_SITE, JS_INSPECTION_STARTED, JS_INSPECTION_DONE,
    JS_QUOTE_REQUIRED, JS_SERVICE_STARTED, JS_WORK_DONE,
    JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED, JS_FAILED, JS_CLOSED_ESTIMATE_DECLINED,
)

# ── Reason codes (spec section 9, verbatim) ─────────────────────────────────
class ReasonCode(str, Enum):
    CUSTOMER_RELATIONSHIP_NOT_FOUND = "CUSTOMER_RELATIONSHIP_NOT_FOUND"
    TENANT_SCOPE_VIOLATION          = "TENANT_SCOPE_VIOLATION"
    JOB_ACCESS_NOT_ACTIVE           = "JOB_ACCESS_NOT_ACTIVE"
    STAFF_NOT_ASSIGNED              = "STAFF_NOT_ASSIGNED"
    CONTACT_RELAY_UNAVAILABLE       = "CONTACT_RELAY_UNAVAILABLE"
    ADDRESS_ACCESS_NOT_YET_AVAILABLE = "ADDRESS_ACCESS_NOT_YET_AVAILABLE"
    ADDRESS_ACCESS_EXPIRED          = "ADDRESS_ACCESS_EXPIRED"
    COMMUNICATION_WINDOW_EXPIRED    = "COMMUNICATION_WINDOW_EXPIRED"
    DISPUTE_CASE_REQUIRED           = "DISPUTE_CASE_REQUIRED"
    MARKETING_CONSENT_REQUIRED      = "MARKETING_CONSENT_REQUIRED"
    GRANTED                          = "GRANTED"


# Pre-assignment statuses: no exact address / contact, ever.
PRE_ASSIGNMENT_STATUSES = {JS_PENDING_ASSIGNMENT}

# "Assigned/scheduled" bucket — assigned staff may get operational access.
ASSIGNED_STATUSES = {JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED}

# Active field-work bucket.
ACTIVE_WORK_STATUSES = {
    JS_ON_THE_WAY, JS_REACHED_SITE, JS_INSPECTION_STARTED,
    JS_INSPECTION_DONE, JS_QUOTE_REQUIRED, JS_SERVICE_STARTED,
}

# Work done / pending confirmation — grace period, masked contact via relay only.
WORK_DONE_STATUSES = {JS_WORK_DONE}

TERMINAL_COMPLETED_STATUSES = {"completed"}
TERMINAL_CANCELLED_STATUSES = {JS_CANCELLED, JS_FAILED, JS_CLOSED_ESTIMATE_DECLINED, JS_CUSTOMER_NOT_AVAIL}

# Grace period after WORK_DONE / completion during which relay communication
# (never raw contact) stays open for confirmation/follow-up.
COMPLETION_GRACE_PERIOD = timedelta(hours=48)

BASE_FIELDS = {
    "alias", "service_group", "master_service", "job_type", "type_brand",
    "locality", "pincode", "requested_schedule", "diagnosis_notes", "diagnosis_photos",
}
OPERATIONAL_FIELDS = BASE_FIELDS | {"exact_address", "directions", "job_instructions"}


@dataclass
class AccessDecision:
    allowed_fields: set[str] = field(default_factory=set)
    allowed_actions: set[str] = field(default_factory=set)
    access_expiry: datetime | None = None
    reason_code: ReasonCode = ReasonCode.GRANTED
    granted: bool = False

    def to_dict(self) -> dict:
        return {
            "allowed_fields": sorted(self.allowed_fields),
            "allowed_actions": sorted(self.allowed_actions),
            "access_expiry": self.access_expiry.isoformat() if self.access_expiry else None,
            "reason_code": self.reason_code.value,
            "granted": self.granted,
        }


def _deny(reason: ReasonCode, fields: set[str] | None = None) -> AccessDecision:
    return AccessDecision(allowed_fields=fields or set(), reason_code=reason, granted=False)


def evaluate(
    *,
    tenant_id: uuid.UUID,
    job_tenant_id: uuid.UUID | None,
    staff_id: uuid.UUID | None,
    assigned_staff_id: uuid.UUID | None,
    customer_id: uuid.UUID | None,
    job_status: str | None,
    job_updated_at: datetime | None = None,
    is_dispatcher: bool = False,
    complaint_open: bool = False,
    purpose: str = "operational",
    current_time: datetime | None = None,
) -> AccessDecision:
    """Single canonical entry point. Returns the field/action grant for one
    (tenant, staff, customer, job) tuple at `current_time`.

    Callers (routers/services) MUST project only `allowed_fields` — never
    fall back to raw model attributes for fields not in that set.
    """
    now = current_time or datetime.now(timezone.utc)

    if customer_id is None:
        return _deny(ReasonCode.CUSTOMER_RELATIONSHIP_NOT_FOUND)

    if job_tenant_id is not None and job_tenant_id != tenant_id:
        return _deny(ReasonCode.TENANT_SCOPE_VIOLATION)

    if job_status is None:
        return _deny(ReasonCode.JOB_ACCESS_NOT_ACTIVE, BASE_FIELDS)

    staff_is_assigned = (
        staff_id is not None and assigned_staff_id is not None and staff_id == assigned_staff_id
    )

    # ── Complaint/warranty/rework: controlled case channel only, never raw contact ──
    if complaint_open and purpose == "dispute":
        if not (staff_is_assigned or is_dispatcher):
            return _deny(ReasonCode.DISPUTE_CASE_REQUIRED, BASE_FIELDS)
        return AccessDecision(
            allowed_fields=BASE_FIELDS | {"masked_locality_snapshot"},
            allowed_actions={"message_relay", "call_relay"},
            access_expiry=now + timedelta(days=14),
            reason_code=ReasonCode.GRANTED, granted=True,
        )

    # ── Before assignment: never exact address/contact ──
    if job_status in PRE_ASSIGNMENT_STATUSES:
        return AccessDecision(allowed_fields=BASE_FIELDS, allowed_actions=set(),
                               reason_code=ReasonCode.ADDRESS_ACCESS_NOT_YET_AVAILABLE, granted=True)

    # ── Cancelled ──
    if job_status in TERMINAL_CANCELLED_STATUSES:
        # If it was cancelled before ever being assigned, or staff isn't the
        # assigned one, no address/contact at all.
        if not staff_is_assigned:
            return _deny(ReasonCode.JOB_ACCESS_NOT_ACTIVE, BASE_FIELDS)
        return AccessDecision(allowed_fields=BASE_FIELDS | {"masked_locality_snapshot"},
                               allowed_actions=set(), reason_code=ReasonCode.ADDRESS_ACCESS_EXPIRED,
                               granted=True)

    # ── Assigned/scheduled/active work: only the assigned staff (or dispatcher) ──
    if job_status in ASSIGNED_STATUSES or job_status in ACTIVE_WORK_STATUSES:
        if not (staff_is_assigned or is_dispatcher):
            return _deny(ReasonCode.STAFF_NOT_ASSIGNED, BASE_FIELDS)
        return AccessDecision(
            allowed_fields=OPERATIONAL_FIELDS,
            allowed_actions={"message_relay", "call_relay", "view_exact_address"},
            access_expiry=None,  # open for the duration of active assignment
            reason_code=ReasonCode.GRANTED, granted=True,
        )

    # ── Work done: grace period, relay only, address only if operationally needed ──
    if job_status in WORK_DONE_STATUSES:
        if not (staff_is_assigned or is_dispatcher):
            return _deny(ReasonCode.STAFF_NOT_ASSIGNED, BASE_FIELDS)
        expiry = (job_updated_at or now) + COMPLETION_GRACE_PERIOD
        if now > expiry:
            return AccessDecision(allowed_fields=BASE_FIELDS | {"masked_locality_snapshot"},
                                   allowed_actions=set(), reason_code=ReasonCode.COMMUNICATION_WINDOW_EXPIRED,
                                   granted=True)
        return AccessDecision(
            allowed_fields=BASE_FIELDS | {"exact_address", "masked_locality_snapshot"},
            allowed_actions={"message_relay", "call_relay"},
            access_expiry=expiry, reason_code=ReasonCode.GRANTED, granted=True,
        )

    # ── Completed (post grace period): revoked ──
    if job_status in TERMINAL_COMPLETED_STATUSES:
        expiry = (job_updated_at or now) + COMPLETION_GRACE_PERIOD
        if now <= expiry and staff_is_assigned:
            return AccessDecision(
                allowed_fields=BASE_FIELDS | {"masked_locality_snapshot"},
                allowed_actions={"message_relay"},
                access_expiry=expiry, reason_code=ReasonCode.GRANTED, granted=True,
            )
        return AccessDecision(allowed_fields=BASE_FIELDS | {"masked_locality_snapshot"},
                               allowed_actions=set(), reason_code=ReasonCode.ADDRESS_ACCESS_EXPIRED,
                               granted=True)

    # Unknown status — fail closed.
    return _deny(ReasonCode.JOB_ACCESS_NOT_ACTIVE, BASE_FIELDS)


# ── Tenant-scoped, non-reversible customer alias (spec section 2) ──────────
import hashlib


def customer_alias(tenant_id: uuid.UUID, customer_id: uuid.UUID) -> str:
    """Stable per-(tenant,customer) alias, e.g. 'Customer HS-8F42'. One-way
    (sha256 of tenant+customer+app-internal salt truncated), never derived
    from or reversible to phone/email, and different per tenant for the
    same customer (salted with tenant_id so no cross-tenant correlation)."""
    salt = b"serviceos-customer-alias-v1"
    digest = hashlib.sha256(salt + str(tenant_id).encode() + str(customer_id).encode()).hexdigest()
    return f"Customer HS-{digest[:4].upper()}"


RAW_CONTACT_KEYS = ("customer_name", "customer_phone", "customer_email", "phone", "email")
RAW_ADDRESS_KEYS = ("address_snapshot", "address", "exact_address", "address_line_1", "address_line_2")


def sanitize_projection(
    decision: AccessDecision, raw: dict, *,
    tenant_id: uuid.UUID, customer_id: uuid.UUID | None,
    city: str | None = None, zipcode: str | None = None,
) -> dict:
    """Apply an already-computed AccessDecision to a raw booking/job dict
    (e.g. ServiceBooking.to_dict()/ServiceJob.to_dict()) before it is
    returned from any tenant/staff-facing endpoint. Single reusable
    sanitizer so routers don't hand-roll parallel masking logic — every
    call site strips the same raw contact/address keys and substitutes the
    alias + masked locality, gated by the same policy decision used
    elsewhere for this job.
    """
    out = dict(raw)
    for k in RAW_CONTACT_KEYS:
        out.pop(k, None)
    if "exact_address" not in decision.allowed_fields:
        for k in RAW_ADDRESS_KEYS:
            out.pop(k, None)
    out["customer_alias"] = customer_alias(tenant_id, customer_id) if customer_id else None
    out["locality"] = masked_locality(city, zipcode)
    out["access_reason_code"] = decision.reason_code.value
    out["access_expiry"] = decision.access_expiry.isoformat() if decision.access_expiry else None
    return out


def masked_locality(city: str | None, zipcode: str | None) -> str | None:
    """'Dugri, Ludhiana · 141013'-style masked snapshot — never the full
    street address."""
    if not city and not zipcode:
        return None
    parts = [p for p in (city, zipcode) if p]
    return " · ".join(parts)
