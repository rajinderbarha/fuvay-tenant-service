# Deferred Items (UX-04B)

Carried forward from UX-04A (compliance-submission resubmission UI,
operational search, filter/preset controls, remaining view sections in
Job Detail Workspace, per-adapter-method contract table, distinct
`ServiceBookingFixture` type beyond the provisional id), plus new this
pass:

- App-wide color-contrast token fix (design-governed decision needed
  first).
- Stray nested `package-lock.json` removal (`frontend/tenant-portal` and
  `frontend/super-admin`), as a dedicated toolchain-hygiene pass.
- A real ESLint config compatible with Next.js 16 (no `next lint`
  anymore).
- Screenshot-based visual/overflow verification at narrow viewports.
- Modal/Drawer/Tooltip-trigger keyboard (Escape, focus-trap) browser
  tests — no UX-04 page currently uses those components, so there's
  nothing to test yet; revisit once one does.
