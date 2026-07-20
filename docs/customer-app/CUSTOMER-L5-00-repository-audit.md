# CUSTOMER-L5-00 — Repository Audit

Date: 2026-07-12
Scope: `mobile/customer-app` (the customer-facing Expo/React Native app).

## 1. Current Repository Condition

`mobile/customer-app` is **not empty**. It is a working, already-shipped Expo app with
real screens wired to the live ServiceOS backend (auth, bookings, jobs, chat, AI chat,
reviews, invoices, addresses, payments, settings, help). It has its own Python test
file (`tests/test_customer_app.py`, 55 assertions) that checks file existence, not
runtime behavior (no Jest/RNTL tests exist).

There is a sibling `mobile/staff-app` with a similar structure (not touched by this
sprint).

This sprint's directive to avoid implementing booking/auth/etc. applies to **new**
work in this sprint, not to the pre-existing app. Per section 36 ("Migration
Requirements") and the explicit instruction "Do not rewrite working code without
evidence" / "Preserve working behavior", **all existing screens, navigation, and API
calls are preserved as-is**. This sprint adds an architecture/design-system foundation
alongside the existing code, wires the theme/error-boundary/query-client into the root
`App.tsx` without changing existing screen behavior, and leaves full screen-by-screen
migration onto the new primitives as an explicitly deferred item (see
`known-gaps.md`).

## 2. Detected Technologies

| Concern | Finding |
|---|---|
| Package manager | npm (`package-lock.json` present, no yarn.lock/pnpm-lock) |
| Platform | Expo managed workflow, SDK 56 |
| React Native | 0.85.0 |
| React | 19.2.0 |
| TypeScript | 5.8.3, `strict: true` already enabled (extends `expo/tsconfig.base`) |
| Navigation | React Navigation 7 (native-stack + bottom-tabs), imperative screen list in `AppNavigator.tsx`, no typed param lists |
| State management | None — local `useState`/`useEffect` only; `AuthContext` (React Context) for session |
| Server state | None — manual `fetch`-wrapper (`src/lib/api.ts`) + `useApi` hook, no caching/retry/dedup |
| Forms | None — controlled inputs with local state per screen |
| Validation | None (no Zod/Yup) |
| Styling | Single flat `theme.ts` object (`StyleSheet.create` + inline styles per screen); no light/dark mode, no semantic token layer |
| Component library | Small ad hoc set: `Button`, `Card`, `Skeleton`, `StarRating`, `JobStatusBadge`, `BookingCard` — not systematized, no accessibility props, no variants/sizes API |
| Testing | Python file-existence checks only; **no Jest, no React Native Testing Library configured** |
| Linting/formatting | `eslint src --ext .ts,.tsx` script exists but **no `.eslintrc*` file present** — lint currently cannot run meaningfully; no Prettier config |
| Build config | `app.json` + `eas.json` (EAS Build profiles: development/preview/production) |
| Env handling | `process.env.EXPO_PUBLIC_API_URL` read directly in `src/lib/api.ts` with a `localhost` fallback baked into source; `.env.example` exists, no validation, no environment-name concept, no protection against a production build using `localhost` |
| Native setup | Managed Expo — no `ios/`/`android/` folders (expected for managed workflow) |
| CI | No CI workflow specific to `mobile/customer-app` found under `.github/` |
| Existing screens/routes | 19 screens wired in `AppNavigator.tsx` + `TabNavigator.tsx`, string-based route names, no typed params |
| API client | `src/lib/api.ts` — single file, typed request/response shapes, custom `ServiceOSError`, token injection via AsyncStorage, but no timeout, no cancellation, no retry policy, no correlation IDs, no redaction |
| Error handling | Per-screen `try/catch` + inline error text; no root error boundary; no normalized error categories beyond `ServiceOSError` |
| Theme | Single light theme only; colors/spacing/radius/shadow in one object; no dark mode; raw hex values used directly in some screens (e.g. `"#fff"` in `TabNavigator.tsx`) |
| Localization | `src/lib/i18n.ts` exists but is **not a localization framework** — it is a hand-rolled dictionary for one specific AI chatbot flow (`SmartBotScreen`), keyed by `pa`/`hi`/`en`. No i18next, no namespace system, no pluralization, no number/date formatting, no persisted locale preference beyond the bot's local state |
| Analytics/logging/crash reporting | None. No logger abstraction; screens do not currently use `console.log` for business logic (clean in that respect) |
| Accessibility | Not implemented — no `accessibilityRole`/`accessibilityLabel`/`accessibilityState` usage found in existing components |
| Secure storage | **None** — auth token stored in plain `AsyncStorage` (`STORAGE_KEYS.token`), not SecureStore/Keychain. This is a real security gap fixed by this sprint's storage foundation (used by future auth sprint, not retrofitted onto `AuthContext` here to avoid an unreviewed auth behavior change). |

## 3. Useful Existing Implementation (kept as-is)

- `src/lib/api.ts` request/response typing conventions and `ServiceOSError` shape —
  informed the new `api/api-errors.ts` normalized categories.
- `AuthContext` + `AppNavigator` auth-gated stack — untouched; still the real app entry
  flow.
- Screens and their business logic — untouched.
- `.env.example` — extended with the new documented keys.

## 4. Unsafe or Weak Patterns Found

- Auth token in `AsyncStorage` instead of secure storage (see above; not silently
  auto-migrated in this sprint — that migration touches live auth behavior and belongs
  to the authentication sprint, tracked in `known-gaps.md`).
- Direct `process.env.EXPO_PUBLIC_API_URL` access with a hardcoded `localhost`
  fallback that would silently ship in a production build if the env var were unset.
- No environment validation — a production build could point at `localhost` with no
  build-time failure.
- No root error boundary — an uncaught render error currently white-screens the app.
- Raw color literals directly in `TabNavigator.tsx` (`"#fff"`) bypassing `theme.ts`.

## 5. Duplicate Implementations

- Two `AIChatResponse` interfaces and two ad hoc `aiApi`/`aiChatApi` objects exist in
  `src/lib/api.ts` (lines documented in file) — pre-existing duplication, left as-is
  per "do not rewrite working code without evidence"; flagged here for a future
  cleanup sprint rather than fixed silently in this architecture sprint.

## 6. Architectural Conflicts

- The target `src/` layout in this spec conflicts with the current flat
  `src/{components,context,hooks,lib,navigation,screens,styles}` layout. Resolution:
  **additive migration** — this sprint creates the new
  `design-system/`, `config/`, `api/`, `storage/`, `state/`, `logging/` (as
  `observability/`), `hooks/`, `navigation/route-types.ts`, `components/` (design
  system primitives) folders alongside the existing ones. The existing
  `screens/`, `context/`, `lib/`, `styles/` folders are untouched. Feature-folder
  restructuring (`features/booking-assistant/`, etc.) is deferred — there is no
  evidence yet of which screens map to which future feature boundaries, and forcing
  that split now would be a blind rewrite.

## 7. Missing Foundations (built in this sprint)

Design tokens, theme system (light/dark/system + persistence), storage adapters
(secure vs preference), validated environment config, API-client foundation with
normalized errors, structured logger with redaction, root error boundary, query-client
foundation, connectivity foundation, accessible primitive component set, localization
infrastructure (i18next), icon adapter, and a development-only Design System Showcase
screen.

## 8. Dependencies Kept

`expo`, `expo-status-bar`, `expo-location`, `expo-notifications`, `expo-image-picker`,
`react`, `react-native`, `@react-native-async-storage/async-storage`,
`@react-navigation/*`, `react-native-safe-area-context`, `react-native-screens`,
`react-native-maps`, `@expo/vector-icons`. All are stable, actively used, and
technically sound for their current purpose.

## 9. Dependencies Added

See `dependency-decisions.md` for full justification per package. Summary: TanStack
Query, Zustand, React Hook Form, Zod, `expo-secure-store`, `i18next` +
`react-i18next`, `expo-localization`, Jest + `jest-expo` + React Native Testing
Library + `@testing-library/jest-native`, ESLint (`eslint-config-expo`) + Prettier.

## 10. Dependencies Removed or Replaced

None removed. Nothing in the existing dependency set was unsound.

## 11. Migration Risks

- Introducing `expo-secure-store` for future token storage without migrating the live
  `AuthContext` today creates a temporary two-pattern state (documented in
  `known-gaps.md`) — accepted risk, avoids an unreviewed behavior change to a working
  login flow in a sprint explicitly scoped to exclude authentication work.
- Adding ESLint config where none existed will surface pre-existing lint violations in
  untouched screens; the new config is scoped to warn, not fail, on pre-existing
  screen code so this sprint does not silently break CI over legacy files (see
  `dependency-decisions.md`).

## 12. Implementation Decisions Made in This Sprint

1. Additive architecture — new folders alongside existing ones, no deletions.
2. Root `App.tsx` gains `AppProviders` (theme, query client, i18n) wrapping the
   existing `AuthProvider`/`AppNavigator` tree, plus a root `ErrorBoundary`. This is
   the only change to existing runtime wiring, and it does not alter any screen.
   `App.tsx` remains for the real app entrypoint.
3. A `__DEV__`-gated route (`DesignSystemShowcase`) is added to the existing
   `AppNavigator` stack so it is reachable only in development builds and never
   ships in production (guarded via a `__DEV__` check, not just a config flag).
4. Localization ships English, Hindi, and Punjabi translations for shared system
   strings only (per section 27); the existing bot-specific `src/lib/i18n.ts` is left
   untouched since it is booking-assistant business content, not shared system UI.

## 13. Deferred Concerns for Later Sprints

See `known-gaps.md`.
