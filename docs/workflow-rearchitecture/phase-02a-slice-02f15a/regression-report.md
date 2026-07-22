# Regression Report

## New test file
`tests/test_phase2f15a_booking_provenance_and_remaining_routes.py` — 8/8 passing.

## Pre-existing tests broken by new provenance queries, fixed
The new independent-relationship-evidence queries added to `create_job`'s `booking_id` path and `convert_to_job` consume additional `db.execute()` calls. 7 pre-existing tests needed an additional mocked query result inserted into their `side_effect`/`_db_returning(...)` sequence (all set to `"customer"`, which short-circuits the new independent-evidence sub-query — no behavioral test logic changed):

- `tests/test_phase2f14d_field_ops_create_job_relational_consistency.py::TestBookingRelationalConsistency::test_matching_booking_customer_service_succeeds`
- `tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py::TestBookingStatusEligibility::test_confirmed_booking_accepted`
- `tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py::TestBookingParentCoexistence::test_booking_only_unaffected`
- `tests/test_phase2f14f_field_ops_manual_customer_authority.py::TestBookingParentModesUnaffectedByRelationshipGuard::test_booking_referenced_creation_does_not_query_relationship`
- `tests/test_checklist_system.py::test_convert_to_job_seeds_checklist_from_catalog_template`
- `tests/test_checklist_system.py::test_convert_to_job_no_checklist_key_when_template_empty`
- `tests/test_service_catalog.py::test_convert_to_job_uses_catalog_job_type_when_present`
- `tests/test_service_catalog.py::test_convert_to_job_falls_back_gracefully_with_no_catalog_entry`

All 8 confirmed passing after the fix.

## Full sweep
```
python -m pytest -q -k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate or coaching or invoice or payment or commission or parts_request or booking"
1713 passed, 9 skipped, 9288 deselected, 49 warnings
```

Zero failures. `9 skipped` are pre-existing skips unrelated to this slice (not re-investigated; consistent with every prior slice's sweep).

## Live-environment exclusions
No live server / live database verification was performed this slice (matches every prior slice in this initiative) — all verification is via unit tests with mocked `AsyncSession` and the static runtime route-introspection tool. This is reported honestly, not counted as "passing" live verification.
