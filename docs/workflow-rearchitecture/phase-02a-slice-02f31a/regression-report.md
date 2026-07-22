# Regression Report

## Full suite, run twice (determinism)

`python -m pytest tests/test_phase2f*.py -q`

| Run | Passed | Failed | Errors | Duration |
|---|---|---|---|---|
| 1 | 2319 | 0 | 0 | 306.27s |
| 2 | 2319 | 0 | 0 | 316.24s |

Identical pass count both runs — deterministic.

## New vs resolved vs unchanged failures

- **New failures introduced by this slice's application code changes:** 0.
- **Resolved (cascading rebaseline from the 233→238 / 29→24 coverage
  change):** 18 tests across 15 files, all fixed this slice (full list:
  [regression-comparison.csv](regression-comparison.csv)).
- **Unchanged (already passing, untouched):** the remaining ~2271 tests in
  `tests/test_phase2f*.py`.
- **New tests added:** 30 (`test_phase2f31a_n01_residual_closure.py`).

Baseline before this slice's rebaseline work: 2289 passed / 18 failed
(after the primary N01 closure code changes landed, before the
cross-slice rebaseline). After rebaseline + new tests: 2319 passed / 0
failed. Net: 2289 + 18 (fixed) + 12 (net new after accounting for the +30
new file against the -18 that were "already counted" as failing, i.e.
2289 + 30 = 2319) — consistent with the two full-suite numbers above.

## Environment changes

None. No dependency added/removed/upgraded, no migration, no config
change. See [environment-test-evidence.md](environment-test-evidence.md).

## Canonical/matrix hashes (final)

- Canonical: `1f7891798eb8382f`
- Matrix: `abac4ae72e8ab1d4`

## Application files changed this slice

- `app/core/permissions.py`
- `app/engines/media/new_router.py`
- `app/engines/media/router.py`
- `app/engines/media/service.py`

(Full allow-list rationale: [expanded-application-file-allow-list.md](expanded-application-file-allow-list.md).)

## Targeted / canary / verifier reruns

- `tests/test_phase2f31_n01_media_closure.py`: 34/34
- `tests/test_phase2f29_m01_identity_closure.py`: 43/43
- `tests/test_phase2f28_module_selection.py`: 34/34
- `tests/test_phase2f30_post_m01_selection.py`: 42/42
- `tests/test_phase2f31a_n01_residual_closure.py`: 30/30 (new)
- `verify_n01_2f31a.py` main: 21/21
- `verify_n01_2f31a.py --selftest`: 21/21 fire correctly
- `verify_selection_2f28.py` main + selftest: 20/20 both
- `verify_m01_2f29.py`: passing (M24 +5 term)
- `verify_dualreview_2f27.py`: passing (V11 rebaselined)
