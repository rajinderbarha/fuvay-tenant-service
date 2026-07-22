# Branch / Worktree Baseline — Slice 2F-39B

- Base commit (immutable starting point): `5852760` (`security/phase-2f39a5-final-product-decisions`,
  final commit of the approved Slice 2F-39A5).
- Worktree: `G:/serviceos-phase2f39b-migration144`
- Branch: `security/phase-2f39b-migration144-demo-roles`
- Guard: `scripts/workflow_rearchitecture/cert_guard_2f39b.py`, storing its
  mutable `expected_head` state at
  `G:/serviceos-2f37r-preserve/cert_guard_2f39b_state.json` — outside the
  committed worktree, same fix as `cert_guard_2f39a4/5.py`.
- Worktree creation hit the same known `git worktree add` timeout as
  prior slices; resolved the same way (confirmed no live git process,
  removed stale `index.lock`, completed via `git reset --hard HEAD`).
