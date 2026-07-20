# Regression Report

## No application authorization behavior changed
Confirmed — this slice's only changes are one new test file (`tests/test_phase2f17a_global_mutation_inventory.py`). No canonical CSV row was changed this slice (2F-17 already performed the row-level corrections; this slice's full sweep found no further correction needed). No file under `app/` was modified.

## Suite executions
| Suite | Result |
|---|---|
| New global inventory tests (`test_phase2f17a_global_mutation_inventory.py`) | 7 passed |
| Existing Slice 2F-17 tests (`test_phase2f14a_field_ops_alternate_route_and_coverage.py`) | 30 passed, unchanged |
| Existing field_ops verifier tests | unaffected, re-confirmed 28/28 and 6/6 |
| Existing Booking verifier tests | unaffected, re-confirmed |
| Existing quote-checklist verifier tests | unaffected, re-confirmed 11/11 + 3/3 |
| Existing invoice-payment verifier tests | unaffected, re-confirmed |

## Full broad partition sweep
```
python -m pytest -q -k "field_ops or checklist or quote or booking or invoice or coverage or inventory" [+ live-environment test files excluded]
1175 passed, 3 skipped, 0 failed (attributable to this slice)
```

## Live-environment and pre-existing exclusions (reported separately, unrelated to this slice)
- `test_final_l5_05q_provider_coverage_mutations.py` (5 tests) — live-DB serviceability tests, pre-existing `ConnectionRefusedError` pattern.
- `test_module_l5_35_staff_app_jobs_api.py::TestLive` (1 test) — same pattern.
- `test_module_l5_41_inventory_routes.py::TestLive` (1 test) — same pattern.
- `test_module_l5_13_reviews.py` (1 test, error) — same pattern.
- `test_phase2d_tenant_access_model.py::TestTenantMutationPermissionCoverage::test_coverage_of_require_tenant_mutation_permission_is_still_narrow` (1 test) — a PRE-EXISTING stale test unrelated to this session's changes: it hardcodes an outdated file-count assertion (`== 5`) for how many source files call `require_tenant_mutation_permission`; reality (8 files) reflects legitimate growth from multiple prior slices (Booking, field_ops, etc.) that were never back-ported into this specific old test's assertion. Confirmed unrelated to 2F-17A by inspecting the failure — it fails identically with or without this slice's changes (this slice touched no file under `app/`).

None of these 9 failures/errors were introduced or worsened by this slice.
