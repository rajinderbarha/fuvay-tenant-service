# Regression Report

## New tests
`tests/test_phase2f15c_booking_actor_customer_binding.py` — 8/8 passing:
- Source-level actor-binding presence proofs (4)
- Wrong-customer-actor / bound-query behavioral tests (3)
- `Booking.customer_id` immutability audit (1)

## Existing tests fixed (query-shape change, not behavior change)
Changing `convert_to_job`'s and `create_job`'s `booking_id`-path creator checks from `select(BookingStatusHistory.changed_by_role)` (returning a raw role string) to a filtered `select(...id).where(..., changed_by == customer_id)` (returning a match-or-None) required updating 2 tests whose mocks supplied a literal `"tenant_owner"` string in the position now interpreted as "is there a bound match" rather than "what role was it":
- `tests/test_phase2f15a_booking_provenance_and_remaining_routes.py::TestConvertToJobIndependentProof::test_provider_created_booking_without_independent_evidence_rejected` — mock's 3rd value changed `"tenant_owner"` → `None` (no bound match)
- `tests/test_phase2f15a_booking_provenance_and_remaining_routes.py::TestConvertToJobIndependentProof::test_provider_created_booking_with_independent_evidence_passes_gate` — same change
- `tests/test_phase2f15b_booking_creation_provenance_and_customer_dependency.py::TestMissingAmbiguousHistoryFailsClosed::test_provider_confirmation_only_history_fails_closed` — same change
- `tests/test_phase2f15b_booking_creation_provenance_and_customer_dependency.py::TestPersonaRuntimeToolAgreement::test_dual_customer_routes_are_subset_of_tenant_provider_routes` — renamed and corrected to assert the NEW (correct) single-persona classification, since its old assertion (`TENANT_PROVIDER_MUTATION` for dual routes) was exactly 2F-15B's contradictory labeling this slice fixes

No test that previously mocked `"customer"` (a truthy value) in this position needed changes — `"customer" is not None` still correctly evaluates to "bound match found," identical outcome to before.

## Canonical coverage test updated
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount::test_canonical_totals` — updated from `220/179` (2F-15B) to `216/175` (2F-15C), reflecting the physical removal of 4 non-tenant Booking rows from the canonical CSV.

## Suite executions (all overlapping, no live-environment exclusions)
| Suite | Result |
|---|---|
| `test_phase2f15c_booking_actor_customer_binding.py` (new) | 8 passed |
| Wrong-customer actor tests | included above |
| Conflicting/duplicate creation-history tests | proven via `legacy-fail-closed-matrix.csv`'s corresponding inherited tests, re-verified passing |
| Missing/invalid actor tests | `TestMissingAmbiguousHistoryFailsClosed` (2F-15B, re-verified with updated mock) |
| Provider-assisted provenance tests | `TestConvertToJobIndependentProof` (2F-15A, re-verified with updated mock) |
| Legacy fail-closed tests | 2F-15B's `TestMissingAmbiguousHistoryFailsClosed`, re-verified |
| Customer dependency regression tests | `TestCustomerDependencyIndependentOfTenantScope` (2F-15B, unmodified, passing) |
| Existing Slice 2F-15 tests | `test_phase2f15_booking_customer_identity_and_confirmation.py`, unmodified, passing |
| Existing Slice 2F-15A tests | `test_phase2f15a_booking_provenance_and_remaining_routes.py`, 2 mocks updated, passing |
| Existing Slice 2F-15B tests | `test_phase2f15b_booking_creation_provenance_and_customer_dependency.py`, 2 tests updated, passing |
| Booking transition tests | `test_step4_booking.py`, unmodified, passing |
| Booking conversion tests | `test_checklist_system.py`, `test_service_catalog.py`, unmodified, passing (mocks already compatible since they pass `"customer"`) |
| field_ops relationship tests | 2F-14D/E/F/G series, unmodified, passing |
| `field_ops.router` tests | 28/28, exit 0 |
| `field_ops.staff_router` tests | 6/6, exit 0 |
| Runtime verification | `booking.router` exit 0 with corrected persona breakdown |
| Coverage recount verification | `test_canonical_totals` updated and passing |

## Full broad partition sweep
```
python -m pytest -q -k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate or coaching or invoice or payment or commission or parts_request or booking"
1734 passed, 9 skipped, 9288 deselected, 49 warnings
```
Zero failures (up from 1726 at the 2F-15B gate: +8 new tests).

## Live-environment exclusions
No live server/database verification performed this slice — unit tests (mocked `AsyncSession`) plus executed runtime route-introspection only, consistent with every prior slice.
