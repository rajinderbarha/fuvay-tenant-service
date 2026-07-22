# Deterministic Test Report

## New test file
`tests/test_phase2f17a_global_mutation_inventory.py` — 7/7 passing:
- `TestFullApplicationExport` (2 tests) — full app export executes, every route has a classification.
- `TestNoMissingTenantMutations` (1 test) — zero genuine missing tenant mutations.
- `TestNoDisconnectedCanonicalRows` (1 test) — zero canonical rows unmounted.
- `TestNoTenantDuplicates` (1 test) — zero tenant-prefixed duplicate registrations.
- `TestNoMisclassifiedNonTenantRows` (1 test) — zero customer/admin/internal rows in the tenant CSV.
- `TestGlobalCoverageConfirmed` (1 test) — 190/226 confirmed.

## Mapping to Workstream 16's required proofs
| Required proof | Satisfied by |
|---|---|
| Full application runtime export executes | `test_full_app_exports_over_one_thousand_mutation_routes` |
| Every mutation-method route receives an actual-behavior classification | `mutation-behavior-classification.csv` (automated, exemption-list-based, zero UNKNOWN) |
| Every genuine mutation receives a persona | `global-persona-classification.csv` |
| No row remains UNKNOWN | `test_every_route_has_a_guard_status` + `mutation-behavior-classification.csv`'s explicit 0-UNKNOWN row |
| No tenant mutation is absent from the canonical inventory | `test_tenant_prefixed_routes_outside_canonical_csv_are_all_confirmed_false_positives` |
| No customer route affects tenant X/Y | `test_no_customer_admin_internal_path_in_canonical_csv` |
| No platform/admin/internal route affects tenant X/Y | same test |
| No false positive affects tenant X/Y | same test + existing `test_no_false_positive_rows` |
| No duplicate affects tenant X/Y twice | `test_no_tenant_prefixed_duplicate_method_path_registrations` + existing `test_no_duplicate_rows` |
| No disconnected row affects tenant X/Y | `test_every_canonical_row_is_mounted_at_runtime` |
| Both canonical CSVs recount identically | unchanged from 2F-15C's established convention (different denominators by design, see `canonical-csv-structure.md`) |
| Runtime recount equals documentation | `test_global_numerator_denominator_match_2f17_baseline` |
| Protected plus unprotected equals denominator | 190 + 36 = 226, confirmed arithmetically in `global-coverage-reconciliation.md` |
| Every unprotected row belongs to exactly one module | `global-module-grouping.csv`, cross-checked to sum to 36 |
| Queue route counts equal the unprotected total | `application-wide-module-queue.csv`'s footer check (10 + 26 = 36) |
| Exactly one next module is selected | `next-module-confirmation.md` |
| Every selected route is mounted | `next-module-confirmation.md` proof point 1 |
