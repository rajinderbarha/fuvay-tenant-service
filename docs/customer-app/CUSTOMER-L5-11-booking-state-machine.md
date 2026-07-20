# CUSTOMER-L5-11 — Booking State Machine

Two separate, small state machines, matching this sprint's two distinct
real concerns (loading a review vs. submitting a confirmation) — kept
separate so a failed/uncertain confirmation attempt never discards the
already-loaded review data.

## `ReviewState` (`domain/booking-state.ts`)

| State | Real trigger |
|---|---|
| `preflight_failed` | A real, lightweight precondition (reused `evaluatePricingPreflight`) is unmet |
| `loading` | `/summary` mutation idle or pending |
| `unavailable` | `/summary` call failed (network/validation) |
| `not_ready` | Real `ready_for_confirmation: false` |
| `ready` | Real `ready_for_confirmation: true` |

## `ConfirmState` (`domain/booking-state.ts`)

| State | Real trigger |
|---|---|
| `idle` | No confirm attempt made yet |
| `confirming` | `/confirm` mutation pending |
| `uncertain` | `/confirm` failed with a category where the request may have committed server-side before the response was lost (`timeout`/`network_error`/`server_error`/`unknown_error`/`maintenance`/`rate_limited`) |
| `confirmed` | `/confirm` succeeded — real `booking_id`/`booking_number` present |
| `failed` | `/confirm` failed with a category certain not to have committed (`validation_error`/`not_found`/`forbidden`/`conflict`) |

## Deliberately Absent States (per the spec's aspirational `BookingCreationState` model, §28)

`PREFLIGHTING` is not a separate observable state — the real preflight
(`mark_ready_for_confirmation`) runs *inside* the same `/confirm` request
as the transaction itself (contract-matrix.md); there is no separate
network round trip to represent as its own loading state. `CONFLICT` is
not modeled as distinct from `failed` — no real
`DRAFT_VERSION_CONFLICT`-equivalent response exists in this backend (no
draft versioning exists anywhere, unchanged since CUSTOMER-L5-06's
original finding); a `409`-shaped conflict, if it ever occurred, would
surface identically to any other `not_found`/`forbidden`-category
failure at this client's current error-normalization layer.
`DUPLICATE_RESOLVED` is not a separate state either: per
`idempotency-contract.md`, a duplicate retry returns the exact same
`confirmed` shape (just with `idempotent: true`) — this client's UI does
not need or show a different screen for it, since the customer's
experience (a confirmed booking with a real reference) is identical
either way.

## Uncertain → Confirmed Is the Real Recovery Path

Per §30, the `uncertain` state's only action is "Check status"
(`bookingReview.checkStatus`), which calls `confirm()` again — reusing
the exact same idempotency key held in `useConfirmBookingFlow`'s
`useRef`. Because the real backend's functional dedup guard is the
`(draft_type, draft_id)` unique constraint (not the idempotency key
itself — idempotency-contract.md), this retry is safe regardless of
whether the first attempt actually committed: if it did, the backend
returns the existing booking (`idempotent: true`); if it didn't, a new
one is created. Either way the state machine transitions cleanly to
`confirmed`.

## Pure, Testable Derivation

`deriveReviewState()` is a pure function over a plain
`ReviewMutationSnapshot` — directly unit-testable without mounting any
hook, mirroring every previous sprint's identical pattern.
`categorizeConfirmFailure()` is likewise a pure function over an
`ApiErrorCategory` string. `ConfirmState`'s own derivation currently lives
inline in `use-confirm-booking.ts` (not extracted to a standalone pure
function, since it additionally depends on the hook's own `hasSubmitted`
local state, which has no meaningful standalone existence outside the
hook) — its four real branches are covered indirectly through
`categorizeConfirmFailure`'s own direct tests plus the hook's own
straightforward, linear composition.
