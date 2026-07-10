# HS5 — Matching Input Readiness Report

## Purpose
Verify service area and availability data is available to provider
matching APIs, or document the gap for HS6.

## Findings
- `tenant_service_areas` (real table, zipcode/city/zone-scoped) is
  queried directly by `_evaluate_provider_bookability` — confirmed
  queryable and real.
- `provider_availability_rules` (real table, day/time-scoped) —
  confirmed queryable and real, now with valid time-range guaranteed
  (this sprint's fix).
- Whether the actual **customer-facing provider matching engine**
  (referenced in the ticket as needing "customer zipcode → tenant active
  service areas → coverage → availability → capacity → bookability")
  currently queries these same tables was **not verified this sprint** —
  locating and reading the matching engine's source was out of this
  sprint's time budget (HS5 focused on the tenant-facing setup pages and
  the availability validation bug).

## Recommendation for HS6
A dedicated sprint should trace the real matching engine's query path
end-to-end and confirm it (a) filters by `tenant_service_areas` for the
customer's zipcode, (b) checks `provider_availability_rules` for the
requested time slot, and (c) respects the `is_bookable` flag from
`provider_visibility_statuses` (fixed in HS4B) before returning a
provider as a match candidate. This was not confirmed this sprint.

## Verdict
Matching input readiness: **data exists and is real**, but end-to-end
matching-engine consumption was **not verified this sprint** —
documented as a clear scope handoff to HS6 rather than assumed.
