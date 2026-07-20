# CUSTOMER-L5-07 — Cache Policy

| Data | staleTime | Query type | Isolation dimensions | Invalidation |
|---|---|---|---|---|
| Address list | `30_000` | `useQuery` | locale, tenant | Invalidated after create/update/delete/set-default |
| Serviceability result | N/A — not cached, a `useMutation` | `useMutation` | N/A | Always re-run fresh on entry to `ServiceabilityScreen` |
| Draft detail (address_id/serviceability_status changes) | `0` (unchanged from CUSTOMER-L5-06) | `useQuery` | draftId, locale, tenant | Written directly via `setQueryData` after address selection and serviceability check, matching L5-06's existing pattern |

## Why Address List Uses a Short Positive `staleTime`

Unlike the draft (mutated by the customer's own immediate actions,
`staleTime: 0`), the address list changes less frequently within a single
booking session — a 30-second window avoids a refetch on every
back-navigation between `AddressFormScreen` and `AddressListScreen` while
still staying fresh enough that a just-created address reliably appears
(the explicit `invalidateQueries` call after every mutation is the actual
mechanism that guarantees freshness, not the staleTime itself).

## Serviceability Address-Change Invalidation

Per CUSTOMER-L5-07 §33/§42, a serviceability result must never be reused
across a different address. This is enforced structurally, not by a cache
key: `useCheckServiceability` is a `useMutation`, not a cached `useQuery`
— there is no stale positive result sitting in a cache to accidentally
reuse. Navigating to `ServiceabilityScreen` with a different `addressId`
always triggers exactly one fresh `mutate()` call on mount.

## Isolation

- **Customer**: enforced server-side (address ownership, draft ownership)
  — the client's locale/tenant scoping is defensive only, matching every
  previous sprint.
- **Logout/account switch**: the existing unconditional `queryClient.clear()`
  (CUSTOMER-L5-02) wipes the address-list cache along with everything
  else — no new logout-time cleanup was needed for this sprint's data,
  since none of it is stored outside React Query's own cache or the
  already-covered local draft-ID pointer.

## No Long-Lived Positive-Serviceability Cache

Directly satisfies CUSTOMER-L5-07 §33's "do not cache a positive
serviceability result indefinitely" — there is no cache for it at all to
go stale.
