# Deferred Items

- Global search/command palette UI chrome (adapter interface exists; no UI built — no confirmed
  backend endpoint to build it against yet).
- Saved-view persistence (currently UI-only affordance).
- Platform Configuration change-history list/diff view.
- Finance Hub tab consolidation of the 5 orphaned pages restored to the sidebar this phase.
- Automated a11y tooling pass (axe/Lighthouse) and manual screen-reader pass.
- i18n framework adoption and string extraction.
- Light/dark snapshot tests, keyboard-focus-order test, long-label overflow regression test,
  Audit Explorer expand/collapse test (see `frontend-test-plan.md`'s "not yet written" section).
- Wiring any `Ux02DataAdapter` implementation against real endpoints (currently all showcase pages
  import fixture arrays directly).
- Production cutover of `UX02_NAV_GROUPS` into `AdminLayout.tsx` (see
  `product-decisions-required.md` item 1).
