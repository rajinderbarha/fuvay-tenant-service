# CUSTOMER-L5-11 — Preflight Contract

## The Real Preflight Is Server-Side, Not Reimplemented Client-Side

Per §22's explicit instruction ("The client must not reproduce this
complete logic locally as authority"), this sprint does not reimplement
`mark_ready_for_confirmation`'s checks. Two real, distinct layers exist:

1. **This client's own lightweight preflight** (`evaluatePricingPreflight`,
   reused verbatim from CUSTOMER-L5-09): a pure, synchronous check over
   the already-loaded draft object (draft exists, not expired, address
   selected, serviceable, provider matched) — the same defensive,
   no-network-call check every screen since L5-09 uses before attempting
   its real network action. This exists purely to avoid firing a doomed
   network request, not to be an authoritative gate.
2. **The real, authoritative, server-side preflight**:
   `mark_ready_for_confirmation` (`service.py:801-871`), invoked
   internally by `POST /{draftId}/confirm` itself (not separately
   callable) — required-field completeness, live serviceability
   re-check, live provider-bookability re-check (fresh SQL query against
   `provider_visibility_statuses`), and a valid-tier-choice check. This
   sprint's UI reflects the **result** of this real check
   (`ready_for_confirmation`, surfaced via `/summary`) — it never
   recomputes or second-guesses it.

## `ready_for_confirmation` Is Backend-Computed, Never Inferred

`build_booking_summary`'s own `ready_for_confirmation` boolean (real
requirements: `serviceability_status == "serviceable"` AND
`selected_tenant_id` set AND `selected_price_tier` in
`("low","mid","high")`) is a **close but not identical** cousin of
`mark_ready_for_confirmation`'s own, separately-enforced requirements
(which additionally include required-field completeness and a **live**
provider-bookability re-check `/summary` does not perform). This is a
real, disclosed asymmetry: `/summary`'s `ready_for_confirmation` can be
`true` while the actual `/confirm` call still fails
`SELECTED_PROVIDER_NOT_BOOKABLE` if the provider became non-bookable in
the moments between viewing the review screen and tapping "Confirm
booking." This sprint's confirm button remains enabled whenever
`ready_for_confirmation` is `true` (the only real signal available) and
handles a real preflight failure at confirm-time as a normal
`confirm_failed`/`failed` outcome (failure-matrix.md) — it does not claim
to guarantee success merely because the review screen looked ready.

## Live Provider Re-Validation — a Real, Meaningful Server-Side Guarantee

`mark_ready_for_confirmation`'s raw SQL query against
`provider_visibility_statuses` (`service.py:852-865`) is real,
independent re-validation happening at the moment of confirmation — this
sprint's client-side code does not attempt to replicate this check (it
has no access to that table), it simply trusts the backend's real
enforcement and surfaces `SELECTED_PROVIDER_NOT_BOOKABLE` as a normal
failure outcome if it fires.

## Preflight Failure Handling — What This Sprint Can and Cannot Distinguish

Per contract-matrix.md's Error Contract: `mark_ready_for_confirmation`'s
own guard exceptions are real, clean `ServiceOSException`s with specific
422 codes (`SERVICE_NOT_AVAILABLE_IN_AREA`, `INVALID_SELECTED_PRICE_OPTION`,
`SELECTED_PROVIDER_NOT_BOOKABLE`, `ERR_REQUIRED_FIELD_MISSING`,
`ERR_NO_PROVIDER_AVAILABLE`) — but this client's pre-existing,
cross-cutting `api-client.ts` error normalization (unchanged since
CUSTOMER-L5-08's original finding) never reads the failure response body,
so **none of these specific codes are actually reachable by this
client** — they all collapse to a generic `validation_error` category,
categorized as `failed` (not `uncertain`) by `categorizeConfirmFailure`
since a 422 is a certain, not-committed rejection. This is the same
pre-existing, disclosed, cross-cutting limitation every sprint since L5-08
has documented and not attempted to fix (out of scope, shared
infrastructure). See known-gaps.md.

## Test Coverage

Covered indirectly via `deriveReviewState`'s `not_ready` case
(`booking-state.test.ts`) and `categorizeConfirmFailure`'s `failed`
classification for `validation_error` (the category every real preflight
failure from `/confirm` collapses to).
