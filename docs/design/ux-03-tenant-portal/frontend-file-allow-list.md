# Frontend File Allow-List

This phase was permitted to touch:
- `frontend/tenant-portal/**` (freely)
- `frontend/packages/design-system/**` (only backward-compatible, evidence-based, additive changes — one change made, documented in design-foundation-compatibility-report.md)
- `docs/design/ux-03-tenant-portal/**`

Explicitly out of scope and untouched: `frontend/super-admin/**`,
`frontend/customer-app/**`, `mobile/customer-app/**`,
`mobile/staff-app/**`, `app/**`, `tests/**`, `scripts/**`, `migrations/**`.
See changed-file-report.md for the actual diff.
