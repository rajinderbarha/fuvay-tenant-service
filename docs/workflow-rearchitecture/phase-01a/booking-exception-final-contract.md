# Decision 10.3 — Booking Exception Resolution: Final Contract

## STATUS: BLOCKED

Per the spec's explicit instruction, this workflow "must remain BLOCKED if the canonical booking/job decision is not sufficiently resolved." The verification pass in this document set found that **three separate booking/job record systems (`Booking` legacy, field_ops `Job`, `ServiceJob` canonical) are simultaneously live and actively depended on by real production screens** across tenant-portal, super-admin, and mobile-customer-app (see `booking-job-canonical-decision.md`). This is a materially different and more serious situation than Phase 1's tentative assumption that the legacy systems were likely dead.

This workflow cannot be built without first answering: does an "exception" on a `Booking`-model booking mean the same thing as an exception on a `ServiceJob`? Do they represent the same real-world booking under two different records, or genuinely different booking types? That is unknown today.

## Correction: an explicit Booking→Job adapter already exists
Runtime route verification found `POST /v1/bookings/{booking_id}/convert-to-job` — an explicit, already-built bridge from `Booking` to field_ops `Job`. This means the blocker is not "these are unrelated systems with no adapter" but "we don't yet know if this adapter's target scope overlaps with `ServiceJob`'s scope." See `booking-job-canonical-decision.md` for the sharpened open question.

## What is NOT blocked (documented for when unblocking occurs)

### Canonical records (target state once resolved)
`ServiceJob` for the execution lifecycle. `Booking`/field_ops `Job` compatibility layer TBD per the migration plan in `booking-job-canonical-decision.md`.

### Actions with confirmed real backend support (unchanged from Phase 1, still valid once workspace is unblocked)
Retry matching, expand service area, reassign provider/technician, contact customer (routes to Domain 1/2/3 chat per `chat-domain-ownership.md`), reschedule, cancel, request information, issue service credit, deduct provider credit, schedule rework, escalate, close case — all RUNTIME_VERIFIED or SOURCE_VERIFIED against `ServiceJob`/`complaints`/`customer_credits`/`invoice_payment` in Phase 1.

### Explicitly excluded regardless of unblock status
Parts sub-panel — no backend entity exists (`quote-parts-scope-decision.md`).

## Unblocking criteria (must ALL be true before this workflow moves from BLOCKED to buildable)
1. Backend/product confirms whether `Booking` and field_ops `Job` rows correspond to the same real-world bookings as `ServiceJob` rows, or represent a genuinely separate booking type.
2. If they're the same bookings under different records: a data-migration or ID-correlation plan exists and the read-aggregation BFF (see `booking-job-canonical-decision.md` item 3) is built.
3. If they're genuinely different booking types: the workspace scope is explicitly redefined to state which booking type(s) it covers, and the other type(s) get their own (likely much simpler) resolution path, or are explicitly deferred.

## Acceptance criteria (once unblocked)
- Workspace reads/writes only the resolved canonical source(s) per the unblocking decision above.
- No screen silently conflates `Booking`, field_ops `Job`, and `ServiceJob` as if interchangeable.
- All 12 actions listed in Phase 1's `booking-exception-resolution-workflow.md` remain available, permission-gated as previously specified.

## Recommendation
Do not schedule this workflow in Phase 2. Track it as the first item of Phase 3, contingent on the backend investigation in item 1 above being completed as an explicit, resourced task — not something that resolves itself as a side effect of other Phase 2 work.
