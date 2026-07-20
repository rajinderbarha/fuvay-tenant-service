# Customer App — Navigation Architecture

## 1. Navigator Hierarchy

```
RootNavigator (single NavigationContainer, owns linkingConfig + navigationRef)
 ├─ system screens (Startup, StartupError, OfflineStartup, Maintenance,
 │   MandatoryUpdate, UnsupportedBuild, AppUnavailable) — exactly one shown
 │   at a time, chosen by the startup snapshot
 └─ MainNavigator
      ├─ BaselineLanding (temporary, honest baseline screen)
      ├─ LegacyApp → AppNavigator (CUSTOMER-L5-00-and-earlier authenticated
      │    stack: 19 real screens, real AuthContext-based login) — nested,
      │    no longer owns its own NavigationContainer
      └─ dev-only: DesignSystemShowcase, StartupInspector
```

`AppNavigator.tsx` (pre-existing) was changed in exactly one way this
sprint: its own `<NavigationContainer>` wrapper was removed so it can nest
inside `RootNavigator`'s single container — React Navigation permits only
one container per app. No screen, route name, or business logic inside it
changed.

## 2. Route Registry

`src/navigation/route-registry.ts` is the single compiled source of truth.
Every route has a stable `id` (the key used everywhere else — remote config,
deep links, notification intents), a `name` (the React Navigation route
string), a `navigator` owner, an `access` policy, `deepLinkEnabled`,
`notificationEnabled`, `productionEnabled`, an `analyticsName`, and a
`fallbackRouteId`. Remote config and deep links can only ever reference a
route by `id` — `getRouteDefinition()`/`isKnownRouteId()` reject anything
not in this compiled map, so neither the backend nor a URL can invent a
navigable destination.

## 3. Typed Route Params

`src/navigation/route-types.ts` (`RootStackParamList`) plus branded ID types
in `route-params.ts` (`ServiceId`, `BookingId`, etc.) — a `ServiceId` and a
`BookingId` cannot be passed to each other's route without a TypeScript
error, even though both are strings underneath. Branding is compile-time
only; runtime values arriving from a deep link or notification are still
validated by `deep-link-validator.ts`/`notification-intent.ts` before they
become a `ServiceId`.

## 4. Route Access Policies

`src/navigation/route-guards.ts#evaluateRouteAccess` is the single
evaluator — screens must never implement their own guard logic. Checks run
in this fixed order: startup readiness → maintenance → mandatory version
update → marketplace availability → dev-only-in-non-dev → production
availability → auth requirement → onboarding requirement → module/feature
eligibility → deep-link/notification eligibility. A route can be denied for
exactly one reason (`RouteGuardDecision`), always the first check that
fails.

## 5. Navigation Service

`src/navigation/navigation-service.ts` is the only sanctioned entry point
for navigating from non-component code (a 401 handler, a notification
tap-handler). It:

- rejects any route not in the compiled registry (`isKnownRouteId`),
- queues exactly one pending intent if the container isn't ready yet and
  flushes it once via `flushQueuedIntent()` (called from
  `NavigationContainer`'s `onReady`),
- ignores a second identical `navigate()` call within 400ms (duplicate-tap
  / duplicate-notification protection),
- never exports the raw `navigationRef` — only action functions
  (`navigate`, `replace`, `resetTo`, `goBackIfSafe`,
  `getCurrentRouteName`).

Screens should still prefer `useNavigation()` for normal in-screen
navigation; this service exists for contexts with no React tree.

## 6. Pending Destination

`src/navigation/deep-links/pending-deep-link-store.ts` holds at most one
pending destination, memory-only (never persisted — the OS redelivers the
initial URL on relaunch, so persistence would only add replay risk).
Consume-once (`consumePendingDestination`) prevents the same link from
firing navigation twice; a 5-minute TTL prevents a very old deferred
destination from firing long after the customer opened the link.

## 7. Back-Button Rules

`MandatoryUpdateScreen` swallows the Android hardware back button entirely
(`BackHandler.addEventListener` returns `true`, never removed while
mounted) — there is intentionally no way to back out of a mandatory system
gate. `ConfirmationModal`/`BottomSheet` (L5-00) handle back-button dismissal
for their own scope only.

## 8. Modal Rules

No new modal navigator was introduced this sprint (`ROUTE_REGISTRY` reserves
a `"modal"` `NavigatorId` for `legalTerms`/`legalPrivacy`/
`designSystemShowcase`, but none of those are mounted as true React
Navigation modals yet — they're plain stack screens). Wiring an actual modal
presentation style is deferred to whichever sprint first needs a real modal
flow.

## 9. Production and Development Routes

`RouteDefinition.productionEnabled` gates whether a route can be entered in
a production build (`route-guards.ts` denies with `deny-production`).
`access: "development-only"` additionally requires `isDevBuild` regardless
of `productionEnabled`. `MainNavigator.tsx` wraps its two dev-only
`Stack.Screen` registrations in `__DEV__` at the component level too —
belt-and-suspenders, since Metro strips `__DEV__`-gated code from release
bundles entirely.

## 10. Future Extension Rules

- Add a new route: add it to `route-names.ts`, `route-types.ts`
  (param shape), and `route-registry.ts` (access policy) — all three in the
  same change, or `isKnownRouteId` will reject it everywhere.
- Add a new navigator: give it a new `NavigatorId` in `route-registry.ts`
  and mount it under `MainNavigator` (or a new top-level area under
  `RootNavigator` if it's a system-level concern, not a business one).
- Do not add a second `NavigationContainer` anywhere in the tree.
