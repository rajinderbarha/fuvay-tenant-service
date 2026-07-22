# Test Report

## New tests this slice

- `tests/test_phase2f31a_n01_residual_closure.py` — 30/30 passing (see
  [targeted-test-report.md](targeted-test-report.md))
- `scripts/workflow_rearchitecture/verify_n01_2f31a.py` — 21/21 conditions
  passing, `--selftest` 21/21 firing correctly (see
  [residual-n01-verification-report.md](residual-n01-verification-report.md),
  [verifier-negative-fixture-report.md](verifier-negative-fixture-report.md))

## Rebaselined tests (cascading regression from the coverage change)

15 pre-existing test files required literal-value updates (233→238,
29→24) plus, for 4 of them, formula-level fixes to reconciliation logic
(2F-28, 2F-30's queue-vs-canonical set arithmetic; 2F-21's
`PROTECTED_BY_LATER_SLICE` additions). Full list in
[regression-comparison.csv](regression-comparison.csv). All fixed and
passing.

## Full suite

`tests/test_phase2f*.py`: **2319 passed, 0 failed**, run twice with
identical results (see [regression-report.md](regression-report.md) and
[deterministic-test-report.md](deterministic-test-report.md)).

## Canaries

`tests/test_phase2f31_n01_media_closure.py` (34/34) and
`tests/test_phase2f29_m01_identity_closure.py` (43/43) — the two closest
non-regression canaries to this slice's changes — both pass in full.
