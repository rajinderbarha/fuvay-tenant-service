# Worktree Interference Guard

`scripts/workflow_rearchitecture/cert_guard_2f38.py` (same pattern as
Slice 2F-37R-A's `recovery_guard_2f37ra.py`) checks worktree path, git-dir,
branch, base-commit ancestry, and expected HEAD before every write, commit,
verifier, and long-running command in this slice. It never reported
`CONCURRENT_WORKTREE_INTERFERENCE` during this slice's execution.

The shared main worktree (`G:/serviceos`, `design/ux-05-staff-technician-app`)
continued to advance independently during this slice (observed at
`a48bb44` at the start of this run) — expected and harmless, since this
slice performs zero writes there.
