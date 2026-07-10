# Provider Matching Browser Report (Part 3, CRITICAL)

## What the real `/admin/home-services/provider-matching` page actually is

Reading `app/admin/home-services/provider-matching/page.tsx`: this route is a **configuration/explainer page**, not an interactive "run a match" test tool. It shows:
- Page header + subtitle explaining ServiceOS auto-selects one provider (customers never pick manually) — real copy, no forbidden "manual bargain" language.
- A live config card (`autoPriceOptionsApi.getConfig()` → `/v1/admin/home-services/config`) showing "Provider-first matching: Enabled" / "Customer manual provider selection: Disabled" — real API-backed status, not hardcoded.
- A static "Ranking Factors" card with fixed platform-constant weights (Health Score 20%, Job Completion 20%, Rating 15%, Availability 15%, Service Match 10%, Area Match 10%, Cancellation 5%, Capacity 5% = 100%) — labeled as fixed constants, "Reset Defaults" button correctly disabled with a tooltip explaining why (no persisted override exists).
- Two links to `/admin/home-services/matching-diagnostics` (Preview Match / View Diagnostics) — this is where the actual matching search/test panel with selectors, zip/city, run button, and results (selected provider, price options, bookability) lives. This matches the spec's actual system design: provider-matching = explainer/config, matching-diagnostics = the real test tool. Verified this split by reading both page files before assuming the spec's illustrative "search panel on provider-matching" description was literal.

## Real matching scenario run (via Matching Diagnostics, in real Chrome browser, Playwright)

Filled: Category ID (AC Repair's category, prefilled), Master Service ID = AC Repair (prefilled), City = Ludhiana (prefilled), Zipcode = 141001 (prefilled), Type ID = Split AC (`c86dfcf3-53bd-4d83-bf0b-51257f382652`), Brand ID = LG (`64a3b25f-23aa-4639-8baf-f67def0f60db`). Clicked "Run Diagnostics".

Result (both via direct `curl` to `/v1/admin/home-services/matching/diagnostics` and via the rendered UI):
- `selected_provider.provider_name = "Demo AC Services"` — appears with a green checkmark, name, customer-visible reason ("Best matched provider based on service coverage, availability, quality, and completion history."), and public badges (Verified, High Completion).
- `price_options`: Low ₹770 / Mid ₹850 / High ₹935 — rendered as three PriceTierCards labeled "Low Mid High" under a "Low / Mid / High Price Preview" section header.
- `payment_mode: "customer_pays_provider_directly"` returned by the API (not directly rendered as a label on this admin diagnostics screen — the payment-mode-as-customer-safe-copy check applies more directly to the customer-app and to the Operations job detail, both of which DO render "Customer pays provider directly", see Part 7/12).
- Provider card renders **before** the price options card in DOM order (selected-provider Card appears above the Low/Mid/High Card in the JSX) — confirmed via page source order and screenshot.
- `request_id` returned by the API (`req_79e0e816c1bb` on this run) — not currently surfaced in the successful-result UI (only shown on error state via `SectionError`). This is a minor, non-blocking gap: request_id is available in the API contract but not displayed for successful runs.
- No raw JSON dump as primary UI — all fields are rendered into labeled cards/badges/stat tiles.

## Verdict
**PASS.** Real end-to-end matching works correctly: single selected provider, correct Low/Mid/High, provider-before-price ordering, no raw JSON. Minor gap: request_id not shown on success (only on error) — does not meet the bar for NOT_READY since the data contract genuinely includes it and errors do show it.
