# Typed Fixture Contract

Types: `frontend/super-admin/lib/ux02/types.ts`. Fixture data: `lib/ux02/fixtures.ts`.

## Entities
`TenantFixture`, `VerificationSubmissionFixture`, `ComplianceCaseFixture`,
`SecurityObservationFixture`, `AuditEntryFixture`, `PlatformNoticeFixture` — all UI-layer types,
explicitly documented in the file header as fixtures, not a second source of truth for backend
contracts.

## Rules followed
- No lorem ipsum — every fixture uses realistic ServiceOS-shaped names/cities/roles/amounts.
- No real production URLs — owner emails use `*-example.test` domains.
- No real secrets — `AuditEntryFixture.detailsRedacted` contains only synthetic key/value pairs.
- Canonical roles only — `AuditEntryFixture.role: CanonicalAdminRole`.
- Finance fixtures separate `packageCreditBalance`, `commissionRateBps`, and
  `securityDepositAmount` as distinct fields (never summed together) per the canonical finance
  rule.

## Separation of concerns
UI model (`types.ts`) / fixture data (`fixtures.ts`) / adapter interface
(`Ux02DataAdapter`, `CommandPaletteAdapter` in `types.ts`) are three distinct pieces — a future
production integration implements `Ux02DataAdapter` against real endpoints without touching the UI
components, which only depend on the type shapes.
