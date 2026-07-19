# Inspection Workflow (type built, showcase route DEFERRED)

Type: `InspectionView` (`lib/ux04/types.ts`) — `serviceJobId`, `findings`,
`customerReportedIssue`, `observations: string[]`, `photos:
MediaAssetFixture[]`, `recommendedWork: string[]`, `requiredParts: {name,
qty}[]`, `quoteRequired: boolean`, `checklistStatus`.

No fixture data or showcase route was built for this type this pass — it
is scoped to `ServiceJob` only (no `field_ops.Job` inspection concept
exists), no safety/legal claims are modeled (only `findings`/
`observations` free text), and no auto-quote action is implied
(`quoteRequired` is a flag for the UI to prompt a human quote-creation
step, not a trigger).
