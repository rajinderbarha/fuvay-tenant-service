# Branch / Worktree Baseline — Slice 2F-39A4

- Base commit (immutable starting point): `cea399f` (`security/phase-2f39a3-route-census-tranche3`,
  final commit of the approved Slice 2F-39A3, including the reviewer's
  wording/disposition/guard-defect corrections).
- Worktree: `G:/serviceos-phase2f39a4-product-decision`
- Branch: `security/phase-2f39a4-product-decision-remediation`
- Guard: `scripts/workflow_rearchitecture/cert_guard_2f39a4.py`, storing its
  mutable `expected_head` state at
  `G:/serviceos-2f37r-preserve/cert_guard_2f39a4_state.json` — outside the
  committed worktree, per the reviewer's fix for the staleness defect
  documented in 2F-39A3's `worktree-interference-guard.md`.
- Worktree creation hit the same known `git worktree add` timeout as prior
  slices (repo has ~6,000 tracked files); resolved the same way — confirmed
  no live git process via PowerShell `Get-Process`, removed the stale
  `index.lock`, completed via `git reset --hard HEAD` in the new worktree.
