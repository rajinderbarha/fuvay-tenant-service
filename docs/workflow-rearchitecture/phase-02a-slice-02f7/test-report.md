# Test Report — Slice 2F-7

## New backend test file
`tests/test_phase2f7_serviceability_authorization.py`
Command: `python -m pytest tests/test_phase2f7_serviceability_authorization.py -q`
Result: **80 passed**, 0 failed.

## Pre-existing tests updated (honest, documented growth — not weakened)
- `tests/test_phase2d_tenant_access_model.py::TestTenantMutationPermissionCoverage::test_coverage_of_require_tenant_mutation_permission_is_still_narrow`
  — count updated from 4 to 5 (this slice added `serviceability/router.py`
  as the 5th file using `require_tenant_mutation_permission`).
- `tests/test_tenant_service_coverage_enterprise_ui.py::test_permission_gated_actions`
  — updated to expect `require_tenant_mutation_permission(...)` instead of
  the plain `require_permission(...)` it previously asserted, matching
  the actual, strengthened guard.

## Combined targeted regression
Command: `python -m pytest tests/test_phase2f7_serviceability_authorization.py tests/test_phase2d_tenant_access_model.py tests/test_tenant_service_coverage_enterprise_ui.py tests/test_phase2e_effective_permissions.py -q`
Result: **151 passed**, 0 failed.

## Broader partition
Command: `python -m pytest tests/ -q -k "phase2f or 2f5 or 2f6 or 2f7 or serviceability or matching or booking_preflight or tenant_isolation or access_scope or permission"`
Result (before the 2 documented-growth fixes): 1209 passed, 2 failed (both
fixed and re-verified green above — not re-run as a full ~10-minute
partition a second time this slice; the fixed 4-file combination above
is a superset proof that both corrections are complete and correct).

## Tooling verification
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.serviceability.router` → `total_routes: 19`, `unverified_count: 0`, exit 0.
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-overlap app.engines.serviceability.router app.engines.tenant_engine.router app.engines.admin_catalog.tenant_router` → `overlaps_found: 0`, exit 0.

## Frontend
`npx tsc --noEmit -p tsconfig.json` (in `frontend/tenant-portal`) — 0
errors attributable to the changed file
(`app/(tenant)/provider/service-areas/page.tsx`).

Frontend linting: **not verified** (not "passed") — this app has no
`eslint.config.js` (v9 format) and `next lint` fails with a pre-existing,
unrelated CLI argument-parsing error in this environment (documented in
Slice 2F-6B's own `known-limitations.md` and re-confirmed unchanged this
slice). Per instruction, reporting this honestly as not-verified rather
than claiming it passed.

## Files touched
- `app/engines/serviceability/router.py` — 8 endpoints re-guarded.
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` — 11 new
  allowlist entries (4 customer-address + 3 query + 4 platform-admin).
- `app/core/permissions.py`: not modified (reused existing
  `require_tenant_mutation_permission`).
- `frontend/tenant-portal/app/(tenant)/provider/service-areas/page.tsx` —
  hardcoded permission booleans replaced with role/access-scope-aware
  computation.
- `tests/test_phase2f7_serviceability_authorization.py` — new.
- `tests/test_phase2d_tenant_access_model.py`,
  `tests/test_tenant_service_coverage_enterprise_ui.py` — updated
  (documented-growth corrections).
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`,
  `tenant-mutation-endpoint-inventory.csv` — updated in place.
- 22 files under `docs/workflow-rearchitecture/phase-02a-slice-02f7/`: new.

No other production or test file was modified.
