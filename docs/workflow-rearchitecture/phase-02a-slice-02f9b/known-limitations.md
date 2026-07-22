# Known Limitations — Slice 2F-9B

1. **No component-level (rendered-DOM) test harness exists in
   `tenant-portal`** — this app has no jest/vitest/testing-library
   configured (same pre-existing gap noted in Slice 2F-6B). Verification
   of the control-visibility logic is therefore at the helper-function
   level (`canOfferProviderComplaintResolution`, 22 direct assertions)
   plus manual source-level review of how the page wires that helper into
   the button/modal/submit-handler conditions (`resolution-control-changes.md`),
   not a rendered-component snapshot/interaction test. This mirrors the
   established, documented testing approach for this app across all
   prior slices.

2. **`next lint` not verified** — pre-existing environment/tooling gap,
   unchanged from every prior slice.

3. **The deep-link/stale-state review (Workstream 6) is a structural +
   source-level analysis, not an end-to-end browser test** — no E2E test
   runner (Playwright/Cypress) is configured for this app. The analysis
   concludes there is no query-parameter or URL-based modal-opening path
   to even attempt bypassing, which is a stronger guarantee than a
   runtime test of one, but it was not independently exercised in a
   browser.

4. **The unresolved `provider_add_response` resolved/settled product
   question remains open**, unchanged from Slice 2F-9A — not decided,
   not touched.

5. **`complaints.customer_router`'s own authorization gap** remains open
   and out of scope for this slice.
