# Compliance Submission Workflow (type built, showcase route DEFERRED)

Type: `ComplianceSubmissionView` (`lib/ux04/types.ts`) — wraps UX-03's
`ComplianceItemFixture`, adds `affectedFields: string[]` (populated only
on rejected/changes-requested-equivalent states),
`reviewerExplanation`, `priorSubmissionPreserved: boolean`,
`resubmissionSupported: boolean`. UX-03 already has a working `/dev/ux-03/
compliance` showcase (reused for facts, not code) — this pass did not
build a UX-04-specific route; the extension fields above are additive to
that existing pattern for a future pass.
