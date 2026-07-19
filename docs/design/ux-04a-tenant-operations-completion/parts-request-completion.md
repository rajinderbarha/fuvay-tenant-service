# Parts Request Completion (UX-04A)

`PartsRequestSummary` (UX-04 baseline component, unchanged) now also
reused in the new `/dev/ux-04/read-only` route with every action forced
`available: false`, demonstrating the restricted-state presentation for
this specific workflow. No "parts-request list" page was built — the
fixture data set only ever contains one parts request per job
(`partsRequestFixture`), so a distinct multi-row list view has no real
content to differentiate it from the single-item summary already shown in
Job Detail Workspace; dispositioned NOT_APPLICABLE_WITH_REPOSITORY_EVIDENCE.
`PartsRequestSummary.test.tsx` (UX-04A) asserts: Approve/Reject render only
when available; a denial reason renders instead of a disabled button when
not; no mark-installed control ever renders (no technician install
authority); the request always displays its `serviceJobId`, never a
field_ops.Job id.
