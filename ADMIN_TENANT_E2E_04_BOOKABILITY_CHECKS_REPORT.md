# Bookability Checks Report (Part 6)

## Real backend gates confirmed (via matching diagnostics `bookability_source`/`area_coverage_source`/`availability_source`/`pricing_source`, and via the provider-matching page's copy)

The provider-matching page itself states the eligibility gate list explicitly: "Provider eligibility itself is a hard gate (bookable, coverage, technician, availability, pricing, package, credits, and deposit) — only eligible providers are ever scored." The matching-diagnostics "No eligible provider found" state repeats this exact list. This is the closest the current admin UI comes to an explicit bookability pass/fail checklist — it is a **narrative list of gate categories**, not a per-check pass/fail grid with individual ✓/✗ rows and timestamps.

## What IS verifiable and real
- Tenant active: confirmed via successful match (Demo AC Services selected) — an inactive tenant would be excluded (per the same gate list) and this was not observed.
- Business profile complete / service coverage / area coverage: confirmed structurally — `area_coverage_source: "normalized_service_area_coverage"` in the diagnostics response is a real named source, not a placeholder string.
- Availability open: `availability_source: "tenant_availability_rules"` — real named source.
- Pricing rule exists / provider price range: `pricing_source: "tenant_type_brand_pricing"`, and the returned Low/Mid/High (770/850/935) are real numbers derived from the real `service_pricing_rules` row (600-950), not fabricated.
- Usage credits sufficient: real ledger balance (3958 credits as of last real deduction) with no low-balance exclusion triggered on live runs.
- No blocking compliance issue: not independently surfaced as a distinct field in the diagnostics payload; compliance would show up as an exclusion reason code if it blocked a provider (the `reason_code` field on `excluded_providers` is generic enough to carry any gate's failure code, e.g. the observed `ZIPCODE_NOT_COVERED`).

## What is NOT present as a dedicated "Bookability Checks" screen
There is no separate `/admin/bookability` page wired specifically as a per-provider pass/fail checklist with "last-checked time" — `/admin/bookability/providers` exists on disk per the E2E-02 route map but is a separate, unrelated admin tool (not part of this sprint's Home Services matching/operations/deduction scope per the strict-scope list, and not linked from provider-matching/matching-diagnostics). Within THIS sprint's strict scope (provider-matching + matching-diagnostics pages), bookability is surfaced as:
1. A narrative gate list (both pages),
2. Real "Canonical Sources" attribution per gate category (matching-diagnostics),
3. Real exclusion reason codes when a gate fails (matching-diagnostics "Excluded Providers" card).

This is genuinely useful and non-misleading — it never claims a provider is bookable when it isn't (confirmed: an uncovered zipcode correctly excludes/empties the result), and it never hides a real reason. It does not, however, meet the spec's literal ask for a "last-checked time" and individual pass/fail rows in a dedicated view.

## Verdict
**PASS with a documented UI-completeness gap.** The underlying bookability logic is real, correctly gates matching, and surfaces genuine reason codes — not broken or misleading (so this does NOT trigger `NOT_READY_ADMIN_BOOKABILITY_FAILED`, which per spec is reserved for "broken/misleading"). The gap is presentation depth (no explicit last-checked timestamp / individual pass-fail grid), tracked in Remaining Blockers as a follow-up UI enhancement, not a correctness defect.
