# Deferred to a Follow-Up Pass — UX-07 Pass 3d

Given the full brief's scope (a targeted Home + SmartBot redesign, plus
responsive matrix, 320px certification, accessibility audit, and
Playwright/visual-evidence work — each independently large), the following
was honestly deferred rather than rushed or claimed done:

1. **Guided SmartBot flow — full Part B visual restructure.** Only the
   category-handoff mechanism (skip re-asking category) and a compact
   context header were built. Not built: an explicit "Step X of Y" /
   segmented progress indicator, a compact expandable "answers so far"
   summary, and auto-advance-vs-explicit-Continue differentiation for a
   multi-select step (no multi-select step exists in the current flow to
   differentiate against yet). See `guided-smartbot-design-contract.md`.
2. **Responsive width matrix / 320px certification** for the redesigned
   Home and SmartBot screens — not performed. No CSV or certification
   document was written claiming this work; this note is the honest
   record of the gap.
3. **Accessibility audit** (screen-reader pass, contrast re-verification
   beyond reusing existing theme tokens, focus-order review) for the
   redesigned screens — not performed.
4. **Playwright / visual-evidence capture** for the redesigned Home and
   SmartBot screens — not performed; no visual-evidence document or CSV
   entry was written claiming otherwise.
5. **ESLint** was not run this pass (same gap carried from Pass 2 — see
   `typecheck-build-lint-report.md`'s Pass 3d addendum).
6. **Home's saved-location chip** remains an honest placeholder (routes to
   the real Address Book) rather than real "default address" data — no
   backend endpoint for that exists today (see `known-limitations.md`).
7. **The pre-existing react/react-native-renderer version mismatch**
   (react-native 0.85.0 peer-depends on react ^19.2.3; this repo pins
   react 19.2.0) was discovered this pass but not fixed — it's an
   environment/dependency-version issue outside this pass's presentation-
   only scope, worked around locally in the 3 new test files only. See
   `known-limitations.md` for the full writeup and
   `theme-stability-non-regression.md`/`customer-test-report.md` for the
   scoped test-file workaround.

None of the above were claimed complete in any status report; this
document is the explicit record of what a genuine Pass 4 (or later) should
pick up.
