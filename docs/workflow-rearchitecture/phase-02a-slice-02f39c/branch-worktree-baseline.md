# Branch / Worktree Baseline — Slice 2F-39C

- Base commit (immutable starting point): `a9659b5` (`security/phase-2f39b-migration144-demo-roles`,
  final commit of Slice 2F-39B before its own doc-only follow-up commit).
- Worktree: `G:/serviceos-phase2f39c-suite-stability`
- Branch: `security/phase-2f39c-suite-stability`
- Guard: `scripts/workflow_rearchitecture/cert_guard_2f39c.py`, storing its
  mutable `expected_head` state at
  `G:/serviceos-2f37r-preserve/cert_guard_2f39c_state.json` — outside the
  committed worktree, same fix as prior slices' guards.
- Worktree creation completed cleanly this time (no timeout).
