# Frontend File Allow List

This phase was permitted to touch only:
- `frontend/tenant-portal/**` (primary scope)
- `frontend/packages/design-system/**` — only for backward-compatible
  evidence-based fixes, documented if used

No design-system fix was needed or made this phase — every UX-04 need was
met by existing `@serviceos/design-system` exports (`PageShell`,
`PageHeader`, `StatusBadge`). `frontend/super-admin`,
`frontend/customer-app`, `mobile/customer-app`, `mobile/staff-app` were
never touched — see `super-admin-non-regression-report.md` and
`mobile-non-change-report.md` for the verification.
