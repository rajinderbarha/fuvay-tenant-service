# Recovered Branch Report

## Final baseline

| Field | Value |
|---|---|
| Branch | `security/phase-2f-authorization-recovered` |
| Worktree | `G:/serviceos-phase2f-recovery` |
| Final commit | `d00f7230f98236c96dd21e1498c78779dc209e7b` |
| Tree hash | `8ad682c33246597ba762d32c247e8fbcaeb3bacb` |
| Parent | `dc7e936b4f8dfaad873fef720337bcbba53c9bc9` |
| Base ancestor (proven) | `4ce23c5` (design/ux-05-staff-technician-app, pre-authorization-program) |
| Working tree | clean (only this slice's own untracked doc directory + guard state file remain, both added by this same run) |

## Commit chain (this slice)

1. `e1ef86b` / `e0652e2` — forensic snapshot (Slice 2F-37R, prior run), unreviewed
2. `29dd931` — consolidated backend baseline, Strategy B, initial exclusion pass
3. `532190d` — correction: restored 2 boot-critical files wrongly excluded
4. `dc7e936` — correction: reverted 47 excluded-but-base-existing files to base content instead of deleting them
5. `d00f723` — `PROTECTED_BY_LATER_SLICE` fix to one now-obsolete historical test assertion

Each correction commit documents, in its own message, the specific defect
it fixes and how it was caught (verifier failure, regression failure) —
none were silent.

## Verification against this final commit

- `verify_2f37.py`: 21/21 PASS (re-run twice, identical)
- `tests/test_phase2f*.py`: 2445/2445 passed, 0 failed (two independent runs, identical)
- `changed-path-classification.csv`: 3,001 paths classified, 0 UNKNOWN
- Application boots successfully (proven by the verifier's own
  `from app.main import app` import, which failed before the corrections
  and succeeds now)

This commit is the recommended starting point for restarting Slice 2F-38.
