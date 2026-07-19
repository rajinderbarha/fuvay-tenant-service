# Frontend File Allow List (UX-04B)

Same allow list as UX-04/UX-04A: `frontend/tenant-portal/**` primary
scope; `frontend/packages/design-system/**` only for backward-compatible,
documented fixes (none made this pass — the Tooltip fix from UX-04A is
unchanged). `frontend/tenant-portal/styles/globals.css` (an app-local
theme file, not shared with any other app) was inspected but
**deliberately not modified** this pass despite a real color-contrast
finding — see `accessibility-test-report.md` and
`documentation-corrections.md` for why a narrow correction pass isn't the
right scope for an app-wide token reskin. `frontend/super-admin`,
`frontend/customer-app`, `mobile/customer-app`, `mobile/staff-app` — zero
changes, tree-hash verified.
