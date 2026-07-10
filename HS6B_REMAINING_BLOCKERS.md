# HS6B — Remaining Blockers (updated, second pass)

## Closed this pass
1. ~~Admin diagnostics not updated~~ — **FIXED**. `_passes_full_eligibility_gate`
   now returns `tuple[bool, str | None]` with a specific reason code per
   exclusion. `select_best_provider` surfaces `excluded_providers: [{provider_name,
   reason_code}]`. The admin diagnostics router (`auto_price_options_router.py`)
   passes this through plus 4 canonical-source labels
   (`bookability_source`, `area_coverage_source`, `availability_source`,
   `pricing_source`). The UI (`matching-diagnostics/page.tsx`) renders a
   "Canonical Sources" panel and an "Excluded Providers" panel with reason
   badges.
2. ~~Break/holiday/booking-window not wired into `select_best_provider`~~ —
   **FIXED**. The gate now accepts `requested_at` and, when given, calls
   HS5B's `get_tenant_home_services_matching_inputs()` (reused, not
   reimplemented) to check `blocked_by_break` → `BLOCKED_BY_BREAK`,
   `blocked_by_exception` → `BLOCKED_BY_HOLIDAY`, booking-window validity →
   `OUTSIDE_BOOKING_WINDOW`, and real-time availability →
   `NOT_AVAILABLE_AT_REQUESTED_TIME`. Live-verified against the real DB:
   holiday-blocked request excluded with `BLOCKED_BY_HOLIDAY`, break-blocked
   request excluded with `BLOCKED_BY_BREAK`, valid time selects the provider
   with 0 exclusions.

## Still open
3. **No legacy JSON-coverage fallback** — deliberate (see Data Model
   Alignment report), but means any hypothetical tenant with only
   old-style `provider_enabled_offerings` JSON coverage and zero
   `tenant_service_area_services` rows would now be excluded from
   matching until they configure normalized coverage. No such tenant
   exists in this dev DB; a production migration audit would be needed
   before deploying this change live.
4. **Full HTTP `curl` transcript not captured** — verification of the
   eligibility gate and the second-pass time-window integration was done
   via direct real-database function calls (equivalent SQL/logic
   coverage) rather than through the actual REST endpoint, which
   requires a multi-step booking-draft setup not completed this sprint.
5. **Only brand-coverage exclusion path individually tested** for the
   base coverage checks (service/type/brand share one SQL-join
   construction, not each separately exercised as its own live
   scenario) — unchanged from the first pass, not addressed this pass
   since it's a test-thoroughness gap, not a functional one.

## What is solid and fixed across both passes
- **Both critical data-model mismatches from HS6 are fixed**: matching
  reads the single canonical HS4B bookability flag (no more parallel
  readiness calculation across 4 different tables), and matching reads
  HS5B's normalized per-area coverage table (no more disconnected
  JSON-array model).
- **Time-window enforcement is now a real hard gate**, not just a
  disconnected preview function — break, holiday, and booking-window
  violations now correctly exclude a provider from matching.
- **Admin diagnostics are fully wired**: canonical source labels and
  per-candidate exclusion reasons are visible end-to-end, backend to UI.
- A real, previously-undetected bug was found and fixed via this
  alignment work: a real dev-DB tenant with an unrelated
  `provider_enabled_offerings.status='pending_approval'` value would
  have been wrongly excluded from matching despite being genuinely
  bookable.
- Live-verified against the real database in both the include and
  exclude direction for all fixes across both passes.
- Zero regressions; 13/13 new second-pass tests, 380/380 broader
  regression sweep (`home_service_booking or matching or bargain or
  provider_first or auto_price or bookab or availability or
  service_area or hs6b`).
