# CUSTOMER-L5-04 — Discovery Architecture

## Category Model

Flat, single-level (`ServiceCategory`, no `parent_category_id`). The client
never invents a hierarchy — `CategoryDetailScreen` shows exactly the
category's own metadata plus its offering list, nothing nested.

## Service (Offering) Model

`MasterOffering`, category-scoped (`category_id` FK, one level, no
children). Offering IDs are opaque strings from the backend (`ServiceId`
brand) — the app never derives or reconstructs one.

## Category → Service List → Service Detail Flow

```
HomeScreen (category press)
  → CategoryDetailScreen(categoryId)
      useCategoryDetail(categoryId)      — category metadata
      useCategoryOfferings(categoryId)   — paginated offering list (useInfiniteQuery)
        → ServiceListItem press
          → ServiceDetailScreen(serviceId, categoryId)
              useServiceDetail(categoryId, serviceId)
              → evaluateBookingBoundary() → "Book service" action
                → BookingAssistant(serviceId, categoryId) [dev-only placeholder; CUSTOMER-L5-05 builds the real flow]
```

`categoryId` travels with `serviceId` through every hop because the real
offering-detail endpoint is category-scoped server-side
(`/categories/{category_slug}/offerings/{offering_slug}`) — there is no
"look up an offering by ID alone" endpoint. This is why `RootStackParamList`
requires both on `ServiceDetails` and `BookingAssistant`, not just
`serviceId`.

## Booking Boundary

`features/service-detail/domain/booking-boundary.ts` is a pure,
side-effect-free evaluator mirroring the real gates already encoded on the
`bookingAssistant` route (`route-registry.ts`): `access: "authenticated"`
and `productionEnabled: false` (CUSTOMER-L5-05 does not exist yet). It never
duplicates route-guard logic ad hoc inside the screen — the screen calls the
evaluator and renders one of three states (`AVAILABLE`, `AUTH_REQUIRED`,
`NOT_YET_AVAILABLE`) rather than deciding for itself.

## Query Keys and Cache Scoping

Every query key includes locale + tenant (the only two isolation dimensions
this backend contract actually carries — there is no marketplace or region
concept in any of these endpoints, so no key segment was added for either;
see CUSTOMER-L5-03's identical, already-established reasoning for Home).

```
category.detail(categoryId, locale, tenantId)
category.offerings(categoryId, locale, tenantId)   — useInfiniteQuery, pages keyed internally by page number
service.detail(categoryId, serviceId, locale, tenantId)
search.results(normalizedQuery, categoryId, locale, tenantId)
```

## Navigation and Deep Links

`categoryDetail` and `serviceDetails` are promoted from CUSTOMER-L5-01-era
placeholders (`productionEnabled: false`) to real, always-on routes
(`access: "authenticated"`, `productionEnabled: true`). `serviceDetails`'s
previous `access: "module-enabled"` + `featureKey: "service-discovery"` gate
was a genuine pre-existing bug — no remote-config module named
`"service-discovery"` is defined anywhere, and `evaluateModule` fails closed
on an unknown key, so the route was permanently unreachable even before this
sprint touched it. Corrected to `"authenticated"`, matching `home`'s own
precedent for core, always-on functionality.

Deep-link paths (`deep-link-validator.ts`):
```
categories/:categoryId                     → categoryDetail
categories/:categoryId/services/:serviceId → serviceDetails
search                                      → search
```
