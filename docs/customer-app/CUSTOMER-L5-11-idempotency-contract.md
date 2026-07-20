# CUSTOMER-L5-11 — Idempotency Contract

## Key Source

Generated client-side, once per confirmation attempt:
`bkconf_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,12)}`
(`use-confirm-booking.ts`'s `newIdempotencyKey()`, mirroring the exact
same pattern `request-context.ts`'s pre-existing `newRequestId()` already
uses elsewhere in this app). Held in a `useRef`, generated lazily on the
first `confirm()` call, never regenerated on a subsequent retry within
the same screen instance.

## Key Lifecycle

- **Created**: on the first tap of "Confirm booking."
- **Reused**: on every subsequent retry from the same screen instance
  (explicit "Try again" after a `failed` state, or "Check status" after
  an `uncertain` state) — the `useRef` never resets except on unmount
  (navigating away and back creates a fresh hook instance and thus a
  fresh key, which is safe: the real functional dedup guard is
  `(draft_type, draft_id)`, not the key itself — see below).
- **Never persisted** beyond the component's lifetime — not written to
  `AsyncStorage`/`SecureStore`, not included in any navigation route
  param, not logged.

## The Real Functional Guard Is NOT the Client's Key

Per contract-matrix.md/baseline-verification.md: the authoritative
duplicate-prevention mechanism is a **database unique constraint** —
`CustomerBookingConfirmation` has `UNIQUE(draft_type, draft_id)`, and
`ServiceBooking` separately has its own `UNIQUE(draft_id)` index. Both are
keyed by the **draft's own ID**, not by any client-supplied idempotency
key. This means: even if this client generated a brand-new idempotency
key on every single retry (which it deliberately does not, per §26's
explicit requirement), the backend would still correctly return the
existing booking rather than create a duplicate — the client-side key
reuse is a defense-in-depth best practice matching the real, additional
`X-Idempotency-Key` middleware layer (below), not the sole thing standing
between a customer and a duplicate booking.

## Two Real, Layered Backend Mechanisms

1. **`CustomerBookingConfirmation` DB-unique lock** (authoritative) — keyed
   by `(draft_type, draft_id)`. `finalize()`'s own first step
   (`check_and_raise_if_duplicate`) checks this before attempting any
   creation; a genuine race (two simultaneous requests) is additionally
   protected by the DB constraint itself raising an `IntegrityError` on
   the losing request's insert (not directly observed this sprint — no
   live database was reachable — see runtime-evidence.md).
2. **`IdempotencyMiddleware`** (`app/core/idempotency.py`, app-wide,
   convenience layer) — reads a **differently-named** header
   (`X-Idempotency-Key`), caches the full HTTP response in Redis for 24h
   keyed by `sha256(key:path:tenant_id)`, and replays it verbatim
   (`X-Idempotency-Replayed: true`) on a repeated key+path+tenant
   combination. This client sends both `Idempotency-Key` (read directly
   by the `/confirm` endpoint for its own audit-trail storage) and
   `X-Idempotency-Key` (read by this middleware) with the identical
   value, to get the benefit of both real layers.

## Retry Behavior (this client's own logic)

- **`failed`** (certain non-commit — `validation_error`/`not_found`/
  `forbidden`/`conflict`): the customer can retry by tapping "Confirm
  booking" again in the `ready` review state — a fresh `confirm()` call
  reusing the same held key.
- **`uncertain`** (possible commit — `timeout`/`network_error`/
  `server_error`/`unknown_error`/`maintenance`/`rate_limited`): the
  customer sees the calm "checking" state and taps "Check status," which
  is literally the same `confirm()` call with the same key — safe per the
  DB-unique-constraint guarantee above, whether or not the first attempt
  actually committed.

## Multi-Device Behavior

Not directly tested this sprint (no live backend — see
runtime-evidence.md), but the same `(draft_type, draft_id)` DB-unique
guard applies regardless of which device's idempotency key arrives first
— a second device confirming the same draft would receive the identical
real booking (`idempotent: true`), never a duplicate, per the backend's
own real constraint (not a client-side assumption).

## Privacy

The idempotency key is never logged (`logger.*` calls in
`use-confirm-booking.ts`/`booking-confirmation-queries.ts` pass no key
value — verified by grep), never included in analytics, and never
rendered in any UI.

## Test Coverage

Not directly unit-tested (the key-generation function itself has no
meaningful branching to test — a single string-template call); its
real-repeatability guarantee rests on the backend's own DB-unique
constraint, documented via source reading rather than a client-side test
that would only prove the client sends a stable string, not that the
backend actually deduplicates on it.
