# Branch/Worktree Baseline

- Certification worktree: `G:/serviceos-phase2f38-certification`, created via
  `git worktree add ../serviceos-phase2f38-certification -b
  security/phase-2f38-certification 01e6ee4`.
- The initial `worktree add` timed out mid-checkout (2min tool limit against
  a ~5,900-file tree) and left a stale `index.lock` in
  `.git/worktrees/serviceos-phase2f38-certification/`. Verified via
  PowerShell `Get-Process` that no git process was actually running before
  removing the stale lock, then completed the checkout with `git reset
  --hard HEAD` inside the new worktree (safe: freshly created worktree,
  no real uncommitted work to lose). Working tree confirmed clean
  (0 porcelain entries) immediately after.
- `git worktree list` at the time of creation:
  ```
  G:/serviceos                                       [design/ux-05-staff-technician-app]
  G:/serviceos-phase2f-recovery                       [security/phase-2f-authorization-recovered]
  G:/serviceos-ux05b-finalization                      [design/ux-05b-finalization]
  G:/serviceos-ux06-customer-app                       [design/ux-06-customer-app]
  G:/serviceos/.claude/worktrees/agent-ab43bbb80d9715b62 [worktree-agent-ab43bbb80d9715b62]
  ```
  No other worktree uses `security/phase-2f38-certification` or points at
  `G:/serviceos-phase2f38-certification`.
- `security/phase-2f-authorization-recovered` confirmed unchanged at
  `01e6ee4` (re-checked via `git rev-parse` from the main worktree,
  read-only) both before and after certification worktree creation.
- All UX branches (`design/ux-05-staff-technician-app`,
  `design/ux-05b-finalization`, `design/ux-06-customer-app`) were only
  read (for their current HEAD, to confirm this session isn't touching
  them), never checked out or written to by this slice.
