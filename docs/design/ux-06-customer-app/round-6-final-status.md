# Round 6 Final Status

## Outcome determination: **B, with a successful Item-4 alternate proof**

The literal question ("can the pipeline continue at server price without a
bargain result?") is answered **NO** — confirmed by direct code reading of
`match_provider_and_price()`, which unconditionally requires an active
`BargainRule` row with no fallback path (see
round-6-bargain-optionality-proof.md). This is Outcome B for the specific
`ac_repair` offering.

However, the Round 6 brief's item 4 alternate path was found and used
successfully: a real, pre-existing, already-active `BargainRule` exists for
a different real `MasterService` (`ac_installation`), in the same DEMO
tenant already seeded in Round 4. Using it, **the complete canonical booking
pipeline was proven live, end-to-end, with zero new shared policy created**:
real draft → real brand/serviceability/price → real provider match → real
tier selection → real idempotent confirm → real booking reference
(`BK-20260721-000001`) → real bookings-list insertion → real booking-detail
retrieval → **verified visible and persistent through the actual production
app UI**, not just curl (see round-6-playwright-and-visual-evidence.md).

## Status: `CUSTOMER_APP_SOURCE_COMPLETE_BACKEND_INTEGRATION_BLOCKED`

Justification against the Round 6 criteria:

- All frontend-owned source work is complete: the booking pipeline code
  (draft/brand/serviceability/price/match/tier/confirm) is correctly
  implemented and PROVEN working against the real backend — the one real
  gap (`ac_repair` lacking a `BargainRule`) is entirely a backend
  catalog/pricing data issue, not a frontend defect.
- All production screens use the new design (see prior rounds' census;
  unchanged and re-confirmed reachable this round).
- UX-06-owned typecheck stays at zero (re-verified this round, unchanged).
- Tests are stable (see round-6-test-stability.md for the 4-run sweep).
- Playwright passes up through and including a REAL booking's full
  lifecycle (creation via the pipeline, list, detail, refresh-persistence)
  — this is materially stronger than merely "up to the blocked step," since
  a real booking (via the legitimate alternate-offering path) was actually
  completed and is now durably visible in the app.
- Booking submission for the SPECIFIC catalog-visible offering (`ac_repair`)
  remains the only material blocker, and it is precisely documented
  (exact error codes, exact code path, exact missing config row) per the
  brief's requirement.

`CUSTOMER_APP_DESIGN_COMPLETE` is not used: Outcome A (bargain genuinely
optional) did not materialize — the mandatory-tier-selection finding stands.
Using DESIGN_COMPLETE would misrepresent that determination. The
`ac_repair`-specific gap, while narrow and clearly a backend data issue
rather than a frontend one, is still a real, unresolved item for the one
offering real end-users can currently discover through the catalog — hence
`SOURCE_COMPLETE_BACKEND_INTEGRATION_BLOCKED` rather than the unconditional
`DESIGN_COMPLETE`.
