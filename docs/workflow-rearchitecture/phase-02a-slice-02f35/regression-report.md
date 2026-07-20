# Regression Report

## Summary

Full `tests/test_phase2f*.py` suite: **2378 passed, 0 failed, 0 errors**,
run twice for determinism (365.24s, 376.82s), identical results both
times. Baseline was 2344 passed at the end of Slice 2F-34; the +34 delta
is exactly the new `tests/test_phase2f35_critical_authorization_batch.py`
file — no removed or renamed node IDs.

## Rebaseline detail

The live canonical CSV moved from 264/241/23 (total/protected/unprotected)
to 273/252/21 as a direct, intended consequence of this slice's closures.
18 pre-existing historical test files across Slices 2F-14A through 2F-26B
assert these figures by reading the live canonical CSV file (not a frozen
snapshot), so each needed its literal updated in place, at its exact
assertion line, with a one-line attribution comment. No frozen
point-in-time artifact, historical CSV, or historical claim was rewritten
— see `documentation-corrections.md` for the full list and
`canonical-row-diff.csv` for the row-level diff. This is the same
current-state-override pattern used by every prior slice in this program
(e.g. the `PROTECTED_BY_LATER_SLICE` set idiom).

## M01 / N01 / geo non-regression

Confirmed unregressed by `TestM01N01GeoNonRegression` (3 tests) in the new
targeted suite, and by re-running each of `test_phase2f29_m01_identity_
closure.py`, `test_phase2f31_n01_media_closure.py`,
`test_phase2f31a_n01_residual_closure.py`,
`test_phase2f33_geo_zone_closure.py` individually — all green.

## Application files changed this slice

Exactly 9: `app/engines/webhook/{router,service}.py`,
`app/engines/rag/{router,service}.py`,
`app/engines/security/{router,service}.py`,
`app/engines/document/{router,service}.py`,
`app/engines/field_ops/service.py` (one internal-caller fix). No
Slice 2F-36/2F-37 file was touched. (The repository's working tree also
carries a large number of uncommitted changes from prior slices in this
same session — those predate this slice and are out of its scope; the 9
files above are the ones this slice itself introduced.)
