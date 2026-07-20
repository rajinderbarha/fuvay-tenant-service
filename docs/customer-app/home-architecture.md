# Customer App — Home Architecture

## Screen Architecture

```
HomeScreen (features/home/screens/HomeScreen.tsx)
 ├─ Header: greeting (domain/greeting.ts) + avatar → Profile
 ├─ OfflineBanner (CUSTOMER-L5-00)
 └─ Section "Services"
      ├─ loading  → Skeleton × 2
      ├─ error    → ErrorState (retry)
      ├─ empty    → EmptyState
      └─ data     → CategoryGrid → CategoryCard × N
```

## Data Flow

```
homeApi.listCategories()          [features/home/api/home-api.ts]
  → GET /v1/customer/categories   (real backend, verified)
  → CategoryListResponse (raw, untrusted)
  → parseCategoryList()           [domain/category-schema.ts, Zod]
      → valid items + droppedCount (invalid items logged, never crash the screen)
  → composeCategorySections()     [domain/discovery-composer.ts]
      → dedupe by id → stable sort (display_order, name) → cap at 12
  → useHomeCategories()           [queries/home-queries.ts, TanStack Query]
  → HomeScreen renders ComposedCategories
```

## Query Flow

One query key: `["home", "categories", locale]` (`homeQueryKeys.categories`).
`staleTime: 5 * 60_000` — categories don't need to refetch on every screen
focus. Pull-to-refresh (`ScreenContainer`'s `onRefresh`) calls
`categories.refetch()` directly rather than invalidating the whole
`QueryClient`.

## Navigation Flow

`startup-route-resolver.ts`'s default-landing branch (CUSTOMER-L5-01,
amended this sprint) picks `"home"` once `auth === "authenticated"` and no
pending deep link/notification applies. `RootNavigator.tsx` reacts to that
`routeId` and mounts `MainNavigator` with `initialRouteName="Home"`
(otherwise `"BaselineLanding"`). A category press does not navigate
anywhere yet — no category-detail screen exists (CUSTOMER-L5-04) — it
surfaces a toast acknowledging the tap instead of either a dead card or a
fake screen.

## State Boundaries

Server state (categories) → TanStack Query, per CUSTOMER-L5-00's
`state-management-guidelines.md`. No new global client state was
introduced — the greeting reads the already-existing `useAuthSession()`
session, and the query result lives entirely in React Query's cache.

## Marketplace Isolation

Not applicable this sprint — the categories endpoint has no
marketplace/tenant parameter in its real contract (see backend-contract-
audit). The query key does not need a marketplace dimension because there
is only one marketplace context recognized by this backend today; adding
one is a documented extension point once the backend gains multi-
marketplace catalogue scoping.

## Feature Evaluation

Home itself is gated by `route-guards.ts` (`access: "authenticated"`,
`productionEnabled: true`) — not by the remote-config module evaluator,
since Home is not a `remote-config` "module" (no such module type is
defined for it). Individual categories are not gated by the module
evaluator either, since the backend already filters to
`is_active && is_customer_visible` server-side — client-side "eligibility"
here is limited to schema validation (drop malformed items), not a
business-rule evaluation.

## Loading / Errors / Cache / Refresh

See `home-content-composition.md` and `home-cache-and-refresh-policy.md`.

## Analytics / Performance

Not implemented this sprint — see `known-gaps.md`. `CategoryGrid` uses a
plain bounded `flex-wrap` layout (capped at 12 items, see §14 of the
sprint spec's own allowance) rather than a virtualized list, since the
category count is small and bounded by `discovery-composer.ts`'s cap.

## Dependency Diagram

```
features/home/screens/HomeScreen.tsx
  → features/home/queries/home-queries.ts
      → features/home/api/home-api.ts        → api/api-client.ts (CUSTOMER-L5-00)
      → features/home/domain/category-schema.ts (Zod)
      → features/home/domain/discovery-composer.ts (pure)
  → features/home/components/{CategoryGrid,CategoryCard}.tsx
      → components/primitives/* (CUSTOMER-L5-00)
  → features/auth/hooks/use-auth-session.ts (CUSTOMER-L5-02)
  → features/home/domain/greeting.ts (pure)
```
