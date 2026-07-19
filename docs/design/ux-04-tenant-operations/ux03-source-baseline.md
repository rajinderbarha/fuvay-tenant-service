# UX-03 Source Baseline

UX-04 is built directly on UX-03 commit `ddf7094` (branch
`design/ux-03-tenant-portal`), which is the base of
`design/ux-04-tenant-operations`. Reused directly, never re-derived:

- `frontend/tenant-portal/lib/ux03/types.ts` — `PipelineKind`,
  `BookingFixture`, `ServiceJobFixture`, `PartsRequestFixture`,
  `PackageCreditFixture`, `ComplaintFixture`, `ComplianceItemFixture`,
  `MediaAssetFixture`, `AuditEventFixture`, `CanonicalTenantRole`,
  `ReadinessState`.
- `frontend/tenant-portal/lib/ux03/fixtures.ts` — realistic fixture rows
  for the above.
- `frontend/tenant-portal/components/ux03/widgets/PipelineBadge.tsx` —
  reused as-is in every UX-04 booking/job showcase row.
- `frontend/tenant-portal/components/ux03/widgets/ReadinessTag.tsx` —
  reused where dev-only readiness needs surfacing.
- `docs/design/ux-03-tenant-portal/booking-job-pipeline-separation.md`,
  `booking-operations-specification.md`, `job-operations-specification.md`,
  `assignment-dispatch-pattern.md`, `quote-checklist-pattern.md`,
  `parts-request-management.md`,
  `package-credit-commission-pattern.md`, `finance-history-pattern.md`,
  `security-deposit-pattern.md`, `customer-complaint-pattern.md`,
  `compliance-pattern.md`, `media-management-pattern.md` — read in full
  before writing any UX-04 spec; facts (status vocabularies, pipeline
  separation, permission model) reused, not re-derived from scratch.

No UX-03 file was modified by this phase.
