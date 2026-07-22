# Test Report

## New tests this slice

- `tests/test_phase2f33_geo_zone_closure.py` — 25/25 passing (see
  [targeted-test-report.md](targeted-test-report.md))
- `scripts/workflow_rearchitecture/verify_geo_2f33.py` — 22/22 conditions
  passing, `--selftest` 22/22 firing correctly (see
  [geo-verification-report.md](geo-verification-report.md),
  [verifier-negative-fixture-report.md](verifier-negative-fixture-report.md))

## Rebaselined tests (cascading regression from the coverage change)

~21 pre-existing test files required literal-value updates
(238→241/262→264/24→23) plus, for 5 of them, formula-level fixes to
reconciliation logic (2F-28, 2F-30's queue-vs-canonical set arithmetic;
2F-21/2F-29's route-set additions; 2F-27a's ROUTE_B provenance/protection
assertions). Full accounting in
[regression-comparison.csv](regression-comparison.csv) and
[documentation-corrections.md](documentation-corrections.md).

## Full suite

`tests/test_phase2f*.py`: **2344 passed, 0 failed**, run twice
consecutively with identical results after all fixes landed (see
[regression-report.md](regression-report.md)).

## Canaries

`tests/test_phase2f31_n01_media_closure.py` (34/34) and
`tests/test_phase2f29_m01_identity_closure.py` (43/43) — the closest
non-regression canaries to this slice's changes — both pass in full.
