# Known Limitations (UX-04A)

- 2 pre-existing UX-03 test files fail under the newly-added vitest config
  (`ux04-test-report.md`) — real, unresolved.
- No lint tooling runnable at all on this Next.js version (`next lint`
  removed) — `NOT_CONFIGURED`, not a regression, but still a gap.
- No hydration-mismatch detection (`ssr-hydration-report.md`) — curl-level
  smoke check only, no headless browser.
- No live browser theme-toggle verification (`theme-runtime-report.md`) —
  source-review only.
- Compliance submission workflow extension (item 21) still has no UI —
  `ALREADY_IMPLEMENTED_AT_BASELINE` disposition covers the base case but
  not the UX-04-specific resubmission fields.
- ServiceBooking-pipeline Booking Detail (item 4) uses a caveat-laden
  representation, not a genuinely distinct fixture type
  (`booking-detail-pipeline-evidence.md`).
- Per-adapter-method contract documentation (route/shape/permission/error
  mapping table) still not written out (`adapter-contract-completion.md`).
- No accessibility tooling (`accessibility-test-report.md`).
