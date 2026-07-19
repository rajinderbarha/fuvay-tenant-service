# Design Governance Rules

- No raw hex colors — every UX-04 component uses `var(--*)` design-system
  tokens exclusively (verified by source review of all 10 new components).
- No new status registry — `StatusBadge` from `@serviceos/design-system`
  is reused unmodified; UX-04 introduces new *vocabularies* (`SLAState`,
  `QuoteStatus`, `InvoiceState`, etc.) as TypeScript unions, not new badge
  components duplicating `StatusBadge`'s rendering.
- Canonical roles only — `CanonicalTenantRole` (UX-03) is imported, never
  redefined; no new role name appears anywhere in `lib/ux04` or
  `components/ux04`.
- Pipeline separation — enforced at the type level (see
  `booking-pipeline-preservation.md`, `job-model-preservation.md`).
- Backward-compatible design-system changes only, documented — see
  `documentation-corrections.md` for the two fixes made this phase.
