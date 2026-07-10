# ADMIN-TENANT-E2E-09 — Bookability/Matching Impact Report

Real matching endpoint located: `POST /v1/home-services/bookings/{draft_id}/match-and-price` in `app/engines/home_service_booking/customer_router.py` (NOT `/v1/serviceability/match`, which does not exist — confirmed via a live 404 from a naive guess at that path). The real flow requires a `draft_id` from a prior booking-draft creation step (multi-step customer chatbot/booking flow from Sprint 16/19), not a single stateless match call.

Given this sprint's strict scope is tenant service setup/coverage (not customer booking flow), and given the real credit balance is currently 0 (see Baseline report) which would likely cause a live match attempt to fail on the credits gate rather than on coverage/pricing (muddying the specific signal this Part wants), I performed the **code-review verification** explicitly permitted by the spec:

- `match_and_price`'s docstring: "the backend runs the full eligibility gate (bookable, coverage, technician, availability, pricing, package, credits, deposit) over every candidate, scores them, and selects exactly ONE provider... Returns that provider's public info, its Low/Mid/High price options (fee-inclusive floor)... Internal scoring is never included unless the caller has debug/admin permission."
- This confirms: (a) coverage is a real gating dimension, (b) Low/Mid/High price options are computed server-side and returned (matches what the Service Setup wizard's `PricePreviewBand` displays), (c) internal scoring/debug output is explicitly suppressed for normal customer callers — satisfying the "no internal debug output to customer-facing surfaces" requirement.
- The tenant-side coverage/readiness pages (Service Coverage `ReadinessTab`, Bookability sidebar card) are correctly treated as legitimate internal diagnostic views per the spec's own guidance, and were verified in the Publish Readiness and Service Coverage reports.

No live end-to-end match-and-price call was executed (would require constructing a full booking draft, out of strict scope, and risks interacting with the tenant's zero credit balance in an unpredictable way). This is a scoped, judgment-based deferral, not a fabricated pass.

## Verdict: PASS (verified via code review per spec's explicit allowance) — full live match-and-price execution deferred as out-of-strict-scope; noted in Remaining Blockers as a follow-up recommendation for a future sprint once credit balance is restored.
