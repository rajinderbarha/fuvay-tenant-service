# Customer App — Home Failure Matrix

| Failure | Detection layer | Affected section | Screen behavior | Retry behavior | Cache fallback | Customer message | Severity |
|---|---|---|---|---|---|---|---|
| `GET /v1/customer/categories` network/timeout error | `apiClient` (CUSTOMER-L5-00) normalizes to `ApiError` | Services section only | `ErrorState` with retry, rest of Home (header, offline banner) stays visible | Manual retry button re-runs the query | None (no disk cache — see cache policy doc) | "Couldn't load services" | P2 |
| Backend returns malformed category item(s) | `category-schema.ts` Zod validation | Services section (partial) | Valid items still render; invalid ones silently dropped | N/A (self-heals next fetch) | N/A | No visible error if ≥1 valid item remains | P3 |
| Backend returns zero categories | `discovery-composer.ts` (empty `items`) | Services section | `EmptyState` ("No services available") | N/A | N/A | "No services available. Please check back later." | P3 (expected operational state) |
| Duplicate category IDs in response | `discovery-composer.ts` dedup | Services section | Duplicate silently dropped, first occurrence kept | N/A | N/A | No visible message | P3 |
| Unauthenticated access to Home route | `route-guards.ts` (CUSTOMER-L5-01, unchanged) | Whole screen | Route denied before Home ever mounts — guest is routed to `baselineLanding`/`authentication` instead | N/A | N/A | N/A (screen never renders) | P0 (must never regress — covered by `route-guards.test.ts`) |
| Maintenance/mandatory-update active | `startup-route-resolver.ts` (CUSTOMER-L5-01, unchanged) | Whole app | Home is never reached — system gate screen shown instead | Per CUSTOMER-L5-01's own matrix | N/A | N/A | P1 |

Every row's Services-section-only failures leave the header/greeting/
avatar/offline-banner fully functional — only the one implemented section
degrades, never the whole screen, per the sprint's own partial-failure
requirement.
