# HS5 — Remaining Blockers

1. **Break/lunch time not supported** — `provider_availability_rules`
   has no `break_start`/`break_end` columns; would need a migration.
2. **Exceptions/holidays feature doesn't exist** — no data model, no
   endpoints found anywhere in the codebase for date-specific
   closures.
3. **Booking-window settings (minimum notice, advance-booking days,
   buffer time) not modeled** as distinct configurable fields — only
   `slot_duration_minutes` exists per availability rule.
4. **Service/type/brand coverage-by-area not independently re-verified
   this sprint** — confirmed present in an earlier sprint's
   certification, but not live-tested again this sprint (time budget
   went to the availability validation fix).
5. **Matching-engine consumption of service-area/availability data not
   traced this sprint** — the tables are real and queryable (confirmed
   via the HS4B bookability fix), but whether the actual customer-facing
   matching engine uses them was not verified. Explicitly handed off to
   HS6 rather than assumed.
6. **Permission-aware UI not implemented** — same gap as every prior HS
   sprint; backend authorization (`require_tenant_owner`) is real.
7. **No dedicated availability test file existed before this sprint** —
   now partially covered by the new HS5 test file, but full CRUD/
   validation coverage (as opposed to the specific time-range bug fixed
   here) wasn't built.

## What is solid
- Service area package-limit enforcement and duplicate-area rejection:
  confirmed real, server-side, unchanged and re-verified (44/44
  regression tests passing).
- Availability time-range validation: **real bug found and fixed this
  sprint**, live-verified (create and update paths both validated,
  partial updates correctly merge with existing values before
  validating).
- Bookability already treats both service areas and availability as
  hard gates (fixed in HS4B, re-confirmed intact this sprint).
- 0 forbidden labels, 0 old menu items, TypeScript clean, 0 regressions
  across 192 total test executions (16 new + 176 broader sweep).
