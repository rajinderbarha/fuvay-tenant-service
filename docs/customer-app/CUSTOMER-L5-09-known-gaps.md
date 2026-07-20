# CUSTOMER-L5-09 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-09-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **This sprint's real Low/Mid/High has no city-tier or zone influence**,
   despite a real, working `CityTierConfig`-based engine existing in this
   backend — because it lives behind a separate, architecturally
   independent endpoint (`/price-estimate`) this sprint correctly does not
   use for the reasons documented in `pricing-resolution.md`. This is the
   sprint's most consequential finding, in the same category as L5-07's
   "no real SLA engine" and L5-08's "no candidate list."
3. **No bargain-eligibility signal is shown**, because
   `BargainRule.bargain_enabled` is confirmed dead code in the real
   customer pricing flow and no equivalent field is ever returned to the
   customer. See `pricing-semantics.md`'s Bargain Eligibility section for
   the full reasoning behind showing nothing rather than an inferred
   claim.
4. **No itemized cost components exist anywhere in this backend** for this
   flow — `included_items`/`excluded_items`/`components` are all
   `MISSING_BACKEND`. This sprint surfaces only the one real structured
   fact available (`payment_mode`), rather than fabricating a plausible
   line-item breakdown.
5. **No tax field exists anywhere in this flow's responses** despite
   `ServicePricingRule.tax_percent` existing in the schema (confirmed
   unread by this flow). This sprint states plainly that tax status is
   unspecified rather than guessing.
6. **Currency is hardcoded to `"INR"` server-side** — this sprint does not
   claim genuine multi-currency support is exercised, only that it renders
   whatever currency code the backend sends.
7. **No component/render tests** for `PricingEstimateScreen` — same,
   now-consistent-across-nine-sprints deprioritization pattern.
8. **`confirm_price_choice`'s request body is unvalidated raw JSON** — a
   missing `price_tier` key raises an unhandled `KeyError` server-side
   rather than a clean 422 (contract-matrix.md). Not this sprint's code to
   fix (this sprint never calls that endpoint), but documented here for
   CUSTOMER-L5-10's benefit since that sprint will call it directly.

## P2

9. **Revision detection is a client-side convenience, not a
   backend-guaranteed concept** — no revision counter exists anywhere in
   the real data. If two customers' devices race to refresh the same
   draft's price near-simultaneously, this client's own "revised" banner
   is only as good as its last-seen local snapshot, not a true
   distributed-revision check. Low real-world impact since a booking
   draft belongs to exactly one customer.
10. **No automatic revalidation trigger if the customer edits address/SLA
    without leaving this screen** — not possible today (no such editing
    control exists on `PricingEstimateScreen`), but flagged as a design
    constraint should a future sprint add inline editing here (see
    `cache-policy.md`).
11. **No analytics events actually wired to a vendor** — same
    now-nine-sprints-running gap: no analytics SDK is integrated in this
    app at all; `logger.*` calls are structured logs only.
12. **`pricing-api.ts`/`use-pricing-estimate.ts` have no dedicated unit
    tests** — consistent with the established, repo-wide pattern that thin
    API wrappers and hook-composition layers over already-tested pure
    functions are not independently tested (verified against every
    previous sprint's identical `*-api.ts`/hook files).

## P3

13. **No genuine multi-provider price-range comparison test** (would
    require a live backend with two or more real tenants having different
    `BargainRule` ranges for the same service) — see `runtime-evidence.md`.
14. **Punjabi/Hindi translations of the new `pricing.*` keys were written
    by this sprint and have not been reviewed by a native-speaking product
    reviewer** — same disclosed caveat pattern as every previous sprint's
    localization additions.
