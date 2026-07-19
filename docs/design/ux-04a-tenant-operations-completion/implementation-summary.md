# UX-04A Implementation Summary

Continuation of UX-04 (baseline commit `6dbd8ce`, status
`TENANT_OPERATIONS_DESIGN_PARTIAL`) on the same branch
`design/ux-04-tenant-operations`. This pass closes the majority of the
original 27-item gap, adds a real automated test suite (new capability —
none existed for tenant-portal at baseline), and re-verifies everything in
a fresh WSL environment after a mid-session host/WSL restart.

## What changed this pass

- **7 new components**: `PipelineAwareBookingDetail`, `StatusTransitionPanel`,
  `ComplaintWorkspace` + `DisputePresentation`, `EvidenceGallery`,
  `SLAExplanation`, `InvoicePaymentSummary`, `InspectionSummary` — none
  duplicate the 10 components built at UX-04 baseline.
- **10 new dev showcase routes**: booking-detail, status-transition,
  complaints, media, sla-risk, operational-exceptions, staff-home,
  read-only, inspection, checklist-execution — bringing the total to 15
  showcase routes (up from 5).
- **New fixtures**: complaint detail, dispute, operational exceptions (3),
  SLA gallery (all 9 states), inspection.
- **New test infrastructure**: `frontend/tenant-portal` had zero test
  capability at UX-04 baseline (no vitest config, no test script). Added
  `vitest.config.ts`, `test-setup.ts`, vitest/testing-library
  devDependencies, and `tsconfig.json` `types` entry — this also fixed the
  4 pre-existing UX-03 test-file type errors that blocked `tsc --noEmit`
  at baseline.
- **9 new test files, 35 passing tests** covering domain preservation,
  authorization presentation, workflow behavior, security/privacy, and UI
  states (see `ux04-test-report.md`).
- **Full 27-item scope reconciliation** — 24 of 27 items now IMPLEMENTED
  (including 2 legitimately dispositioned NOT_APPLICABLE_WITH_REPOSITORY_EVIDENCE
  and 1 ALREADY_IMPLEMENTED_AT_BASELINE), see
  `original-scope-reconciliation.csv`.

## What's still open

One item (#4, ServiceBooking-pipeline Booking Detail) is
IMPLEMENTED_WITH_CAVEAT because UX-03's fixture layer never modeled a
distinct "ServiceBooking" pre-job entity — see
`booking-detail-pipeline-evidence.md`. Pre-existing UX-03 test files
(`PermissionEditor.test.tsx`, `SetupWizard.test.tsx`) fail with an "Invalid
hook call" error under the newly-added vitest config — a real,
pre-existing incompatibility this pass surfaced but did not fix (root
cause not conclusively diagnosed within this pass's budget — see
`ux04-test-report.md`). `next lint` no longer exists in Next.js 16 — lint
is genuinely NOT_CONFIGURED, not fabricated.
