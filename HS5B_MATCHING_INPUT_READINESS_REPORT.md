# HS5B — Matching Input Readiness Report

## Implemented: `get_tenant_home_services_matching_inputs()`
A real, DB-backed function (not the full HS6 provider-matching/ranking
engine — that's explicitly out of scope this sprint) that answers
exactly the ticket's required question set for a hypothetical customer
request:

```json
{
  "zipcode_covered": bool,       // tenant_service_areas
  "service_covered": bool,       // tenant_service_area_services
  "type_covered": bool,          // tenant_service_area_services.service_type_id
  "brand_covered": bool,         // tenant_service_area_services.brand_id
  "available_at_requested_time": bool,  // provider_availability_rules
  "blocked_by_break": bool,      // break_start_time/break_end_time
  "blocked_by_exception": bool,  // tenant_availability_exceptions
  "booking_window_valid": bool,  // tenant_booking_window_settings
  "is_bookable": bool,           // AND of everything + _evaluate_provider_bookability (HS4B)
  "blocking_reasons": [...]
}
```

Exposed via `POST /v1/provider/home-services/matching-inputs/preview`.

## Live-verified — all 3 required scenarios
1. **Blocked by break**: requested Tuesday 14:30 (inside the 14:00–15:00
   break) → `is_bookable: false`, `blocked_by_break: true`,
   `blocking_reasons: [BLOCKED_BY_BREAK]`, all coverage checks
   correctly `true` (proving the block is specifically the time, not a
   coverage gap).
2. **Blocked by holiday**: requested during the real "Independence Day"
   full-day exception created this sprint → `is_bookable: false`,
   `blocked_by_exception: true`, real reason message including the
   exception's actual `reason` field ("You are closed on this date:
   Independence Day").
3. **Fully valid**: requested Tuesday 11:00 (open day, outside break,
   real Split AC+LG coverage, real zipcode) → `is_bookable: true`,
   `blocking_reasons: []`.

## Explicit handoff to HS6
This function is a **readiness preview**, not the real matching/ranking
engine. HS6 must:
1. Confirm the actual customer-facing booking-creation flow queries
   these same tables (not verified this sprint — no time to trace the
   real matching engine's existing code path, if one exists).
2. Extend this into ranking/scoring across multiple candidate tenants
   (this function only evaluates one tenant at a time).
3. Handle concurrent-booking slot capacity (`max_bookings_per_slot`/
   `max_jobs_per_day` are stored but not yet consumed by this preview
   function — a fully slot-capacity-aware version needs those wired in).

## Verdict
Matching input readiness: **real, DB-backed function built and
live-verified against 3 required scenarios** (break-blocked, holiday-
blocked, fully-valid). Scope explicitly limited to a single-tenant
readiness check per the ticket's "do not build full provider matching
here" instruction — HS6 requirements clearly documented above.
