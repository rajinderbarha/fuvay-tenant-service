# Regression Report

## New tests
`tests/test_phase2f15b_booking_creation_provenance_and_customer_dependency.py` — 13/13 passing:
- Exact-creation-provenance source invariants (2)
- Later-customer-activity tests (2)
- Missing-history legacy tests (3)
- Customer dependency tests (4)
- Persona/runtime-tool agreement (2)

## Existing tests fixed
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount` — 2 tests hardcoded the prior canonical figures (221 total / 174 protected). Updated to the corrected canonical figures (**220 total / 179 protected**) reflecting: (a) `booking_preflight` physically removed from the canonical CSV rather than left as a `FALSE_POSITIVE`-labeled row (this also satisfies `test_no_false_positive_rows`, which asserts no canonical row's `guard_status` contains the string `FALSE_POSITIVE` — a pre-existing invariant this slice's initial approach violated and then corrected by removing the row instead of relabeling it), and (b) the 5 booking.router routes fixed in Slice 2F-15A. No other pre-existing test required modification.

## Suite executions (all overlapping, no live-environment exclusions)
| Suite | Result |
|---|---|
| `test_phase2f15b_booking_creation_provenance_and_customer_dependency.py` (new) | 13 passed |
| `test_phase2f14a_field_ops_alternate_route_and_coverage.py` (coverage recount, fixed) | 30 passed |
| Existing Slice 2F-15 tests (`test_phase2f15_booking_customer_identity_and_confirmation.py`) | included in full sweep below, unchanged, passing |
| Existing Slice 2F-15A tests (`test_phase2f15a_booking_provenance_and_remaining_routes.py`) | included in full sweep below, unchanged, passing |
| Existing Booking tests (`test_step4_booking.py`) | included in full sweep below, unchanged, passing |
| Existing conversion/checklist/catalog tests (`test_checklist_system.py`, `test_service_catalog.py`) | included in full sweep below, unchanged, passing |
| Existing field_ops relationship tests (2F-14D/E/F/G series) | included in full sweep below, unchanged, passing |
| `field_ops.router` runtime verification | exit 0, unchanged |
| `field_ops.staff_router` runtime verification | exit 0, unchanged |
| Coverage recount verification (runtime persona breakdown) | exit 0, matches documentation |

## Full broad partition sweep
```
python -m pytest -q -k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate or coaching or invoice or payment or commission or parts_request or booking"
1726 passed, 9 skipped, 9288 deselected, 49 warnings
```
Zero failures (up from 1713 passed at the 2F-15A gate: +13 new tests). The `9 skipped` are pre-existing skips unrelated to this slice.

## Live-environment exclusions
No live server / live database verification performed this slice — all verification is unit tests (mocked `AsyncSession`) plus static/executed runtime route-introspection, consistent with every prior slice. Reported honestly, not counted as live-environment passing.
