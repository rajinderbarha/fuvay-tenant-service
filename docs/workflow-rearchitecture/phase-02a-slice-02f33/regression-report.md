# Regression Report

## Full suite, run three times total (one post-fix confirmation + two-for-determinism)

`python -m pytest tests/test_phase2f*.py -q`

| Run | Passed | Failed | Errors | Duration |
|---|---|---|---|---|
| 1 (initial, before full rebaseline) | 2284 | 60 | 0 | 317.26s |
| 2 (after primary rebaseline; 1 straggler found) | 2343 | 1 | 0 | 993.41s |
| 3 (post-straggler-fix; confirmation) | 2344 | 0 | 0 | 852.70s |
| 4 (determinism run 2) | 2344 | 0 | 0 | 827.11s |

Final two runs identical: **2344 passed, 0 failed, deterministic.**

## New vs resolved vs unchanged failures

- **New failures caused by this slice's application code changes:** 0.
- **Resolved (cascading rebaseline from the 238→241/262→264/24→23
  coverage change):** 60 tests across ~20 files, all fixed this slice.
  One additional straggler (`test_phase2f14a_field_ops_alternate_route_
  and_coverage.py`) was found in the first full-suite confirmation run
  and fixed.
- **Self-inflicted regression found and fixed within this slice:** a
  blanket literal-value sed initially miscorrected 6 unrelated
  classifier-agreement assertions (2F-26d/e/f/g/h test files) that
  happened to share the literal `24`/`23` with the canonical-coverage
  figures but meant something unrelated (corpus sample counts). Caught by
  running the FULL suite rather than only the directly-touched files;
  fixed with narrow, explained, non-blanket corrections. A second, more
  subtle round was needed: Slice 2F-33's authorization fix legitimately
  changed the LIVE persona/tenant-direction classifier's read of 2
  routes (`update_location`, `create_zone`) from `CLIENT_ASSERTED_TENANT`
  to `PRINCIPAL_TENANT` — this is a correct, expected consequence of the
  fix, not a bug, and was reconciled via a documented per-route exception
  in the classifier-corpus tests rather than editing the frozen manual
  labels. See [documentation-corrections.md](documentation-corrections.md)
  for the full account.
- **New tests added:** 25 (`test_phase2f33_geo_zone_closure.py`).
- **Unchanged (already passing, untouched):** the remaining ~2280+ tests.

## Environment changes

None. No dependency added/removed/upgraded, no migration, no config
change.

## Canonical/matrix hashes (final)

- Canonical: `d4900ce03daa5437`
- Matrix: `abfa5d030b1cfeee`

## Application files changed this slice

- `app/engines/geo/router.py`
- `app/engines/geo/service.py`

Confirmed by `git status --porcelain app/` count: 63 (pre-existing dirty
files from unrelated earlier work) → 65 (+2, exactly the two files
above) — no other application file was touched. Also confirmed by mtime:
these two files are the only `app/` files modified within this slice's
working window.

## Targeted / canary / verifier reruns

- `tests/test_phase2f33_geo_zone_closure.py`: 25/25
- `tests/test_phase2f29_m01_identity_closure.py`: 43/43
- `tests/test_phase2f31_n01_media_closure.py`: 34/34
- `tests/test_phase2f31a_n01_residual_closure.py`: 30/30
- `tests/test_phase2f28_module_selection.py`: 34/34
- `tests/test_phase2f30_post_m01_selection.py`: 42/42
- `verify_geo_2f33.py` main: 22/22
- `verify_geo_2f33.py --selftest`: 22/22 fire correctly
