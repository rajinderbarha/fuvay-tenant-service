# HS6 — Area/Availability Filter Report

## Confirmed real
`select_best_provider()`'s base candidate query joins
`TenantServiceArea`, filters `is_active=true` and city match, and gives
an exact-zipcode match a scoring bonus (`distance_score`) — real,
zipcode/city-aware filtering, confirmed via source read this sprint.

`_passes_full_eligibility_gate()` checks
`provider_availability_rules` has at least one active row — real
availability gate, confirmed.

## Not re-verified this sprint
- Whether the area filter also checks per-area **service/type/brand
  coverage** (the `tenant_service_area_services` table, extended and
  wired to a real endpoint for the first time in HS5B this session) —
  the matching engine's eligibility gate checks `provider_enabled_
  offerings.supported_type_ids/supported_brand_ids` instead, a
  **different, JSON-array-based data model** than
  `tenant_service_area_services`. This is a second confirmed
  data-model inconsistency (see Bookability Filter report for the
  first) — the HS5B per-area coverage table this session just built is
  **not consumed by the real matching engine at all**.
- Whether availability filtering checks the **requested date/time**
  against `provider_availability_rules.day_of_week`/`start_time`/
  `end_time` (and the new HS5B break/exception fields) — the
  eligibility gate only checks "at least one active rule exists,"
  not "available at the specific requested time." This is a real gap:
  HS5B's `get_tenant_home_services_matching_inputs()` preview function
  does this time-specific check, but the actual matching engine used by
  live bookings does not call it.

## Verdict
Area filtering: **real, city/zipcode-aware**. Availability filtering:
**real but coarse** (existence-only, not time-specific). Two real,
confirmed data-model gaps found (per-area type/brand coverage and
time-specific availability are not consumed by the live matching
engine) — documented, not fixed this sprint given the scope of
unifying them safely.
