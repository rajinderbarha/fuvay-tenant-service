# Booking Audit/History Provenance

## Classification: SUPPORTING_EVIDENCE_ONLY (not AUTHORITATIVE_PROVENANCE)

`BookingStatusHistory` (append-only, `booking_id` FK, `changed_by`, `changed_by_role`, `reason`,
`created_at`) records every status transition, including who made it and their role at the time.

## What it CAN prove

- The exact sequence of status transitions and their timestamps.
- Which `actor_id`/`actor_role` triggered each transition (as self-reported by the authenticated
  session at the time — not independently re-verified).
- That `confirm_booking`'s literal history reason (`"Confirmed by tenant owner"`) was written,
  confirming the confirmation path taken.

## What it CANNOT prove (and was not relied upon for this slice's fix)

- Independent, cryptographically-verifiable proof of actor identity beyond the session's own
  claim — this is standard application-level audit logging, not a tamper-evident ledger. No
  integrity/immutability mechanism beyond normal database row protection exists.
- Genuine customer participation/intent — the history only shows WHO called the API, not whether
  a human customer meaningfully consented (this is exactly why this slice's fix targets
  `create_booking`'s customer-identity/relationship validation directly, rather than trying to
  infer trustworthiness from history text).

## Why this slice's fix does not depend on audit/history at all

`_assert_tenant_customer_relationship` and this slice's new `create_booking` checks both query
only structural fields (`status`, `tenant_id`, `customer_id`, `booking_id`, `parent_job_id`) —
never `BookingStatusHistory` — for authorization decisions. This is intentional: using audit
prose or `actor_role` history labels as security authority would violate the mission's explicit
instruction not to do so unless integrity/immutability is established, which it is not.
