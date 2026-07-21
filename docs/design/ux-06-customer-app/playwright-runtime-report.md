# Playwright Runtime Report — UX-06 (updated Round 5)

## Round 4 evidence (unchanged, still valid)

Real Chromium (headless, 390px viewport) against a real Expo web dev server
(port 19006, CORS-allowlisted) and the live backend, real seeded customer
(`customer@serviceos.local`): real login, real Home, real Bookings/Profile
tab render, real chat-session creation, real chat-scoped language selector
(Hindi selected), real 14 categories, real offering fetch, real issue/address
collection, real serviceability success, real price response ₹82. Zero
uncaught page errors, one cosmetic React key-prop warning.

## Round 5: what changed and what was blocked

Round 5 fixed a real `react-dom`/`react` version mismatch (19.2.7 vs the
project's pinned 19.2.0) that was blocking Playwright's Login screen from
rendering interactive elements entirely — root-caused and fixed via a real
npm `overrides` entry (see round-5-implementation-summary.md).

After that fix, this round's live curl-level re-verification (not
Playwright — see below for why) confirmed:
- The corrected confirm endpoint reaches a materially more precise error
  (`HOME_BOOKING_NO_PROVIDER_AVAILABLE`) than Round 3/4's generic
  `FINAL_DRAFT_NOT_READY`, proving every other real field/step in the
  pipeline is now correct (canonical-booking-live-evidence.md).

**The backend (`http://localhost:8000`) became unreachable partway through
this round** (confirmed repeatedly via `curl`/`Test-NetConnection` over an
extended polling window) — a genuine infrastructure interruption external to
this worktree, not a frontend defect. This blocked completing a fresh, full
Playwright browser certification pass with the react-dom fix in place. The
Round 4 Playwright evidence above remains valid or its own screenshots; a
fresh Round 5 pass covering the corrected confirm-endpoint flow, tier
selection UI, Service Detail screen, and dark-theme sweep is deferred to the
next round specifically because of this outage — see known-limitations.md.

## Duplicate-submit / idempotency

Proven at the request-construction layer via a real unit test
(`bookingContract.test.ts`) that a retry reuses the identical
`Idempotency-Key`; not re-exercised as a live double-click race condition in
the browser this round (blocked by the same outage).
