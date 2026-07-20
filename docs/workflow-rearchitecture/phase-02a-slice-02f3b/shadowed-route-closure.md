# Shadowed Route Closure — Workstream 2

## What was done
Removed only the `@staff_router.post("/{job_id}/accept")` and
`@staff_router.post("/{job_id}/reject")` decorators from
`app/engines/execution/home_service_router.py`'s `staff_accept_job` and
`staff_reject_job` functions. The function bodies were left completely
intact and undeleted.

## Why this is safe
- Both functions were **already 100% unreachable** (confirmed live in
  Slice 2F-3A via HTTP call) — `home_service_assignment.staff_router`'s
  `accept_job`/`reject_job` always answered these paths because that
  module is imported/registered before `execution.home_service_router` in
  `app/main.py`.
- Removing the decorator does not change which code executes for any real
  request — it only removes the OpenAPI schema noise of a phantom,
  never-reachable second operation, and eliminates any future risk that a
  refactor of `app/main.py`'s import order could silently start routing
  traffic to the weaker execution-router copy instead.
- The canonical paths (`/v1/staff/service-jobs/{job_id}/accept`,
  `.../reject`) are completely unchanged — still served by
  `home_service_assignment.staff_router`, still at the same URL.
- No frontend or API client changes were needed — they call the path, not
  a specific module; the path is unchanged.

## Verification
- `MSYS_NO_PATHCONV=1 PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-overlap app.engines.execution.home_service_router app.engines.home_service_assignment.staff_router app.engines.home_service_assignment.provider_router` → **exit 0, 0 overlaps found** (was 2 before this slice).
- `app.openapi()["paths"]["/v1/staff/service-jobs/{job_id}/accept"]` and
  `.../reject` each show exactly one POST operation.
- Live HTTP test (`TestShadowedRouteDecoratorsRemoved::test_canonical_assignment_implementation_still_answers`)
  confirms `home_service_assignment.staff_router` still answers
  (`engine_id: "assignment"`).
- `execution.home_service_router.staff_accept_job` and `.staff_reject_job`
  remain importable, undeleted (`hasattr` regression test).

## Runtime route count impact
`execution.home_service_router`'s mounted mutation count drops from 23 to
**21** (2 fewer — the two now-undecorated functions are no longer FastAPI
routes at all). This is the explicitly expected and documented "-2" per the
brief's own instruction: "a total runtime route-count reduction of two is
acceptable and expected, provided it is explicitly documented."

## Final disposition
The route-order dependency is **fully removed**, not merely
"acknowledged" — there is no longer a second route registered at these
paths for `app/main.py`'s import order to matter for. This is why the
slice can report **SECURITY_CLOSED** rather than
**SECURITY_CLOSED_WITH_ROUTE_ORDER_DEPENDENCY** for this specific finding.
