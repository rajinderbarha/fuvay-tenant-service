# UX-07 Pass 3f — Accessibility Audit + Remediation (Home / SmartBot / booking-flow modal / bottom nav)

## Scope and honesty statement

This is a **bounded, critical-pass accessibility review**, not a WCAG
certification. It covers exactly the four surfaces named in this pass's
brief: `HomeScreen.tsx`, `DeepSeekChatScreen.tsx` (including the guided
booking-flow modal and the language-selector modal it also renders), and
`TabNavigator.tsx` (bottom nav). No other screen was audited this pass.

Per the coordinator's mid-task correction, **Part 1 (responsive/width
certification) was explicitly descoped** — see `known-limitations.md`.
This document covers Part 2 only.

## Method

Manual source read of all three files line-by-line, checking every
`TouchableOpacity`/`TextInput`/interactive `View` for:
`accessibilityLabel`, `accessibilityRole`, `accessibilityState`
(selected/disabled/busy/expanded), touch-target size (`hitSlop` where the
visual box is under ~44x44), modal semantics
(`accessibilityViewIsModal`), and loading-state announcement. Each finding
recorded in `home-smartbot-accessibility-audit.csv` with a
CRITICAL/HIGH/MEDIUM/LOW severity and a fix-status column.

## Findings summary

- 1 CRITICAL: language-picker option rows in `DeepSeekChatScreen.tsx` had
  **no accessibility props at all** — a screen-reader user could not
  identify or choose a language. **Fixed.**
- 2 HIGH: (a) bottom-tab icons exposed only a text label describing
  selection state, with no `accessibilityRole="tab"` /
  `accessibilityState={{selected}}` for assistive tech that relies on
  structural roles rather than parsing label text; (b) the guided
  booking-flow modal lacked `accessibilityViewIsModal` (the sibling
  language-selector modal already had it — an inconsistency, not a new
  idea); (c) the three price-tier buttons (low/mid/high) — a primary
  booking decision point — had no accessibility props whatsoever. **All
  fixed.**
- 7 MEDIUM: icon-only touch targets under ~44x44 without `hitSlop`
  (notifications icon, profile avatar, guided-flow back/close button);
  several primary flow buttons ("Start Conversation", "Check
  availability", "Confirm Booking", "Continue with this price") missing
  `accessibilityRole`/`Label`/`accessibilityState={{disabled,busy}}`
  despite visibly changing to a busy/disabled state; the three guided-flow
  text inputs (issue/address/city) relying on placeholder text alone
  instead of an explicit `accessibilityLabel`. **All fixed.**
- Several LOW items (View Booking button, decorative trust-row icons,
  handoff/serviceability notice text, per-loading-state live-region
  announcements) were reviewed and **deferred** — see
  `known-limitations.md` for the explicit list and reasoning. None of
  these block a screen-reader user from completing the core booking flow;
  they are refinements, not blockers.

**Every CRITICAL and HIGH finding was fixed for real** (actual props
added, verified in source and covered by new or existing tests where
meaningfully testable — see below). No MEDIUM/LOW item was silently
dropped; all are itemized in the CSV and in `known-limitations.md`.

## What was NOT done (explicit)

- No automated axe-core/accessibility-linter pass was run (none is wired
  into this repo's toolchain); this audit is manual source review only.
- No real device/screen-reader (VoiceOver/TalkBack) manual walkthrough was
  performed — that would require a physical or simulator session outside
  this pass's time budget. The fixes are the standard React Native
  accessibility API surface, and are exercised by new unit tests using
  React Native Testing Library's accessibility-prop assertions
  (`getByLabelText`, `.props.accessibilityRole`,
  `.props.accessibilityState`), but that is not equivalent to a live
  screen-reader pass.
- LoginScreen, BookingsListScreen, NotificationsScreen, ProfileScreen, and
  every other screen were **not** audited this pass (out of the named
  scope).

## Files changed

- `mobile/customer-app/src/screens/HomeScreen.tsx` — `hitSlop` on the
  notifications icon and profile-avatar icon-only buttons.
- `mobile/customer-app/src/navigation/TabNavigator.tsx` —
  `accessibilityRole="tab"` + `accessibilityState={{selected}}` on
  `TabIcon`.
- `mobile/customer-app/src/screens/DeepSeekChatScreen.tsx` — language
  option rows (role/label/selected state), price-tier buttons
  (role/label/disabled+busy state), standard-price/confirm/check-
  availability/start-conversation/view-booking buttons
  (role/label/disabled+busy where relevant), guided-flow text inputs
  (accessibilityLabel), guided-flow modal (`accessibilityViewIsModal`),
  guided-flow back button (`hitSlop`).
- `mobile/customer-app/src/navigation/__tests__/TabNavigator.test.tsx` —
  new test asserting the focused tab exposes `accessibilityRole="tab"`
  and `accessibilityState={{selected:true}}`.
- `mobile/customer-app/src/screens/__tests__/DeepSeekChatScreen.guidedFlow.test.tsx`
  — 2 new tests: the guided-flow modal's back/close control has an
  accessible label + role + `hitSlop`; the language-picker's English
  option exposes `accessibilityRole="button"` and
  `accessibilityState={{selected:true}}` when English is the active
  language.
