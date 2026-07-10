# No-Match / Excluded Provider Case Report (Part 5)

## Scenario used
Unsupported zipcode `999999`, city "Nowhere", same AC Repair master_service_id/category_id. This is a safe, read-only diagnostic call — no data mutation, no real customer/tenant affected.

## Real API response (via curl, then reconfirmed in browser)
```json
{
  "eligible_provider_count": 0,
  "candidate_provider_count": 0,
  "excluded_provider_count": 0,
  "excluded_providers": [],
  "selected_provider": null,
  "top_candidates": [],
  "price_options": null,
  "area_market_comparison": null,
  "bookability_source": "canonical_provider_status",
  ...
}
```
`request_id` present in the response envelope (`meta.request_id`, e.g. `req_f54448423fdb`).

## Browser-rendered result
- No provider selected: YES — the page renders the dedicated "No eligible provider found" card (XCircle icon, red-tinted) with the explanatory copy: "0 candidate(s) found in the area, all excluded by eligibility gates (bookable, coverage, technician, availability, pricing, package, credits, or deposit)."
- Reason is clear: YES — human-readable sentence, not an error code dump.
- `request_id` visible: the diagnostics page does not print `request_id` on a *successful* (200) no-match response since it's a valid empty-result response, not an error — this mirrors Part 3's finding (request_id only shown on the `SectionError` error path, not on successful-but-empty results). Documented as the same minor, non-blocking gap noted in Part 3/4.
- Retry/change-filters action: the form remains fully editable in place (all inputs stay populated/editable, "Run Diagnostics" button remains available to retry with different filters) — functionally equivalent to a retry action, though there is no dedicated "Retry" or "Clear Filters" button labeled as such.
- No crash: confirmed via Playwright — page renders cleanly, no console errors observed, no raw backend exception/traceback text present in body (`playwright` assertion `not.toMatch(/traceback|exception|internal server error/)` passed).

## Secondary real observation
When a real service-type/brand combo IS in the area but zipcode isn't covered, the backend correctly returns a populated `excluded_providers` array with a specific reason code (observed live: `ZIPCODE_NOT_COVERED` for "Demo AC Services" when Split AC + LG were specified together with an uncovered zip in one intermediate test run) — proving the exclusion-reason mechanism is real and specific, not a generic catch-all.

## Verdict
**PASS.** No-match path is clean, human-readable, non-crashing. Minor gap (no request_id shown on a non-error empty result) noted but does not rise to NOT_READY.
