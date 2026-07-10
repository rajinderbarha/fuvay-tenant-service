# Matching Diagnostics Report (Part 4)

`/admin/home-services/matching-diagnostics` runs a **new** diagnostic on demand (POST `/v1/admin/home-services/matching/diagnostics`); it does not load a stored historical trace — there is no persisted "matching run" table/list to browse past runs. This is an honest limitation, not a bug: the endpoint is stateless per the API contract (`autoPriceOptionsApi.runMatchingDiagnostics`), and the page is explicitly framed as a live diagnostic tool ("Run provider-first matching for any service/area combination and see exactly why a provider was selected").

## Verified via real browser run (AC Repair / Split AC / LG / 141001 / Ludhiana)
- Shows selected provider: YES — "Demo AC Services" with score 75.0 and a per-factor breakdown (health_score 100, job_completion_score 50, rating_score 0, availability_score 100, service_match_score 100, distance_score 100, cancellation_score 100, capacity_score 100).
- Shows WHY selected: YES — `customer_visible_reason` text plus the internal score breakdown grid (admin-only, labeled "Final Score (admin-only)").
- Shows bookability checks: partially — the page shows "Canonical Sources" (Bookability Source: `canonical_provider_status`, Area Coverage Source: `normalized_service_area_coverage`, Availability Source: `tenant_availability_rules`, Pricing Source: `tenant_type_brand_pricing`) confirming which subsystem backed each check, but does not show a full pass/fail checklist inline on this page — that level of detail lives on the dedicated Bookability Checks verification (Part 6), which is a related but separate concern per spec scope.
- Shows pricing rule source: YES — "Pricing Source: tenant_type_brand_pricing" and the returned Low/Mid/High are traceable to the real `service_pricing_rules` row (600-950 admin range → 770/850/935 customer-facing).
- Shows no-match/excluded reason if applicable: YES — see Part 5 for the dedicated no-match run; when `excluded_providers` is non-empty, the page renders a dedicated "Excluded Providers" card with provider name + reason code badge (e.g. `ZIPCODE_NOT_COVERED`).
- No raw unformatted JSON as main UI: confirmed — every field is rendered into a labeled card/stat/badge component (`MiniStat`, `PriceTierCard`, badges), never a raw `<pre>` dump.
- Loading/empty/error states: loading is handled via the `useAction` hook's `.loading` flag (button shows a spinner via `Btn loading={...}`); before any run, the page shows just the form (no premature "no results" flash); error state renders a red-styled message with `requestId` appended when available.

Admin-level detail (internal_score numbers, raw source-key strings like `tenant_type_brand_pricing`) is acceptable per spec ("Admin-level detail is fine ... just must be organized/readable, not a raw dump") — confirmed organized, not a dump.

## Verdict
**PASS.** Diagnostics page is a genuine, organized, readable internal admin tool backed by a real live endpoint, not a raw JSON viewer.
