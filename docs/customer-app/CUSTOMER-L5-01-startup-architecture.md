# CUSTOMER-L5-01 — Startup Architecture

## 1. Startup State Model

One module-level orchestrator (`src/app/startup/startup-service.ts`) owns the
entire startup lifecycle. It is driven by a pure reducer
(`startup-machine.ts`) that computes the next `StartupSnapshot` from the
current one plus an action — no I/O, no timers, fully unit-testable without
mounting React. `startup-context.tsx` is the only React-facing wrapper: it
starts exactly one run on mount, subscribes to snapshot changes, and
re-evaluates on app resume.

```
StartupProvider (React)
  -> runStartup() [startup-service.ts]
       -> dispatch(startupReducer) [startup-machine.ts]  (pure)
       -> side effects: remote-config-service, connectivity, deep-link resolver
  -> useStartup() -> RootNavigator picks a screen from the snapshot
```

## 2. Phase Sequence

`idle → initializing → validating-environment → loading-local-preferences →
loading-secure-session-placeholder → resolving-locale → resolving-theme →
checking-connectivity → loading-cached-config → fetching-remote-config →
evaluating-version-policy → evaluating-maintenance-policy →
resolving-marketplace-context → resolving-auth-placeholder →
resolving-onboarding-placeholder → resolving-deep-link →
resolving-initial-route → ready | degraded | failed`

`resolving-locale` and `resolving-theme` are recorded as phases for
observability/diagnostics, but the actual hydration work for those two is
owned by CUSTOMER-L5-00's `ThemeProvider`/`AppBootstrap` (already tested in
that sprint) — the startup service does not duplicate that logic, it only
brackets the phase for the phase-history timeline.

## 3. Phase Dependencies

Each phase is sequential except:

- `fetching-remote-config` only runs when connectivity is not `offline`; if
  it fails, the flow falls through to whatever was already loaded by
  `loading-cached-config` (or compiled defaults) rather than failing the
  whole run.
- `resolving-deep-link` depends on `resolving-auth-placeholder` and
  `resolving-onboarding-placeholder` having already run, since guard
  evaluation needs both.

## 4. Timeout Rules

See `startup-timeouts.ts` — one deliberate value per operation, not a single
blanket timeout:

| Operation | Timeout |
|---|---|
| Environment validation | 500ms |
| Preference hydration | 2000ms |
| Secure-session placeholder read | 2000ms |
| Remote-config fetch | 8000ms |
| Total blocking startup | 12000ms (documented budget; not separately enforced as a second timer — see known-gaps) |
| Deep-link resolution | 500ms |
| Store-open action | 5000ms |

A timed-out phase produces a `StartupError` with category `timeout` and
`retryAllowed: true`.

## 5. Cancellation Rules

Every async phase checks `sequenceId !== activeSequenceId` before applying
its result. `RESET` (fired by `runStartup`/`retryStartup`) increments
`activeSequenceId`, so a stale in-flight phase from a superseded run
silently no-ops instead of corrupting the newer run's snapshot — this is the
mechanism satisfying "cancel obsolete requests" and "stale config replacing
newer config" protection.

## 6. Retry Rules

`retryStartup()` clears the `running` flag and calls `runStartup()` again,
which bumps `activeSequenceId` (superseding anything in flight). Per
CUSTOMER-L5-01 §41: retryable failures are network/timeout/temporary-server
categories; `invalid_schema`, `unsupported_schema_version`, and
`integrity_failure` are never retried automatically by
`remote-config-service.ts` — the customer must trigger it explicitly via a
system screen's retry button.

## 7. Cache-First Behavior

`loadCachedConfig()` is always attempted before any network call
(`loading-cached-config` phase precedes `fetching-remote-config`). Cache
usability (`remote-config-cache.ts#evaluateCacheUsability`) rejects
environment-mismatched, marketplace-mismatched, or too-old entries.

## 8. Remote Refresh Behavior

`refreshRemoteConfig()` de-duplicates concurrent calls via a single
in-flight promise (`inFlightRefresh`), sends `If-None-Match` when a cached
ETag exists, and treats HTTP 304 as `remote-not-modified` (reuses the cached
payload, updates only `fetchedAt`).

