# Resolution Decision Boundary — Slice 2F-10 (Workstream 9)

## Model and linkage
`ComplaintResolution` is created only by the provider
(`provider_offer_resolution`, Slice 2F-9/2F-9A closed, unmodified). The
customer may only decide it — `accept_resolution`/`reject_resolution`.

## Ownership fix (this slice)
Before this slice, `customer_accept_resolution`/`customer_reject_resolution`
fetched the resolution via `_get_resolution(db, resolution_id)` with **no
cross-check against the caller's already-verified `complaint_id`** — a
customer who owned complaint A could accept/reject any `resolution_id`
that happened to belong to complaint B (any other customer's or tenant's
complaint), mutating a foreign record's `.status` while the complaint
transition itself applied to their own complaint A. Fixed with the
identical pattern Slice 2F-9 used for `_get_settlement_proposal`: an
optional `complaint_id` parameter, cross-checked, failing with the same
`RESOLUTION_NOT_FOUND` a genuinely missing resolution would produce.

## Ordering defect fix (this slice)
`resolution.status` was set (and, for a rework resolution, a real
`ServiceReworkRequest` was created **and committed** via
`ServiceReworkService().create_rework_request_from_complaint`) *before*
`_transition` ever validated whether the complaint's current status
legally permits `resolved`/`rework_approved`. Fixed by pre-validating the
target status against `ALLOWED_TRANSITIONS_EXT.get(complaint.status,
set())` before any mutation or side effect — proven directly in
`test_accept_rework_resolution_illegal_state_does_not_create_rework`
(mocks `ServiceReworkService` and asserts it is never even instantiated
when the complaint's status is illegal).

## Repeated decision behavior
A second accept/reject call after the resolution has already transitioned
the complaint out of its legal source state (`awaiting_provider_response`/
`under_admin_review`) is rejected by the same pre-validation —
`STATE_TRANSITION_REJECTED`, not idempotent (the mission's classification
scheme applies here: this is not "the same safe action twice", it's
"the complaint has moved on").

## Provider cannot decide on the customer's behalf through another route
`customer_accept_resolution`/`customer_reject_resolution` are the only
callers of this decision (confirmed: `_get_resolution` has exactly 2
production call sites, both in these two methods) — no shared or
alternate route reaches the same mutation with a different persona.

## Financial/rework side effects
Rejecting a resolution has no financial or rework side effect
(`_transition` to `under_admin_review` only). Accepting a rework
resolution creates a `ServiceReworkRequest` (workflow record, not
money) — now correctly gated behind the pre-validated transition check
above. Accepting a non-rework resolution simply resolves the complaint;
no cash refund or credit issuance occurs from this path at all.
