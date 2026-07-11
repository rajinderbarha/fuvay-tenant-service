# FINAL-L5-04B — Customer Category Availability Report

> **Updated in FINAL-L5-04C.**

## FINAL-L5-04C update: real enforcement via the shared matching pipeline
`HomeServiceChatbotBookingService.match_provider_and_price()` — the real customer-facing entry point (called from the chatbot booking flow) — calls `select_best_provider()` directly, the same function now entitlement-aware (see Matching Entitlement Report). No duplicate entitlement logic was added to the customer layer (satisfying rule 1: reuse the canonical service); customer availability inherits the fix automatically because it shares the exact same code path as admin diagnostics.

### Required checks — status
| # | Check | Result |
|---|---|---|
| 1 | Category with no entitled supply follows visibility policy | **Implemented**: if `match["signals"]` is `None` (no eligible/entitled candidate survives the gate), `match_provider_and_price` raises `ERR_NO_PROVIDER_AVAILABLE` (422) — an honest, safe "no provider" response. Never fabricates or leaks a non-entitled provider's info. |
| 2 | Disabling one tenant entitlement removes only that tenant | **Live-verified** — disabling Tenant One's AC entitlement excludes only Tenant One from AC matching results; Tenant Two's own (different) entitlement set is structurally unaffected (separate DB rows, separate bulk-resolution query results) |
| 3 | Disabling the final entitled tenant removes/marks category unavailable | Structurally true — if the bulk resolver returns an empty entitled set, every candidate is excluded and `match["signals"]` is `None`, triggering the same honest `ERR_NO_PROVIDER_AVAILABLE` path |
| 4 | Re-enabling restores availability | **Live-verified** |
| 5 | Existing `service_booking` history remains readable | **Unaffected** — no read/history endpoint was touched; only the create-time matching/confirm paths gained the new check |
| 6 | Deep links to unavailable categories return safe unavailable state | The existing `ERR_NO_PROVIDER_AVAILABLE` (422) mechanism, already used for zero-coverage/zero-pricing cases, now also covers the zero-entitlement case — no new failure mode, no 500 |
| 7 | Customer search excludes inactive/unavailable categories | Global category `is_active` is already checked inside the bulk entitlement resolver itself (one of the 8 required conditions) — a globally-inactive category can never produce an entitled tenant, so it's structurally excluded |

## Booking confirmation guard (Part 6) — closes the "matched-then-revoked" window
Previously undocumented as a distinct requirement in 04B; implemented in 04C. See Matching Entitlement Report and the Bug Fix Register (L5-04C-002) for the `PROVIDER_ENTITLEMENT_CHANGED` 409 guard in `confirm_draft()`.

## Result
Customer category/provider availability is now real and entitlement-aware, achieved with zero duplicated logic (same shared matching pipeline as admin diagnostics), live-verified for both the "still entitled" and "no longer entitled" cases, plus a dedicated re-validation guard at booking confirmation time.
