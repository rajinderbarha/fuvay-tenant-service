# Localization Readiness

## Current state: no i18n exists
Neither `super-admin` nor `tenant-portal` has an i18n library, locale
routing, or externalized string catalog today. All copy in both apps
(including the new design-system components) is hardcoded English JSX text/
props.

## What is ready for i18n later
- No component in `@serviceos/design-system` concatenates strings in a way
  that would break translation (no `"X of Y items"` string-built via
  template literals with embedded logic beyond simple interpolation).
- `StatusBadge`'s registry stores English labels centrally
  (`statusRegistry[key].label`) — swapping to a translation lookup keyed by
  the same status key is a contained change in one file.
- Numeric/date formatting in the showcase uses `toLocaleString("en-IN")`
  explicitly rather than assuming a locale, showing the pattern to extend
  to a dynamic locale later.
- Layout components (`PageHeader`, `Card`, `Modal`) don't hardcode text
  direction; flex-based layouts would need an `dir="rtl"` review but no
  component uses hardcoded `left`/`right` in place of logical properties in
  a way that would silently break RTL (a follow-up audit item, not fixed
  here).

## Not ready
No message-catalog structure, no `next-intl`/`react-i18next` wiring, no
pluralization handling. This was explicitly out of scope for UX-01
(foundation phase) — see `deferred-items.md`.
