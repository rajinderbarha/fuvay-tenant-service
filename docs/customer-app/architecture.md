# Customer App — Architecture

Scope: `mobile/customer-app`. This document describes the architecture established
by CUSTOMER-L5-00 and the rules future sprints must follow.

## 1. Layers and Dependency Direction

```
screens (existing) ──┐
                      ├─▶ components (design-system + feedback + forms + layout)
future features ──────┤        │
                      │        ▼
                      │   design-system (tokens, themes) ── no business imports
                      │
                      ├─▶ api (client, errors, request-context) ── no UI imports
                      ├─▶ storage (secure, preference) ── no UI imports
                      ├─▶ observability (logger, redaction) ── no UI imports
                      ├─▶ config (environment, app-config) ── no UI imports, no feature imports
                      └─▶ state (query-client) ── no UI imports
```

Dependencies only point downward: screens/features depend on components and
infrastructure; infrastructure never imports screens, features, or UI
components. `design-system/` never imports anything from `screens/`,
`context/`, or a future `features/*`.

## 2. Feature Boundaries

This sprint does not create `features/*` folders — see the repository audit
for why (no evidence yet of the correct split for the 19 existing screens).
When a later sprint introduces a feature folder, it must follow:

```
feature-name/
  api/       — feature-specific endpoints, built on top of api/api-client.ts
  components/
  domain/    — pure types/rules, no React
  hooks/
  screens/
  schemas/   — Zod schemas
  state/     — feature-local Zustand slice or React Query hooks, not global state
  types/
```

Only create the subfolders a feature actually needs.

## 3. State Boundaries

See `state-management-guidelines.md` for the full decision guide. Summary:
server data → TanStack Query (`src/state/query-client.ts`); durable
app-wide client state (theme preference, locale, connectivity) → the
relevant provider/hook in `design-system/` or `hooks/`; feature state → the
feature's own `state/`; screen-local interaction state → `useState` in the
screen.

## 4. API Boundaries

All HTTP calls go through `src/api/api-client.ts`. It:

- reads the base URL/timeout from `src/config/environment.ts` (never
  `process.env` directly),
- attaches request/correlation IDs, tenant, and locale headers via
  `src/api/request-context.ts`,
- resolves the auth token through a registered provider
  (`setAuthTokenProvider`) rather than importing storage or auth context
  directly — keeps the client decoupled from how auth is implemented,
- normalizes every failure into an `ApiError` with a stable `category`
  (`src/api/api-errors.ts`) so UI code never branches on raw HTTP status
  codes or server messages,
- only retries safe requests (GET, or a mutation carrying an
  `idempotencyKey`) and never retries a mutation silently.

The pre-existing `src/lib/api.ts` (used by all current screens) is left
in place — it is not migrated onto `api-client.ts` in this sprint (see
`known-gaps.md`).

## 5. Storage Boundaries

- `src/storage/secure-storage.ts` — keychain-backed (`expo-secure-store`).
  Reserved for tokens/session data. Nothing writes here yet in this sprint
  (auth is out of scope); the adapter exists so the auth sprint has it
  ready.
- `src/storage/preference-storage.ts` — `AsyncStorage`-backed. Only for
  non-sensitive preferences (theme, locale, onboarding, dev toggles).
- Auth tokens must never be written to `preference-storage`.

## 6. Navigation Boundaries

`src/navigation/route-names.ts` and `route-types.ts` define every route
identifier and its param shape in one place. Only `DesignSystemShowcase` is
actually registered as a reachable screen this sprint (dev-only, gated by
`__DEV__` in `AppNavigator.tsx`). The existing `AppNavigator.tsx` /
`TabNavigator.tsx` (string route names, no typed params) are left as-is —
migrating them to the typed route list is deferred (see `known-gaps.md`)
since it would touch 19 existing screens' navigation calls with no
independent test coverage to verify against.

## 7. Naming and Import Conventions

- Design-system primitive components are prefixed `App*` (`AppButton`,
  `AppText`, ...) to avoid collision with the pre-existing ad hoc
  `components/Button.tsx`, `components/Card.tsx`, etc., which remain in use
  by existing screens.
- Barrel exports (`design-system/index.ts`) re-export tokens/themes only —
  never re-export a file that itself has a circular dependency on the
  barrel.
- Feature code imports from `../../design-system/...` or
  `../../components/...`; the reverse import direction is prohibited.

## 8. Error Handling

- `src/app/ErrorBoundary.tsx` — root-level React error boundary, wraps the
  entire provider tree in `AppProviders.tsx`. Renders a themed fallback with
  a retry action and a generated error reference ID; logs through
  `observability/logger.ts`. The same component accepts a `section` prop
  for narrower, section-level boundaries in later sprints.
- API failures are normalized (`ApiError`) before reaching UI code; UI code
  branches on `error.category`, never on raw status/message text.

## 9. Observability

`src/observability/logger.ts` is the only sanctioned place to call
`console.*`; `src/observability/redaction.ts` strips sensitive keys
(tokens, OTP, passwords, phone/email/address, lat/lng, session IDs, etc.)
from any logged context before it reaches console output, a future crash
reporter, or analytics. Crash-reporting and analytics are pluggable
adapters (`setCrashReportingAdapter`, `setAnalyticsAdapter`) — no vendor is
wired in this sprint (none was specified/authorized).

## 10. Configuration Flow

```
.env(.local) → process.env.EXPO_PUBLIC_* → config/environment.ts (validated once at module load)
                                          → config/app-config.ts (non-secret app-wide defaults)
```

`environment.ts` throws at startup for `staging`/`production` builds with
missing/unsafe configuration (missing API URL, `localhost` API URL, or mock
mode enabled). `local`/`development`/`test` fall back safely so a fresh
clone still boots. No screen or feature reads `process.env` directly.
