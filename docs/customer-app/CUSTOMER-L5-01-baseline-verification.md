# CUSTOMER-L5-01 — Baseline Verification (CUSTOMER-L5-00)

Date: 2026-07-13
Method: re-ran the actual commands (not trusted from memory) — `npx tsc --noEmit`,
`npx eslint src --ext .ts,.tsx`, `npx prettier --check`, `npx jest`, `npx expo-doctor` —
against the current `mobile/customer-app` working tree, and read the CUSTOMER-L5-00
docs against the code they describe.

## 1. Previous Sprint Status

CUSTOMER-L5-00 was closed as **PARTIAL** (its own final report), not a hard PASS —
the architecture/design-system/infrastructure baseline was complete and gated, but
device-level accessibility and Android/iOS build validation were not possible in the
sandboxed environment. That self-assessment is confirmed accurate by this
verification: nothing further was discovered that contradicts it.

## 2. Verified Implementation

Re-ran every automated gate from CUSTOMER-L5-00 §7 against the current tree:

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | 31 errors, all inside pre-existing `src/screens/*.tsx` (unrelated to L5-00/L5-01 scope, documented in known-gaps.md). Zero errors in `src/design-system`, `src/api`, `src/storage`, `src/observability`, `src/config`, `src/state`, `src/components/{primitives,forms,feedback,layout}`, `src/app`, `src/navigation/route-*`. |
| `npx eslint src --ext .ts,.tsx` | 0 errors, 36 warnings, all in the same pre-existing screens. |
| `npx prettier --check` | Passes (pre-existing legacy files excluded via `.prettierignore`, documented). |
| `npx jest` | 16/16 suites, 88/88 tests passing. |
| `npx expo-doctor` | Same 3 pre-existing findings as L5-00's report (missing `assets/icon.png`, duplicate transitive `expo-constants`, several pre-existing packages behind the SDK-56 matrix). No new findings. |

Root providers (`AppProviders.tsx`): ThemeProvider → QueryClientProvider → ErrorBoundary
wrap the app tree; `AppBootstrap.tsx` hydrates the persisted locale and initializes
i18next before first render; confirmed by reading `src/App.tsx` — matches
`architecture.md` §1 and `design-system.md` §8. Theme and localization startup are
deterministic: `ThemeProvider` resolves `system → useColorScheme()` synchronously on
first render and only re-renders once hydration of the *persisted preference*
completes (tested by `theme-provider.test.tsx`); i18next is initialized with the
persisted locale (or system-detected fallback) before `AppContent` renders the real
navigator, so there is no language flash. This is a solid foundation for this
sprint's stricter startup-phase requirements, but L5-00 did not implement discrete,
observable startup phases — that is exactly this sprint's job, not a defect.

## 3. Missing Previous-Sprint Requirements

None found relative to CUSTOMER-L5-00's own acceptance criteria. The known gaps are
the ones L5-00 already declared in `known-gaps.md` (auth token still in AsyncStorage,
existing 19 screens not migrated onto new primitives, AppNavigator/TabNavigator still
using untyped string routes, no device-level a11y pass, 6 pre-existing packages behind
SDK version, no Android/iOS build validation possible in this environment).

## 4. Defects Discovered (new, found during this verification)

1. **No `scheme` registered in `app.json`.** CUSTOMER-L5-00 did not touch native
   linking configuration (out of its scope). This sprint's deep-link work requires a
   real registered scheme to be testable/functional, so it is added here (see
   `deep-linking.md`).
2. **`environment.ts`'s `deepLinkScheme` default (`"serviceos"`) had no corresponding
   native registration** — the env var existed but nothing consumed it. Fixed by this
   sprint's `linking-config.ts` + the new `app.json` `scheme` field.

Neither is a P0/P1 blocker to *starting* this sprint — they are exactly the gap this
sprint closes.

## 5. Blockers

None. CUSTOMER-L5-00's infrastructure (theme, storage, logger, api-client, error
boundary, query client) is stable and reusable as-is for the startup orchestrator and
remote-config client this sprint adds.

## 6. Corrective Work Performed

- Added `"scheme": "serviceos"` to `app.json` (additive, no existing native config
  removed).
- No other CUSTOMER-L5-00 file required correction — the 31 pre-existing screen
  TypeScript errors and 36 lint warnings are left as documented, unrelated legacy
  debt (see `known-gaps.md`), not touched by this sprint since fixing them means
  editing business-logic screens with no independent test coverage, which is out of
  scope for both L5-00 and L5-01.

## 7. Deferred Non-Blocking Issues

Carried forward unchanged from CUSTOMER-L5-00 `known-gaps.md`; this sprint adds its
own new deferred items to the same file rather than duplicating a second gaps list.
