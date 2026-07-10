# HS6 — Provider Matching Report

## Real, substantial pre-existing engine found
`app/engines/home_service_booking/matching_engine.py` (530 lines) and
its caller `service.py` already implement provider-first matching:
`select_best_provider()` runs a real eligibility gate (bookable status,
offering enablement, type/brand support, technician count, availability,
package status, usage credits, security deposit) against real candidate
tenants in the requested city, scores and ranks them, and returns a
single selected provider — confirmed via source read this sprint. This
predates HS6 and was not built from scratch.

## Provider-first order confirmed
`service.py`'s matching method calls `select_best_provider()` **before**
`compute_price_tiers()` — source-order confirmed via
`test_still_provider_first_selection` (new test this sprint). Price
options cannot be computed before a provider is selected; there is no
code path that reverses this order.

## Home Services scope confirmed
`assert_home_services_vertical()` is called at the top of the matching
flow — confirmed unchanged, real vertical guard.

## Two real, critical bugs found and fixed this sprint
See `HS6_TYPE_BRAND_PRICE_RESOLUTION_REPORT.md` and
`HS6_AUTO_PRICE_OPTIONS_REPORT.md` for full detail:
1. `compute_price_tiers()` didn't apply platform fee to the high end —
   violated the ticket's explicit hard gate.
2. The bargain-rule (price) lookup ignored `offering_type_id`/`brand_id`
   entirely — the exact "Window AC price used for Split AC" bug, live
   in the real customer-facing matching path.

## Not independently re-verified this sprint
- The eligibility gate's use of `tenant_wallets`/`security_deposits`/
  `tenant_package_assignments` (a **different** set of tables than the
  ones `_evaluate_provider_bookability` reads — `tenant_billing` — fixed
  in HS4B). This is a real, confirmed **data-source inconsistency**
  between the two bookability-adjacent systems in the codebase; not
  unified this sprint (too large a change for the remaining time
  budget). Flagged in Remaining Blockers.
- Live HTTP curl testing of the full `select_best_provider`/matching
  HTTP endpoint (would require constructing a full booking-draft/
  category context) — not performed. The two pure-function bugs found
  were instead live-verified via direct Python re-import against the
  real fixed functions with the ticket's exact numeric examples.

## Verdict
Provider matching: **real, substantial, pre-existing engine**, with 2
critical bugs found and fixed this sprint (both live-verified at the
function level). A real data-source inconsistency between two parallel
bookability-checking systems was found and documented, not fixed.
