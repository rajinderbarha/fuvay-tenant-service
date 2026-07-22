# Regression Report

## No application authorization behavior changed
Confirmed — this slice's only changes are: (1) 5 rows corrected in `tenant-mutation-endpoint-inventory.csv` (1 removed, 4 reclassified), (2) 1 recount-test assertion updated. No file under `app/` was modified.

## Suite executions
| Suite | Result |
|---|---|
| Canonical coverage recount tests (`test_phase2f14a_field_ops_alternate_route_and_coverage.py`, updated) | 30 passed |
| Runtime inventory tests (`--verify-module` across 13 modules, executed manually this slice) | 11 exit 1 (genuinely unprotected, expected), 2 exit 0 (reclassified, expected) |
| Duplicate-route tests | `test_no_duplicate_rows`, unchanged, passing |
| Persona classification | `persona-reclassification.csv`, documentation-only, cross-checked against runtime |
| Remaining-row completeness | `recount-test-report.md` |
| Module-grouping | `module-grouping-summary.csv`, documentation-only |
| Ranking/selection consistency | `non-selected-module-queue.csv` + `selected-next-module.md`, cross-checked to sum to exactly 36 |
| Existing Slice 2F-15C tests (Booking) | included in full sweep below, unaffected |
| Existing Slice 2F-16 tests (quote_checklist) | included in full sweep below, unaffected |
| Existing Slice 2F-16A tests (quote_checklist/invoice lineage) | included in full sweep below, unaffected |
| Existing field_ops verifier tests | unaffected, re-confirmed 28/28 and 6/6 |
| Existing Booking verifier tests | unaffected, re-confirmed 11/11 |
| Existing quote-checklist verifier tests | unaffected, re-confirmed 11/11 + 3/3 |

## Full broad partition sweep
```
python -m pytest -q -k "field_ops or checklist or quote or booking or invoice" [+ live-environment test files excluded]
1032 passed, 3 skipped, 10010 deselected, 47 warnings
```
Zero failures attributable to this slice.

## Live-environment exclusions (reported separately, pre-existing, unrelated)
`test_final_l5_04c_matching_entitlement.py` (2 tests), `test_module_l5_35_staff_app_jobs_api.py` (1 test), `test_module_l5_13_reviews.py` (1 test, error) — all fail with `ConnectionRefusedError`/live-server dependency errors unrelated to this slice's CSV/test-assertion-only changes.
