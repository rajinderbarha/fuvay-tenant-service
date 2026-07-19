# Operational Search Specification (DEFERRED — typed contract only)

`Ux04OperationsAdapter.search(query): Promise<OperationalSearchResultGroup[]>`
is defined in `lib/ux04/types.ts`. `OperationalSearchResultGroup` groups
`EntityLinkView[]` results under a `pipelineLabel` (e.g. "Bookings",
"Service Jobs", "Quotes", "Parts Requests", "Invoices", "Complaints") so
results are never shown as one undifferentiated flat list.

**Not built this pass**: no search input UI, no showcase route, no
fixture-backed search implementation. This is the single largest
deliberate scope cut in this phase — search cuts across every entity type
and needed the other view models finished first; it is next in line for a
follow-up pass, not blocked by any product/security question.
