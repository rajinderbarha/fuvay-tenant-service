# Accessibility Report

## Verified (via Vitest + Testing Library, real assertions)
- **Focus trap**: `Modal.test.tsx` renders an open modal and asserts `Tab`/
  Shift+Tab cycling stays inside the dialog (implemented via a manual
  `keydown` listener over `querySelectorAll(FOCUSABLE)`), and `Escape`
  closes it (`onClose` called once).
- **Escape-to-close**: verified for both `Modal` and `Drawer`.
- **ARIA roles**: `Modal`/`Drawer` render `role="dialog"` + `aria-modal="true"`
  + `aria-label`; `Alert` uses `role="alert"` for danger tone and
  `role="status"` otherwise; `Tooltip` uses `role="tooltip"` +
  `aria-describedby`; `Spinner` uses `role="status"` + `aria-label`.
- **Icon-only labeling**: `Button variant="icon"` warns in the console if
  rendered without `aria-label` (manually verified in the showcase page).
- **Unknown-status safety**: `StatusBadge.test.tsx` confirms an unregistered
  status string renders a readable fallback rather than crashing or
  rendering blank.
- **Keyboard reachability**: all interactive components (`Button`, form
  fields, `Modal`/`Drawer` close buttons) are native `<button>`/`<input>`/
  `<select>` elements — no custom `<div onClick>` controls — so they are
  tab-reachable and activate on Enter/Space by default.
- **Focus-visible ring**: `.ds-focus-visible:focus-visible` applies
  `box-shadow: var(--focus-ring)` (2px background offset + brand color),
  visible in both themes, only on keyboard focus (not mouse click) via the
  native `:focus-visible` pseudo-class.
- **Reduced motion**: `theme.css` includes a global `@media
  (prefers-reduced-motion: reduce)` block zeroing all animation/transition
  durations; `motionDuration()` helper is the JS-side equivalent.

## Not verified (would need a real browser + axe/manual screen-reader pass)
- Actual screen-reader announcement behavior (NVDA/VoiceOver) — not run in
  this environment (jsdom only, no AT emulation).
- Full-page color-contrast audit across every existing feature page — only
  the new component library's token pairs were reviewed by eye against WCAG
  AA (body text vs. surface, badge text vs. badge background); no automated
  contrast-ratio tool was run. Flagged as a follow-up in
  `known-limitations.md`.
