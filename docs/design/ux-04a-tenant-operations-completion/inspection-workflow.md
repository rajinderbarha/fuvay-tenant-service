# Inspection Workflow (UX-04A)

`components/ux04/InspectionSummary.tsx`, fixture `inspectionFixture`
(`lib/ux04/fixtures.ts`), route `/dev/ux-04/inspection`. ServiceJob-scoped
only (`serviceJobId`). No safety/legal claims beyond the free-text
`findings`/`observations` fields entered by the technician. `quoteRequired`
renders a prompt copy ("A quote is required before work proceeds"), never
an automatic quote-creation trigger — no code path calls a quote-creation
function from this component.
