# Phase 2A Slice 2F-3A — Execution/Assignment Overlap Adjudication — Implementation Summary

## Mission
Resolve the confirmed overlap between `execution.home_service_router`,
`home_service_assignment.staff_router`, and
`home_service_assignment.provider_router` before any broad mutation-guard
application to `execution.home_service_router`, per Slice 2F's original
finding that this overlap remained un-adjudicated.

## Central finding
Of the 29 mutation routes across all 3 modules, **exactly 2 (method, path)
pairs are genuinely duplicated**: `POST /v1/staff/service-jobs/{job_id}/accept`
and `.../reject`, mounted identically by both
`execution.home_service_router` (`staff_accept_job`/`staff_reject_job`) and
`home_service_assignment.staff_router` (`accept_job`/`reject_job`). Both
operate on the same `ServiceJob` record via the same `job_id`, for the same
staff/technician persona, performing the same business transition.

Live proof (HTTP call via pytest + mocked DB): `home_service_assignment.staff_router`'s
version answers every request to this path — confirmed via its unique
`engine_id: "assignment"` and error code `STAFF_JOB_NOT_ASSIGNED_TO_USER` in
the response. This is because `app/main.py` registers
`home_service_assignment`'s routers (Sprint 20) BEFORE
`execution.home_service_router`'s (Sprint 21), and Starlette/FastAPI route
matching is first-match-wins. **`execution.home_service_router`'s copies at
this path are 100% unreachable dead code.**

Every other apparent similarity (e.g. `provider_cancel_job` vs
`cancel_assignment`) was traced to a genuinely distinct business transition
on the same `ServiceJob` record (whole-job cancellation vs.
assignment-only cancellation) — confirmed by reading both service methods,
not assumed from naming.

## Why no code change was made
Workstream 9's 7-point test for applying a code change requires the weaker
route to be materially, exploitably weaker. Here, the "weaker" route
(`execution.home_service_router`'s copies) is not merely weaker — it is
**completely unreachable**, so it poses zero live security risk regardless
of its own guard composition. No code change was warranted or made to
either implementation. Per the mission's explicit constraint ("apply code
changes only when a directly exploitable weaker duplicate route is
conclusively proven"), the correct action was thorough documentation plus
regression tests locking in the current (correct) behavior — not a route
deletion, redirect, or guard change.

## What was added
1. **7 new tests** (`tests/test_phase2f3a_execution_assignment_overlap.py`)
   proving: which implementation answers the shared path (live HTTP);
   the shadowed functions still exist in source (must not be deleted
   without a fresh adjudication); `app/main.py`'s registration order still
   matches the documented finding; `provider_cancel_job`/`cancel_assignment`
   remain distinct capabilities; the Parts-request boundary remains intact.
2. **1 new regression test** in the existing
   `tests/test_phase2f_mutation_enforcement.py` proving the live route walk
   finds exactly the 2 adjudicated overlaps and no others.
3. **Inventory tooling extension**
   (`scripts/workflow_rearchitecture/inventory_mutation_routes.py`):
   `--verify-overlap MODULE [MODULE ...]` — finds every (method, path) pair
   mounted from more than one of the given modules and fails closed unless
   each is present in a new `ADJUDICATED_ROUTE_OVERLAPS` allowlist. Run
   against the 3 modules: **exit 0, 2 overlaps found, both adjudicated.**

## Readiness disposition for `execution.home_service_router`
**READY_WITH_DISTINCT_PIPELINE_EXCEPTIONS** — see
`execution-guard-readiness.md` for full reasoning. The overlap that could
have blocked broad guard application is resolved; a few narrower,
per-endpoint ownership-verification items remain for that future slice to
do itself (documented in `known-limitations.md`, not blocking).
`home_service_assignment.staff_router`/`provider_router` also need their
own guard-application work — recommended to combine with
`execution.home_service_router`'s slice given how tightly coupled the
shared `ServiceJob` record is.

## Files changed
- **Modified:** `scripts/workflow_rearchitecture/inventory_mutation_routes.py`
  (`ADJUDICATED_ROUTE_OVERLAPS` + `--verify-overlap` mode),
  `tests/test_phase2f_mutation_enforcement.py` (1 new regression test).
- **New:** `tests/test_phase2f3a_execution_assignment_overlap.py` (7
  tests), this documentation directory (16 files).
- **No application code was changed** — `app/engines/execution/`,
  `app/engines/home_service_assignment/`, `app/engines/tenant_engine/`, and
  `app/engines/provider_portal/` are all byte-for-byte unchanged from
  before this slice.

## Test results
490 targeted (1 pre-existing, unrelated flake, confirmed by isolated re-run)
+ 316 broader-partition (3 pre-existing skips) = 806 tests, 0 real failures.
