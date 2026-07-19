# Job Detail Workspace

Built: `app/dev/ux-04/job-detail/page.tsx`. Sticky header
(`PageHeader` + `PipelineBadge` + `SLAIndicator`) followed by
`JobStatusTimeline`, then sections: status transition, quote
(`QuoteSummary`), checklist (`ChecklistProgress`, `mode="provider_review"`),
parts requests (`PartsRequestSummary`), credit & commission
(`CreditCommissionSummary`), customer communication
(`CustomerCommunicationTimeline`).

Sections specified but not rendered in this route (data modeled in
`JobDetailView` but no section markup written): overview narrative,
assignment (candidates are shown separately in the Assignment/Dispatch
Workspace route, not duplicated here), customer-address, service-details,
inspection, notes, media (`EvidenceGallery` equivalent), invoice/payment,
activity/audit. `JobDetailView` already carries `assignment`, `invoice`,
`media`, `activity` — wiring in the remaining sections is additive, not
blocked.

No information is repeated across the sections that were built.
