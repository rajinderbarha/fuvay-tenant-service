# HS5B — Remaining Blockers

1. **No frontend UI built for any of the 4 new feature areas**
   (break/lunch, exceptions/holidays, booking window, per-area
   coverage) — this sprint was entirely backend (schema + API +
   validation + live verification). The `/provider/availability` and
   `/provider/service-areas` pages were not modified.
2. **Permission-aware UI not implemented** — same gap as every prior HS
   sprint; backend authorization (`require_tenant_owner`) is real.
3. **Matching-engine consumption not traced** — the new matching-input
   readiness function is real and live-verified, but whether an actual
   customer-facing booking/matching engine exists and would consume it
   was not investigated. Explicitly documented as HS6 scope.
4. **Slot-capacity awareness incomplete** — `max_bookings_per_slot`/
   `max_jobs_per_day` are stored but not yet consumed by the matching-
   input preview function (it checks day/time window and breaks/
   exceptions, not concurrent booking counts).
5. **"Emergency booking policy gate" undefined** — the ticket mentions
   emergency booking "can only be enabled if policy allows" but no such
   policy exists elsewhere in the codebase; accepted as a plain tenant
   preference.

## What is solid and newly fixed this sprint
- All 3 missing schema pieces (break/lunch, exceptions/holidays,
  booking-window) now exist via a safe, idempotent, live-applied
  migration.
- Per-area type/brand coverage: found genuinely dead infrastructure
  (`tenant_service_area_services` existed but had zero routers) and
  wired it up for the first time, with real validation against catalog
  tables.
- A real matching-input readiness function was built and live-verified
  against exactly the 3 required scenarios (break-blocked, holiday-
  blocked, fully-valid).
- One real bug found and fixed mid-sprint (asyncpg date-binding in the
  exceptions endpoint).
- Zero regressions across 310 test executions this sprint.
