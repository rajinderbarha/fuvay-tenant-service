# Parts Request Workflow

Built: `app/dev/ux-04/parts-approval/page.tsx`, component
`components/ux04/PartsRequestSummary.tsx`, type `PartsRequestView`.

Hard constraints verified in the component itself: `request.serviceJobId`
is the only linkage field (no `field_ops.Job` id accepted anywhere in the
type), and the Approve/Reject buttons render only when
`actions.find(a => a.actionKey.includes("approve"))?.available` is true —
otherwise a "not available with your current permissions" message renders
instead of a disabled-but-visible button. No "mark installed" control
exists in the component for a technician-facing render; the type notes
mark-installed as provider-only in its actions but no separate technician
view was built (technician request/view-only surface is deferred).
No invented PO/inventory workflow — only qty × unitCost line totals.
