# CUSTOMER-L5-12 — Action Contract

## No Real `allowed_actions` Backend Contract Exists

Confirmed by exhaustive, repo-wide grep (own research + independent
cross-check, both reaching the same conclusion): no
`allowed_actions`/`can_cancel`/`can_reschedule`-shaped field exists
anywhere for `ServiceBooking`/`ServiceJob`. The one unrelated hit
(`app/core/hateoas.py`'s `tenant_allowed_actions`) is a tenant/subscription
-plan helper, structurally unrelated to bookings.

## Per-Action Real Contract

| Action | Backend route | Prerequisite | Feature owner | Customer label | This sprint's treatment |
|---|---|---|---|---|---|
| Cancel | **None** — the only real cancel endpoint (`POST /{draftId}/cancel`) operates on a pre-confirmation draft, not a confirmed `ServiceBooking` | N/A | Unowned — no sprint currently plans this per available spec context | `bookings.detail.actionCancelReschedule` | Informational row only, no route, no button |
| Reschedule | **None** | N/A | Unowned | Same row as Cancel | Informational row only |
| Track | Real live-tracking data does not exist for `ServiceBooking`/`ServiceJob` (only the separate `execution` engine's dispatched/on-the-way events, deliberately deferred — see baseline-verification.md) | N/A | CUSTOMER-L5-13 | `bookings.detail.actionTrack` | Informational row only |
| View technician | `ServiceJob.assigned_staff_id` exists but no customer-facing technician-profile endpoint was found reachable from this client's real contract | N/A | CUSTOMER-L5-13 | `bookings.detail.actionTechnician` | Informational row only |
| Approve parts | `ServiceJob.completion_data` exists (reserved, HS8B) but no real pending-parts-request field or endpoint is reachable today | N/A | CUSTOMER-L5-14 (per spec's own note) | `bookings.detail.actionParts` | Informational row only |
| View invoice | No real invoice field/endpoint exists anywhere in this flow | N/A | Unowned | `bookings.detail.actionInvoice` | Informational row only |
| Leave a review | `GET`/`POST /v1/customer/bookings/{id}/rating` (real, `home_service_assignment/customer_router.py`) | `booking.status === "completed"` (currently unreachable by any real booking — status-projection.md) AND no existing review | Submission: unowned (out of this sprint's explicit scope, §36) | `bookings.detail.leaveReview`/`alreadyReviewed` | **Real logic implemented** (query the real `GET .../rating` endpoint, gated on real `status`), rendered as informational text since no submission screen exists yet |

## Why Informational Rows, Not Buttons

Per §28's "Do not show dead buttons": none of Cancel/Reschedule/Track/
Technician/Parts/Invoice have both (a) a real backend signal to gate
visibility on, and (b) a real, typed route to navigate to. Rather than
either fabricating a plausible-looking button that goes nowhere, or
omitting all mention of these concepts entirely (which would under-inform
the customer about what capabilities exist), this sprint renders each as
a plain, non-interactive text row: a label plus a short, honest note
("Not available in this version yet..."). This satisfies both
"do not show dead buttons" (no `onPress`, no button affordance at all)
and the spec's own instruction to acknowledge these boundaries exist.

## Review Boundary — The One Real, Implemented Boundary

Unlike the other six, the review boundary has real backend logic behind
its gating decision (`status === "completed"` and a real
`GET .../rating` existence check) — this sprint implements that gating
logic correctly and completely, even though submission itself is out of
scope and no booking can currently reach `"completed"` in practice
(status-projection.md). This is real, tested (`booking-review-status-schema.test.ts`)
forward-compatible logic, not a placeholder.

## Test Coverage

The review-boundary gating logic (`isCompleted` check, conditional
`useBookingReviewStatus` query) is exercised indirectly via
`booking-review-status-schema.test.ts`'s real null/existing-review shapes.
The six informational rows have no branching logic to test (they always
render identically) — consistent with this project's established
deprioritization of static-display component tests.
