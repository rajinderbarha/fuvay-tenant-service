# CUSTOMER-L5-08 — Cache Policy

## No Dedicated Query Key for Match Results

`useMatchProvider` is a `useMutation`, not a `useQuery` — there is no
`providerMatchQueryKeys` module, because there is nothing GET-able to key
(see matching-architecture.md). The match result lives only in:

1. The mutation's own in-memory `data`/`error`/`status` (React Query's
   mutation state — cleared on unmount, not persisted across navigation
   away and back, matching `useCheckServiceability`'s identical behavior).
2. A patch onto the existing `draftQueryKeys.detail(draftId, locale,
   tenantId)` cache entry (`status`, `selected_tenant_id`,
   `provider_match_status`) — reusing CUSTOMER-L5-06's already-established,
   locale/tenant-scoped key.

## Re-entering the Screen Re-runs the Match

Since `ProviderPreviewScreen` triggers the mutation fresh on every mount
(no cached "already matched" short-circuit), navigating back to
`AddressSelection` and forward again re-invokes `match-and-price`. This is
intentional and matches the real backend's own re-derivation semantics
(contract-matrix.md's Idempotency section) — showing a stale, possibly
now-ineligible provider from a prior mount would be the actual bug.

## Logout / Account Switch

No new local persistence was added this sprint (unlike CUSTOMER-L5-06's
draft-ID pointer) — the existing unconditional `queryClient.clear()`
(CUSTOMER-L5-02 pattern) already discards any in-flight/cached mutation
state and the patched draft-detail cache entry on logout or account
switch, with no additional clearing logic required.

## Tenant/Locale Scoping

The draft-detail cache patch reuses the exact key
(`draftQueryKeys.detail`) CUSTOMER-L5-06 already scopes by
`locale`/`tenantId ?? "no-tenant"` — no new scoping logic was introduced or
needed this sprint.
