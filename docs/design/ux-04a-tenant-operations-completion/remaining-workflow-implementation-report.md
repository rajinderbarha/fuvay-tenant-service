# Remaining Workflow Implementation Report

See `original-scope-reconciliation.csv` for the authoritative per-item
disposition. Summary of the 12 items that were NOT yet implemented at
UX-04 baseline, and their outcome this pass:

| Item | Baseline state | This pass |
|---|---|---|
| 3/4 Booking Detail (both pipelines) | type only | Built `PipelineAwareBookingDetail`, route `/dev/ux-04/booking-detail`, both pipelines side by side |
| 6 field_ops.Job detail | not built | Dispositioned NOT_APPLICABLE_WITH_REPOSITORY_EVIDENCE — no job-specific sections exist for this pipeline beyond Booking Detail |
| 9 Status transition (standalone) | inline only | Extracted into `StatusTransitionPanel`, route `/dev/ux-04/status-transition`, added out-of-sequence-transition flagging |
| 10 Inspection | type only | Built `InspectionSummary`, fixture, route `/dev/ux-04/inspection` |
| 12 Checklist execution (standalone) | mode existed, unused | Route `/dev/ux-04/checklist-execution` added |
| 14 Parts-request list | not built | Dispositioned NOT_APPLICABLE_WITH_REPOSITORY_EVIDENCE — fixture data only ever has one request per job |
| 16 Invoice/payment | type+fixture only | Built `InvoicePaymentSummary`, wired into Job Detail Workspace |
| 19/20 Complaint + Dispute | not built | Built `ComplaintWorkspace` + `DisputePresentation`, fixtures, route `/dev/ux-04/complaints` |
| 21 Compliance submission | UX-03 has a working route; UX-04 extension type unused | Left as ALREADY_IMPLEMENTED_AT_BASELINE — no UX-04-specific route added this pass either (real remaining gap) |
| 22 Media/evidence gallery | not built | Built `EvidenceGallery`, route `/dev/ux-04/media` |
| 23 SLA-risk gallery | inline only | Built `SLAExplanation`, route `/dev/ux-04/sla-risk`, all 9 states |
| 24 Operational exceptions | component built, unembedded | Route `/dev/ux-04/operational-exceptions` added |
| 25/26/27 Staff home / read-only / restricted | not built | Routes `/dev/ux-04/staff-home` and `/dev/ux-04/read-only` added |
