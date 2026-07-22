# Customer Source Change Report — Pass 3c

Only one file changed in this pass:

| File | Reason |
|---|---|
| `mobile/customer-app/src/context/__tests__/ThemeContext.test.tsx` | Added a deterministic mock for `Appearance.addChangeListener` (previously unmocked, causing an intermittent race with the real environment's live color-scheme signal) — test-infrastructure fix only. |

No production source file (`ThemeContext.tsx`, any screen, any shared
component) was modified in this pass. No new dependency, script, or config
file was added.

An unrelated drift in `app.json`/`package.json` (Expo SDK/react version
downgrade, caused by an external `expo start` process auto-adjusting
versions) was found in the working tree before this pass began and was
reverted via `git checkout --` without being committed — it is not part of
this pass's change set and predates it.

## Pass 3d addendum

8 files changed across 3 commits (`13c818f`, `be43db2`, `b3a0fa0`):

| File | Reason |
|---|---|
| `mobile/customer-app/src/screens/HomeScreen.tsx` | Full IA rebuild: search entry, SmartBot CTA, real active-booking/empty states, popular-service tiles (no premature badges, no emoji), trust row, honest greeting fallback. |
| `mobile/customer-app/src/screens/__tests__/HomeScreen.test.tsx` | New — 6 real behavioral tests for the above. |
| `mobile/customer-app/src/screens/DeepSeekChatScreen.tsx` | Added optional `route.params.initialCategoryLabel` handling: auto-session-start, auto-open booking flow, real-category fuzzy match (skip re-asking), honest no-match notice, compact category-context header. |
| `mobile/customer-app/src/screens/__tests__/DeepSeekChatScreen.handoff.test.tsx` | New — 3 real behavioral tests for category handoff + language-switch state preservation. |
| `mobile/customer-app/src/navigation/TabNavigator.tsx` | Narrowed to exactly 5 tabs (Home/Bookings/SmartBot/Notifications/Profile); emoji → `@expo/vector-icons`; typed `AIAssistant` route params. |
| `mobile/customer-app/src/navigation/AppNavigator.tsx` | Added a `Chat` root-stack screen (title "Messages") so the human/provider support surface stays reachable after leaving the primary tab bar. |
| `mobile/customer-app/src/screens/ProfileScreen.tsx` | Added a "Messages" row under Support, navigating to the new `Chat` stack route. |
| `mobile/customer-app/src/navigation/__tests__/TabNavigator.test.tsx` | New — 2 real behavioral tests (exactly 5 non-wrapping tabs; no standalone "Chat" tab label). |

No backend file, no other mobile app (`staff-app`), no `app.json`, and no
dependency version in `package.json` was changed this pass (confirmed —
see `package-config-drift-report.md`).

## Pass 3f addendum (accessibility remediation)

Files changed (all `mobile/customer-app/`):

- `src/screens/HomeScreen.tsx` — added `hitSlop` to the notifications-icon
  and profile-avatar icon-only touchables (both 36x36 visual boxes, under
  the ~44x44 recommended touch target).
- `src/navigation/TabNavigator.tsx` — `TabIcon` now sets
  `accessibilityRole="tab"` and `accessibilityState={{selected:focused}}`
  in addition to its pre-existing `accessibilityLabel`.
- `src/screens/DeepSeekChatScreen.tsx` — see
  `accessibility-remediation-report.md` for the full itemized list;
  summary: added accessibility props (role/label/state) to the
  language-picker option rows (was a CRITICAL gap — no props at all),
  the 3 price-tier buttons (was HIGH), the guided-flow modal
  (`accessibilityViewIsModal`, was HIGH), the guided-flow back button
  (`hitSlop`), the issue/address/city text inputs
  (`accessibilityLabel`), and the Start Conversation / Check availability
  / Confirm Booking / Continue with this price / View Booking buttons
  (role/label/disabled+busy state where applicable).
- `src/navigation/__tests__/TabNavigator.test.tsx` — 1 new test.
- `src/screens/__tests__/DeepSeekChatScreen.guidedFlow.test.tsx` — 2 new
  tests.

No screen outside this named scope (Home / SmartBot / booking-flow modal
/ bottom nav) was touched. No backend file was touched (see
`backend-non-change-report.md`).
