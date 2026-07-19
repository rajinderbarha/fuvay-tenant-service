# Platform Configuration Pattern

Showcase: `/dev/ux-02/settings` (`app/dev/ux-02/settings/page.tsx`). Readiness:
`PRODUCT_DECISION_REQUIRED` (whether these settings get a real write path is a product decision,
not just an engineering task).

## Layout
Section cards, one per setting: current value, "last changed by / when", an Edit button.

## Unsaved-change protection
Clicking Edit marks the page dirty; a `role="status"` banner warns that navigating away discards
changes — this is a design-only guard (no real form/dialog/router-block wired yet), explicitly
labeled as such in the source comment.

## Read-only mode
A `readOnly` flag (currently hardcoded false in the showcase) disables the Edit button — the real
implementation would derive this from the user's canonical role (e.g. `admin_readonly` always
read-only) rather than a local flag.

## Not built
Change history list/diff view — deferred, see `deferred-items.md`.
