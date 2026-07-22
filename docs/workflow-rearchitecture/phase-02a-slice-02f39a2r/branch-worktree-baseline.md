# Branch/Worktree Baseline

`G:/serviceos-phase2f39a2r-remediation` created via `git worktree add
../serviceos-phase2f39a2r-remediation -b
security/phase-2f39a2r-defect-remediation fca8a96`. The initial `worktree
add` timed out mid-checkout (same recurring pattern as every large
worktree creation in this program — a ~6,000-file tree against a 2-minute
tool limit); confirmed no git process running via PowerShell
`Get-Process` before clearing the stale `index.lock` and completing via
`git reset --hard HEAD` (safe: fresh worktree, no real work to lose).
Working tree confirmed clean immediately after.

`G:/serviceos-phase2f39a2-route-census` (the prior tranche's worktree)
was not touched.
