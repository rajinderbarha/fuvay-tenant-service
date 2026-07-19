# Known Limitations (UX-04B)

- App-wide color-contrast token shortfall (light mode `--text-secondary`/
  `--warning-text`) — real finding, documented and excluded from the
  blocking axe assertion pending a design-governed follow-up (see
  `accessibility-test-report.md`, `product-decisions-required.md`).
- No modal/drawer/tooltip-trigger exists in any UX-04/04A/04B showcase
  route, so Escape-closes-overlay and focus-trap-and-return were not
  browser-tested this pass (those patterns are covered at the UX-01
  design-system unit-test level instead).
- Table horizontal-scroll-on-overflow at narrow/mobile viewports was not
  visually confirmed (no screenshot diffing performed).
- Dev-showcase pages don't set a per-page `<title>` — all show the app's
  default title.
- Stray nested `package-lock.json` files remain in the repo (worked
  around, not removed — see `lockfile-and-toolchain-evidence.md`).
- No lint tooling configured (`next lint` removed in Next.js 16) —
  genuinely NOT_CONFIGURED, not attempted to be replaced this pass.
- The untracked, foreign `lib/api.persona.test.ts` file (not authored by
  any UX phase, part of pre-existing uncommitted parallel work) still
  fails vitest collection with "No test suite found" — left untouched,
  not this phase's file to fix or delete.
- Item 4 (Booking Detail — ServiceBooking pipeline)'s underlying
  ServiceBooking id remains provisional/placeholder pending a real
  backend contract (`servicebooking-provenance-contract.md`).
- Per-adapter-method contract documentation (route/shape/permission/error
  mapping table) still not written out (carried from UX-04A).