## 9. Initial Route Priority

Implemented in `startup-route-resolver.ts#resolveInitialRoute`, in this
order (matches CUSTOMER-L5-01 §7):

1. Invalid environment → `unsupportedBuild`
2. Unsupported build → `unsupportedBuild`
3. Startup failure / no config → `startupError` or `offlineStartup`
4. Mandatory maintenance → `maintenance`
5. Mandatory update / blocked build → `mandatoryUpdate`
6. Marketplace/app disabled → `appUnavailable`
7. Offline with no cache → `offlineStartup`
8. Auth unknown → `startup` (stay put; should not normally be reached since
   auth placeholder always resolves synchronously to `guest` this sprint)
9. Guest + deep link requiring auth → `authentication`
10. Onboarding required → `baselineLanding` (no onboarding screens exist
    yet — see known-gaps)
11. Pending validated deep link → deep link's route
12. Pending validated notification → notification's route
13. Default landing (`navigation.initialRouteOverride` or
    `navigation.fallbackRouteId`) → usually `baselineLanding`

A deep link can never reach step 11 if any of steps 1–7 apply — this is
enforced by ordering alone (deep link is only inspected after all mandatory
checks return a non-blocking result), and is covered by
`startup-route-resolver.test.ts`.

## 10. App Resume Behavior

`StartupProvider` listens to `AppState` and re-runs startup on `active` if
at least `RESUME_REEVALUATION_MIN_INTERVAL_MS` (60s) has passed since the
last check, and only when the app was already `ready`/`degraded` (never
re-triggers while a first run is still in progress). This re-evaluates
maintenance and version policy (via a full `retryStartup`) without a
separate "resume-only" code path — reusing the same deterministic resolver
keeps the two flows from drifting apart.

## 11. Error Handling

`StartupError` (category + generated `errorReferenceId`) is the only error
type surfaced to `StartupErrorScreen`; no raw stack trace or backend message
ever reaches customer-facing text. `remote-config`'s own `RemoteConfigError`
categories are caught internally by the startup service and folded into the
"config unreachable, fall back to cache/defaults" path rather than failing
the whole startup — only a genuinely unrecoverable condition (no config
source of any kind) produces a terminal `StartupError`.

## 12. Analytics

Not wired to a concrete vendor this sprint (none was authorized in L5-00
either) — `logger.info`/`logger.warn` calls at the safe event names listed
in `CUSTOMER-L5-01`'s spec (`startup.completed`, `startup.failed`,
`remote_config.fetch_succeeded`, `remote_config.fetch_failed`,
`remote_config.not_modified`, `deep_link.opened`, `deep_link.rejected`,
`deep_link.deferred`) stand in as the analytics-adapter-ready log points;
wiring `logger.track()` to these same call sites is a one-line change once a
vendor is chosen (see `known-gaps.md`).

## 13. Logging

All startup logging goes through `src/observability/logger.ts` (L5-00),
which redacts sensitive keys before anything reaches `console.*`. No raw
config dump, no raw deep-link query string, and no notification payload is
ever logged — only route ids, categories, and counts.

## 14. Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│ App.tsx                                                         │
│  AppProviders (L5-00: Theme, QueryClient, ErrorBoundary, Toast)  │
│   └─ StartupProvider ─┬─ runs startup-service.ts once            │
│      AuthProvider     │                                          │
│       └─ RootNavigator│ (single NavigationContainer)             │
│            ├─ Startup / StartupError / OfflineStartup            │
│            ├─ Maintenance / MandatoryUpdate                      │
│            ├─ UnsupportedBuild / AppUnavailable                  │
│            └─ MainNavigator                                      │
│                 ├─ BaselineLanding (temporary, honest)            │
│                 ├─ LegacyApp (CUSTOMER-L5-00-and-earlier stack)  │
│                 └─ dev-only: DesignSystemShowcase, StartupInspector │
└────────────────────────────────────────────────────────────────┘
```
