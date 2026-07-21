# Frontend File Change Report

Exactly one frontend source file changed this round:

- `mobile/customer-app/src/lib/chatLanguages.ts` — narrowed `CHAT_LANGUAGES`
  from a 14-entry BCP-47 registry to exactly 3 entries
  (en/hi/pa = English/हिन्दी/ਪੰਜਾਬੀ), per this phase's explicit requirement.
  Grep-confirmed sole consumer: `mobile/customer-app/src/screens/DeepSeekChatScreen.tsx`.
  No other file imports this module. See `smartbot-language-verification.md`
  for the full rationale and what was NOT changed (the selector UI itself,
  the `withLanguageInstruction()` mechanism).

No other frontend file (super-admin, tenant-portal, mobile/staff-app, or
any other mobile/customer-app file) was modified in Round 1.

## Round 2

Exactly one additional frontend file changed:

- `frontend/tenant-portal/package.json` — added
  `"@testing-library/dom": "^10.4.0"` as an explicit devDependency (a
  missing peer dependency of the already-pinned
  `@testing-library/react@^16.0.1`). See `frontend-corrections-report.md`
  for full justification. This is the ONLY code change made in Round 2 —
  every other Round 2 change is a new or appended documentation file.

No other frontend file was modified in Round 2. A real, precisely-diagnosed
React-version-pin mismatch was found in the SAME file
(`frontend/tenant-portal/package.json`'s `react`/`react-dom: 19.2.7` vs
`frontend/super-admin/package.json`'s `19.2.0`) but was deliberately NOT
changed this round — see `frontend-corrections-report.md`'s "Correction
considered but NOT made" section for the full reasoning.

## Round 3

Three files changed, net:

- `frontend/super-admin/package.json` — added `vitest`,
  `@testing-library/jest-dom`, `@testing-library/react`,
  `@testing-library/dom`, `@testing-library/user-event`, `jsdom` as
  devDependencies, and a real `"test": "vitest run"` script. This is
  wiring up MISSING test infrastructure (Round 2's found gap), not a
  version upgrade of anything already pinned.
- `frontend/super-admin/vitest.config.ts` — NEW file, an exact mirror of
  `frontend/tenant-portal`'s own existing, working config (jsdom
  environment, react/react-dom dedupe hint, same exclude patterns) — not
  an invented configuration, a copy of this repo's own proven pattern.
- `frontend/super-admin/test-setup.ts` — NEW file, identical 1-line
  content to tenant-portal's own (`import "@testing-library/jest-dom/vitest"`).

**Root `package.json`'s `overrides` field was added, tested, found to
regress a different test set, and REVERTED this round** — net change to
this file across the whole round: **zero** (confirmed via
`git diff -- package.json` showing no diff after the revert). See
`react-version-pin-investigation.md` for the full attempt-and-revert
narrative.

No other frontend file was modified in Round 3.

## Round 4, Pass 2 (customer-app dark mode / responsive / accessibility)

All changes are inside `mobile/customer-app/`. No backend, migration, seed-script,
super-admin, tenant-portal, or staff-app file was touched.

### New files
- `mobile/customer-app/src/context/ThemeContext.tsx` — ThemeProvider/useTheme:
  System/Light/Dark preference, AsyncStorage persistence
  (`customer_app_theme_preference`), system-scheme listener, `isLoaded` gate to
  avoid a flash-of-wrong-theme.
- `mobile/customer-app/src/context/__tests__/ThemeContext.test.tsx` — real tests.
- `mobile/customer-app/src/styles/__tests__/theme.test.ts` — real tests for the
  dark palette contract.

### Modified files (reason)
- `src/styles/theme.ts` — added a full dark palette (`buildTheme("dark")`)
  alongside the existing light palette, new surface-hierarchy tokens
  (surfaceRaised/surfaceInteractive/surfaceSelected/surfaceDisabled), chat-bubble
  tokens, `statusBarStyle`. Kept the static `theme` export (light) for backward
  compatibility with not-yet-migrated screens.
- `src/lib/jobStatus.ts` — added `CUSTOMER_STATUS_COLOR_DARK`, a dark-mode-legible
  variant of the existing status color map.
- `src/App.tsx` — wraps the tree in `ThemeProvider`; moved `<StatusBar/>` out (now
  rendered by AppNavigator, theme-driven).
- `src/navigation/AppNavigator.tsx` — theme-aware header colors, React Navigation
  `theme` prop (light/dark `NavigationContainer` theme), theme-driven `<StatusBar/>`,
  loading gate now also waits on `ThemeContext.isLoaded`.
- `src/navigation/TabNavigator.tsx` — theme-aware tab bar colors; accessibility
  labels on tab icons.
- `src/components/Card.tsx`, `Button.tsx`, `JobStatusBadge.tsx`, `Skeleton.tsx`,
  `StarRating.tsx`, `BookingCard.tsx` — migrated from the static `theme` import to
  `useTheme()` so every screen using these shared components (the majority of the
  app) gets working dark mode without per-screen changes. Added accessibility
  roles/labels/states, 44px-minimum tap targets, and made `Skeleton` respect the
  platform Reduce Motion setting.
- `src/screens/SettingsScreen.tsx` — migrated to `useTheme()`; added a real
  System/Light/Dark appearance selector (client-side preference only).
- `src/screens/LoginScreen.tsx` — migrated to `useTheme()`; input labels, error-
  region accessibility semantics.
- `src/screens/HomeScreen.tsx` — migrated to `useTheme()`; category grid uses
  `surfaceRaised` instead of hardcoded light pastel backgrounds in dark mode, with
  a dark-legible `TYPE_COLOR_DARK` pill variant; removed the screen-local
  hardcoded `StatusBar` (now global).
- `src/screens/DeepSeekChatScreen.tsx` (SmartBot) — migrated to `useTheme()`; chat
  bubbles switched to dedicated `bubbleCustomer*`/`bubbleAssistant*` tokens;
  accessibility labels on header controls, bubbles, composer, language-selector
  modal (added a close button, previously missing).

### Explicitly NOT changed this pass
- No backend file, migration, or seed script.
- No super-admin, tenant-portal, or staff-app production source.
- 14 remaining customer-app screens (BookingsList/BookingDetail/Chat/JobTracking/
  Profile/Review/Notifications/AddressBook/ServiceHistory/ServiceDetail/
  HelpSupport/PaymentMethods/Invoice/QuoteApproval) still import the static
  (light-only) `theme` export — see `known-limitations.md`, "Round 4 Pass 2"
  section, for the concrete user-facing consequence (partial dark mode).
