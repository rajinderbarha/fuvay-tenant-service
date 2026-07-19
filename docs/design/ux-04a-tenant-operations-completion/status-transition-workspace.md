# Status Transition Workspace (UX-04A)

`components/ux04/StatusTransitionPanel.tsx`, route
`/dev/ux-04/status-transition`. Enforces the repository-backed lifecycle
`assigned -> on_the_way -> inspection -> in_progress -> work_done ->
completed` as defense-in-depth: options in `allowedNext` that aren't the
immediate next lifecycle step are visually flagged (red border +
"out-of-sequence transition offered by the adapter" warning) rather than
silently accepted — see `StatusTransitionPanel.test.tsx` for the assertion.
Terminal state (`completed`) renders no further options. An empty
`allowedNext` on a non-terminal status renders an explicit "no allowed
transition" message rather than an error or blank panel.
