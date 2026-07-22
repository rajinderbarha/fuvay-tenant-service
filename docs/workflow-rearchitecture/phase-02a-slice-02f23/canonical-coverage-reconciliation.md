# Canonical Coverage Reconciliation — Slice 2F-23

## Baseline confirmed
Counted live from `tenant-mutation-endpoint-inventory.csv`, not copied from
prior documentation: **226 total rows, 207 in the VERIFIED protected set, 19
unprotected.** Matches the approved 207/226 baseline exactly.

## Arithmetic

- Previous numerator: 207
- Newly discovered already-protected rows: **0** — all 19 were runtime-checked
  against the live walk and none reports a VERIFIED guard_status
  (`test_none_of_the_nineteen_is_already_protected`).
- Incorrectly counted protected rows: **0**
- **Reconciled numerator: 207 + 0 − 0 = 207**

- Previous denominator: 226
- Missing mounted tenant mutations: **0** (this slice reconciles the remaining
  19-row queue; the full application sweep for net-new routes was performed in
  2F-17A and is out of this slice's scope, which is stated rather than implied)
- False positives removed: **0**
- Non-tenant rows removed: **0**
- Duplicates removed: **0**
- Deprecated/disconnected removed: **0**
- **Reconciled denominator: 226**

## Result
**207/226 stands exactly. 19 unprotected across 8 modules.**
Status: `NEXT_MODULE_SELECTED_COVERAGE_UNCHANGED`.

## Row-level correction applied (numerator-neutral)

Six canonical rows carried a literal `UNVERIFIED` guard_status
(`submit_reply`, `flag_review`, `provider_run_report`,
`generate_launch_campaign`, `submit_campaign_review`,
`update_asset_provider_notes`). Workstream 1 forbids leaving any row
UNKNOWN or UNVERIFIED, so each was replaced with its runtime-observed value,
**`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`**, together with a precise
`verification_level` note.

Neither the old nor the new value is a member of the VERIFIED set, so this is
a precision correction with **no effect on the numerator or denominator** —
asserted programmatically at the time of the edit (`protected before: 207
after: 207`) and re-asserted by `test_no_canonical_row_remains_unverified`.
Recorded row-by-row in `coverage-row-diff.csv`.

## Breakdown of the 226

| Category | Count |
|---|---|
| Protected (VERIFIED guard_status) | 207 |
| Unprotected genuine tenant/provider mutations | 19 |
| Modules spanning the 19 | 8 |
| Customer mutations | 0 in this CSV — Design A keeps it tenant-only |
| Platform/admin/internal mutations | 0 in this CSV, by the same convention |
| False positives | 0 |
| Duplicates | 0 |
| Disconnected rows | 0 |
| Unverified rows | **0** (was 6 — corrected this slice) |

## Repository-wide search for numeric coverage assertions

Every numeric baseline assertion was located by grep before declaring
reconciliation complete — the step whose omission caused the 2F-20
regression. All currently assert 207/226 or 19 remaining and all pass:

| File | Assertion |
|---|---|
| `test_phase2f14a_field_ops_alternate_route_and_coverage.py` | `total == 226`, `protected == 207` |
| `test_phase2f17a_global_mutation_inventory.py` | `total == 226`, `protected == 207` |
| `test_phase2f19_remaining_queue_reconciliation.py` | `protected == 207`, remainder `19` |
| `test_phase2f21_...selection.py` | live-canonical reads at 207 / remainder 19 |
| `test_phase2f23_...selection.py` (new) | `total == 226`, `protected == 207`, remainder `19` |

No assertion required changing this slice, because the numerator did not move.

## Historical artifacts deliberately NOT rewritten

Per the mission's explicit instruction, point-in-time slice CSVs were left
intact even though the global total has since advanced:

- 2F-19's own CSVs still record 26 remaining / 10 modules.
- 2F-21's own CSVs still record 20 remaining / 9 modules, and its
  `runtime-reverification.csv` still records the package-purchase route as
  unprotected (true at 2F-21; handled by a narrow named exemption in that
  slice's test rather than by rewriting the record).

## Second canonical CSV

`mutation-enforcement-matrix.csv` remains a legacy per-domain summary whose
TOTAL row predates 2F-17A. Consistent with the convention applied in 2F-19,
2F-20, 2F-21 and 2F-22, it is not the authoritative denominator and was not
forced to match. `tenant-mutation-endpoint-inventory.csv` is the single source
of truth and recounts exactly at 226/207.
