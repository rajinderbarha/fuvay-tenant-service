# Active Process Quarantine

## Worktrees at start of this run

```
worktree G:/serviceos
HEAD 12ed9f64433b8e29c3f1e628a474234c71a2f3d0
branch refs/heads/design/ux-05-staff-technician-app

worktree G:/serviceos/.claude/worktrees/agent-ab43bbb80d9715b62
HEAD 910d9ff1d04fa3be3ff604de90fe5ca571a41ac6
branch refs/heads/worktree-agent-ab43bbb80d9715b62
```

No `.git/*.lock` files present.

## Processes observed

```
 2996 claude      2026-07-20 08:46:35
 7084 claude      2026-07-20 09:16:16
15908 claude      2026-07-20 08:46:35
 4888 node        2026-07-20 09:30:16
14252 node        2026-07-20 09:29:57
16704 node        2026-07-20 09:30:16
17100 node        2026-07-20 09:30:16
12176 python      2026-07-20 10:59:39
16380 python      2026-07-20 10:59:58
```

Three separate `claude` host processes are running, two started before this
session's own work began (08:46), one at 09:16. The second worktree
(`agent-ab43bbb80d9715b62`) is a Claude Code subagent worktree, isolated from
the main `G:/serviceos` directory — not the source of the collision.

## Root cause assessment

The reflog evidence from the interrupted 2F-37R run (`checkout: moving from
recovery/phase-2f-uncommitted-snapshot to design/ux-05-staff-technician-app`,
followed by commit `12ed9f6`, both unattributed to this session) is
consistent with **one of the other `claude` processes (2996 or 15908,
running since before this session started) operating directly in the shared
main worktree `G:/serviceos`**, continuing its own UX-05 Round 4 work while
this session was also using the same directory for git operations. The two
sessions were not worktree-isolated from each other, so both were reading
and writing `G:/serviceos/.git` and its single working tree concurrently.

This is not something this session can fix by itself (it cannot safely
terminate another session's host process). The mitigation available to this
session is exactly what this slice's non-negotiable rule specifies: stop
using the shared main worktree for further recovery writes, and move all
recovery work into a dedicated worktree bound to its own branch.

## Quiet observation window

Recorded branch/HEAD, waited, rechecked:

| Check | Time | Branch | HEAD |
|---|---|---|---|
| 1 | T+0s | design/ux-05-staff-technician-app | 12ed9f6 |
| 2 | T+~90s (after this doc + subsequent commands) | design/ux-05-staff-technician-app | 12ed9f6 |

No further unexplained mutation occurred on `G:/serviceos` during this
session's own quarantine/worktree-setup window. Proceeding to Workstream 2
(dedicated recovery worktree), after which this session performs no further
writes to the shared main worktree at all.
