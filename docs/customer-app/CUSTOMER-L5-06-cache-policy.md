# CUSTOMER-L5-06 — Cache Policy

| Data | staleTime | Query type | Isolation dimensions | Invalidation |
|---|---|---|---|---|
| Draft detail | `0` (always considered stale) | `useQuery` | draftId, locale, tenant | Every mount refetches; mutations (`useCreateDraft`/`useUpdateDraft`/`useLinkDraftPhoto`) write the fresh result directly via `setQueryData` |
| Draft media list | `30_000` | `useQuery` | draftId, locale, tenant | Invalidated after upload+link, delete, or replace |
| Active draft ID (local pointer) | N/A — not a React Query cache at all | `AsyncStorage` | customerId | Explicit clear on logout/logout-all/cancel |

## Why Draft Detail Uses `staleTime: 0`

Unlike CUSTOMER-L5-04's category/service caches (5-minute staleTime, safe
because they're public, slow-changing catalog data), a booking draft is
mutated by the customer's own in-progress actions and must never show
stale status/photo state after a mutation elsewhere in the flow. Always
refetching on mount is the simplest correct policy given this sprint's
request volume is low (a handful of screens, not a scrolling list).

## Isolation

- **Customer**: enforced server-side on every endpoint (ownership check),
  not merely by the client's query key — the query key's locale/tenant
  scoping is defensive, matching every previous sprint's pattern, not the
  actual isolation boundary.
- **Cross-draft**: `mediaQueryKeys.draftMedia` is keyed by `draftId`, so
  one draft's media list can never be served from another draft's cache
  entry.
- **Logout/account switch**: `queryClient.clear()` (CUSTOMER-L5-02,
  unmodified) wipes both the draft-detail and draft-media caches
  unconditionally on every logout, in addition to the local draft-ID
  pointer being cleared explicitly.

## No Long-Lived Positive-Serviceability Cache

Not applicable this sprint — no serviceability concept exists in this
sprint's scope (CUSTOMER-L5-07 owns it). Documented here only to state that
this sprint introduces no such cache to worry about yet.
