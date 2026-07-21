# Round 6 — Playwright + Visual Evidence

Real Chromium (headless, 390px viewport), real Expo web dev server (port
19006), real live backend (confirmed healthy at the start of this round).
Screenshots in `round3-runtime-evidence/r6-*.png`.

## Full sequence results

| # | Step | Result |
|---|---|---|
| 1 | Login (light, 390px) | **PASS** — real `/v1/auth/login` |
| 2 | Home | **PASS** — real greeting, real category grid, **real "Recent Bookings" section showing the actual booking created this round** (`Need new AC installed`, `BK-20260721-000001 · Ludhiana`, `Finding a Technician`, `Demo AC Services`, `₹150`) plus 2 other real pre-existing bookings |
| 3 | Bookings list | **PASS** — the real booking appears with its real number/status/price |
| 4 | Booking Detail | **PASS** — opens with real data (booking number, provider, price, job reference) |
| 5 | Booking Detail after page refresh | **PASS** — data persists, no re-login required, no stale/blank state |
| 6 | Profile tab | **PASS** |
| 7 | Chat entry / AI session | **PASS** (same as Round 3-5 evidence) |
| 8 | `ac_repair` booking attempt (the only catalog-visible offering) | Reaches the real brand-selection step (LG/Samsung/Voltas — confirms `requires_brand` handling is correct), consistent with all prior rounds' finding that this specific offering lacks a `BargainRule` and cannot complete `match-and-price` — re-confirmed via direct API in round-6-canonical-booking-live-evidence.md rather than exhaustively re-clicked through in this specific browser pass |

## What's new and significant this round

Items 2-5 are the first time in this entire phase that a **real, canonically
created booking** (not a fixture, not injected into the DB directly) is
visible through the actual production app UI — Home's "Recent Bookings",
the Bookings tab list, and Booking Detail all show it, and it survives a
full page reload. This is the strongest runtime evidence produced in any
round of UX-06.

## Console/errors

One pre-existing cosmetic React key-prop warning (unchanged from Round 4/5,
not re-investigated this round — same root cause hypothesis stands). One
`422` network response logged as a console error during the `ac_repair`
attempt — this is the EXPECTED, real backend rejection (not a client bug);
Chromium logs any non-2xx fetch response as a console error by default, and
the app itself correctly caught and handled it (no uncaught exception, no
crash, no blank screen).

## Theme coverage

**Light theme only** — this app has no dark-theme implementation at all
(confirmed again this round; unchanged finding from Rounds 4/5). Claiming a
dark-theme pass would be fabricated; there is nothing to toggle.

## Not captured this round

320px-width and large-text-scaling evidence (a standing gap across all
rounds), Notifications with real data (no real notification-triggering event
was produced this round beyond the booking creation itself, and this round's
time was concentrated on the booking-pipeline proof).
