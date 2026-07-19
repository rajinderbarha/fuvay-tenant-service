# Assignment / Dispatch Workspace

Built: `app/dev/ux-04/assignment-workspace/page.tsx`, component
`components/ux04/AssignmentCandidateCard.tsx`, type
`AssignmentCandidateView`.

Fields rendered: name, availability, current workload, skill match, brand
match, zone coverage, distance (renders "distance not available" when
`distanceLabel` is null rather than fabricating a number), existing
assignment count, rating (same null-safe treatment), warnings, current
assignee marker. No AI-matching score of any kind is computed or
displayed — this was a deliberate hard-constraint check while writing the
component.

Assign/reassign/unassign action (`AssignmentActionView` type exists) is
modeled but the showcase's "Assign" button has no `onAssign` handler wired
(no-op) — reason-required and confirmation-copy fields exist in the type
but aren't rendered in a confirmation dialog this pass.
