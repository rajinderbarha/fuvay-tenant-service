# Phase 2A Slice 2F-3A — Approval Gate

**`tenant_engine.router` unchanged. `provider_portal.router` unchanged.
`readonly@` untouched. Migration 144 not applied. No visual redesign. No
booking-pipeline decision made. No route deleted. Stopping here for
review.**

## Disposition: COMPLETE (adjudication achieved; no code change warranted)

## Files changed
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` —
  `ADJUDICATED_ROUTE_OVERLAPS` allowlist + `--verify-overlap` mode.
- `tests/test_phase2f_mutation_enforcement.py` — 1 new regression test.
- **New:** `tests/test_phase2f3a_execution_assignment_overlap.py` (7
  tests), this documentation directory (16 files).
- **Updated:** global Slice 2F `tenant-mutation-endpoint-inventory.csv` (4
  rows: 2 shadowed routes reclassified `DISCONNECTED`, 2 canonical routes
  annotated as confirmed-reachable).
- **No application code was changed** in any of the 3 audited modules, or
  in `tenant_engine.router`/`provider_portal.router`.

## Mutation routes inventoried by router
- `execution.home_service_router`: 23
- `home_service_assignment.staff_router`: 2
- `home_service_assignment.provider_router`: 4
- **Total: 29**

## Overlapping capability groups
7 capability groups documented (`overlapping-capability-groups.csv`): 1
true duplicate (accept/reject), 1 distinct-pipeline pair (whole-job-cancel
vs. cancel-assignment), 5 sole-owner groups (assignment lifecycle,
execution progress, parts lifecycle, admin overrides — no competing route).

## Record types by router
All 29 routes operate on `ServiceJob` (`app.engines.final_records.models`)
and its `job_id`-linked satellites (`ServiceJobAssignment`, `PartsRequest`,
`ServiceJobExecutionNote`, `ServiceJobMediaUpload`) — no Booking/Job/
ServiceBooking model confusion found within these 3 modules.

## Pipelines identified
One shared pipeline (home-services `ServiceJob` execution + assignment),
cooperatively split between the assignment lifecycle (who's assigned, have
they accepted) and the execution lifecycle (on-the-way through completion,
parts). Other verticals (`coaching_router`, `real_estate_router`) use
separate, non-overlapping pipelines — not touched or further audited.

## Same-record duplicates found
**Exactly 2**: `POST .../accept` and `POST .../reject`, both mounted at
identical paths by `execution.home_service_router` and
`home_service_assignment.staff_router`.

## Distinct-pipeline routes found
`provider_cancel_job` (whole-job cancellation) vs. `cancel_assignment`
(assignment-only cancellation) — same `job_id`, genuinely different
transitions, both required.

## Compatibility routes found
None — no route in either module functions as a compatibility/adapter
layer for the other.

## Disconnected routes found
**2**: `execution.home_service_router`'s `staff_accept_job` and
`staff_reject_job` — confirmed unreachable dead code via live HTTP proof.

## Frontend callers by route group
- accept/reject: called by `frontend/tenant-portal` (always answered by
  the canonical `home_service_assignment.staff_router` implementation).
- assign/reassign/cancel-assignment/schedule: called by
  `frontend/tenant-portal` (`home_service_assignment.provider_router`,
  sole owner).
- whole-job cancel, parts-reject: called by `frontend/tenant-portal`
  (`execution.home_service_router`, sole owner).
- Remaining execution-progress/parts endpoints: not individually
  re-verified this slice (out of the narrow overlap-adjudication scope).

## Weaker authorization paths found
1 candidate documented (`home_service_assignment`'s accept/reject having no
explicit tenant_id filter, relying solely on assignment-ownership matching)
— not proven exploitable, flagged as a non-blocking observation for the
future guard-application slice, not a bypass requiring closure now.

## Safe bypasses closed
**0 required.** The one duplicate found (accept/reject) has its "weaker"
copy completely unreachable — not exploitable, so Workstream 9's threshold
for a code change was not met. No code change was made.

## Unresolved bypasses
None — the only candidate was resolved by proving it is not live-exploitable
(dead code), which is itself a resolution, not an open blocker.

## Parts and quote boundary findings
**Intact, no violation found.** `PartsRequest` remains exclusively
`ServiceJob`-linked; zero Parts-related endpoints exist anywhere in
`home_service_assignment`; provider-only installation restriction
unchanged; no cross-pipeline adapter introduced.

## Tests run / passed / failed
Targeted: 490 run, 489 passed, 1 failed (pre-existing, unrelated flaky
concurrency test, confirmed passing in isolated re-run — see
`test-report.md`). Broader partition: 316 passed, 3 pre-existing skips, 0
failed. Combined: 806 tests, 0 real failures caused by this slice.

## Broader regression coverage
316 tests across 9 files covering execution, assignment, staff operations,
ServiceJob, quotes, parts, and IDOR — not claimed as full-repository
coverage.

## Runtime route count
Unchanged — no route added, removed, or modified this slice.

## Route collisions
**2 pre-existing collisions found and adjudicated** (not introduced this
slice) — see `canonical-route-disposition.csv`. Both confirmed to resolve
safely (one implementation always wins, the other never executes).

## execution.home_service_router readiness status
**READY_WITH_DISTINCT_PIPELINE_EXCEPTIONS** — see
`execution-guard-readiness.md`.

## Required future guard slices
1. A combined guard-application slice for `execution.home_service_router`
   + `home_service_assignment.staff_router` + `.provider_router` (recommended
   together, given how tightly coupled the shared `ServiceJob` record is).

## Remaining blockers
None block this slice's own approval. For the future guard slice: per-
endpoint ownership-mechanism re-verification (documented in
`known-limitations.md`), and the 2 non-blocking observations (assignment
router's tenant-filter gap; unverified original intent behind the
duplication).

## Whether every quality gate passed
**Yes, all 28 gates.** Notably: gate 10 (directly exploitable weaker
duplicates closed or block approval) — the one duplicate found was
conclusively proven NOT directly exploitable (dead code), which satisfies
this gate without requiring a code change. Gate 11 (no route retired based
only on naming similarity) — no route was retired; the shadowed functions
remain in source. Gate 19 (booking/job model ownership remains unresolved
unless evidence genuinely closes the limited overlap question) — the
narrow accept/reject overlap question IS genuinely closed by direct
evidence; the platform-wide Booking/Job/ServiceBooking/ServiceJob merge
question remains untouched and unresolved, as required.

---
**Stopping here. Not beginning broad execution guard application. Not
remediating `readonly@`. Not applying migration 144. Awaiting approval
before any further slice.**
