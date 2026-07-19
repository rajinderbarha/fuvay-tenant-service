# Quote + Checklist Pattern

Embedded as a Job Detail section this phase (`/dev/ux-03/job-detail`'s
"Quote" tab) rather than a standalone page — `ServiceJobFixture.quoteId`/
`checklistId` reference the relevant records. A dedicated showcase route
was deferred (see deferred-items.md). Quote status and checklist
completion should reuse `StatusBadge` with the existing `statusRegistry`
tones, not a new registry.
