# Known Limitations — Slice 2F-37R-A

- **Strategy B, not Strategy A.** Exact per-slice (2F-35 vs 2F-36 vs 2F-37)
  commit boundaries could not be reconstructed — see
  `recovery-strategy-decision.md`. Only the final, combined 313/313 state
  is git-verifiable from this recovery; historical intermediate positions
  (252/273, 294/297) remain narrative claims from the pre-existing
  documentation, not independently re-derivable from committed history.
- **No dedicated held-registry/Set-C recount script exists.** This slice's
  canonical-state evidence relies on `verify_2f37.py`'s R01/R03/R16
  conditions rather than a from-scratch recomputation script for those two
  dimensions specifically (R13/R14/R19/R20 — protected/unprotected/hash —
  were independently recomputed). See `canonical-state-reconciliation.md`.
- **UX-05's own test suite was not re-run.** By design (concurrency
  isolation) this slice never touched the shared main worktree after
  Workstream 1, so UX-05's own 39/39 (as of its own latest commit) is
  taken on the strength of its own commit messages, not independently
  re-verified here.
- **Migration 144 remains unapplied and unproven at runtime.** No
  PostgreSQL/Redis/Docker is reachable in this environment. Apply/rollback/
  reapply evidence still does not exist anywhere in this program. See
  `migration-runtime-blocker.md`.
- **Both invalid-role demo accounts remain unresolved.** No evidence-backed
  canonical mapping exists for either. See `role-remediation-blocker.md`.
- **N01 domain-integrity backlog remains open**, unchanged and
  unremediated by this slice (out of scope, per the frozen contract chain
  inherited from 2F-34).
- **The concurrency root cause is not fixed.** This slice worked around a
  second process actively committing to the shared main worktree by using
  a dedicated worktree; it did not (and could not) stop that other process.
  Future slices should confirm no other session is using `G:/serviceos`'s
  main worktree before doing further git-mutating authorization work there,
  or continue using isolated worktrees as a standing practice.
