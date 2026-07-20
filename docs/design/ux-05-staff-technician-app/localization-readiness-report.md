# Localization Readiness Report

## What this is (and isn't)
No i18n infrastructure exists in this app (no string catalog, no `t()`/translation-loading mechanism, no
locale-switching) — building that is real, separate infrastructure work, not attempted this round. This is a
**spot-check**: real, full-length Hindi and Punjabi sentences (not lorem ipsum, not single words) dropped
directly into a handful of already-built components, to see whether layout/text-wrapping breaks on genuinely
long translated content, per the coordinator's explicit "no need to build full i18n, just verify wrapping"
request.

## What was checked
`LocalizationShowcaseScreen` (new dev-only screen) renders:
- A ~180-character real Hindi sentence (a customer describing an AC issue) inside `CustomerContactCard`'s issue
  summary and `PermissionRestrictedState`'s reason text — both have no `numberOfLines` prop, so they should wrap
  to as many lines as needed rather than clip.
- A ~110-character real Punjabi sentence inside `NotificationCard`'s body — which **intentionally** sets
  `numberOfLines={2}` (correct behavior in a scrollable notification list, not a localization bug).
- Punjabi city/name text inside `AddressCard`.

## What was found
- `CustomerContactCard` and `PermissionRestrictedState` render the full long Hindi string with no truncation
  (verified via RNTL exact-text-match assertions in
  `src/screens/ux05/__tests__/LocalizationShowcaseScreen.test.tsx` — 4 real tests, all passing) — neither
  component has a fixed-width container or a `numberOfLines` that would clip it.
- `NotificationCard`'s 2-line clamp on the Punjabi body behaves as intended (partial text renders, matched via a
  prefix regex in the test, not an exact match) — this is deliberate list-context truncation, not something to
  "fix."
- `AddressCard` renders the Punjabi city/state text without truncation.

## Real limitation of this check
RNTL/Jest render text into a virtual DOM-like tree, not a real laid-out screen with actual pixel wrapping — this
check proves **no component accidentally truncates** (no unexpected `numberOfLines`, no silently-clipped Text)
but does NOT prove pixel-perfect visual wrapping on an actual device/screen width. A true visual check would
need a real device/emulator render or a Playwright screenshot comparison against the Expo web bundle at a
mobile viewport width — not attempted this round (would require navigating to an authenticated dev-showcase
route in the browser smoke check, which isn't reachable without a real login — see `runtime-test-report.md`).

## Not checked
- Date/time/currency/number formatting for `hi`/`pa` locales (no formatting-helper layer exists in this app at
  all yet — every date is formatted with a hardcoded `"en-IN"` locale string, e.g. `new Date(...).toLocaleString
  ("en-IN", ...)` in `HomeScreen`/`JobDetailScreen`/`NotificationsScreen` — a real, disclosed gap).
- Right-to-left layout (not applicable to Hindi/Punjabi, both left-to-right scripts).
- Font rendering/glyph support verification on a real device (Devanagari/Gurmukhi script rendering was not
  visually confirmed outside the Playwright DOM check, which does render real glyphs via system fonts on the
  headless Chromium instance, but this wasn't specifically screenshotted or reviewed).
