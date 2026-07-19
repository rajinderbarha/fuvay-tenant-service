# Status Transition Workspace

Built inline within Job Detail Workspace (`app/dev/ux-04/job-detail`),
type `StatusTransitionView` / `StatusTransitionOptionView`. Shows current
status, each allowed-next option's required fields/evidence, and
customer-visible effect. Finance effect is modeled (`financeEffect: string
| null`) but not rendered in the built showcase (only the two fields shown
above are — a one-line addition to render it, deferred for time).

Confirmation dialog, success/error states, and audit-on-transition are
**not implemented** — the workspace is read-only presentation of the
transition contract, no mutating action is wired. `allowedNext` being
empty is treated as a valid terminal/blocked state in the type (no
fallback fabricated options).
