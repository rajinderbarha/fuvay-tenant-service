# CUSTOMER-L5-09 — Cache Policy

## No Dedicated Query Key for Price Estimates

`useCalculatePriceEstimate` is a `useMutation`, not a `useQuery` — same
reasoning as L5-08's `useMatchProvider`: there is no GET-able "current
estimate" resource on this backend (contract-matrix.md). The estimate
result lives only in:

1. The mutation's own in-memory `data`/`error`/`status`, composed by
   `usePricingEstimate` into the centralized `PricingState`.
2. A `useRef`-held "previous options" value, used only for client-side
   revision-banner detection (pricing-architecture.md) — never persisted,
   never shared across screens, cleared automatically on unmount since it
   lives in component/hook-local React state.
3. A patch onto the existing `draftQueryKeys.detail(draftId, locale,
   tenantId)` cache entry — reusing CUSTOMER-L5-06's already-established,
   locale/tenant-scoped key, same fields L5-08 already patches.

## Re-entering the Screen Re-runs the Calculation

Since `PricingEstimateScreen` triggers the mutation fresh on every mount
(no cached "already calculated" short-circuit — mirroring L5-07/L5-08's
identical pattern), navigating back to `ProviderPreview` and forward again
re-invokes `match-and-price`. This is intentional: it matches the real
backend's own re-derivation semantics and ensures a stale price from a
prior mount (e.g., after the customer changed their address in between)
is never shown as current.

## Logout / Account Switch

No new local persistence was added this sprint. The existing unconditional
`queryClient.clear()` (CUSTOMER-L5-02 pattern) discards the patched
draft-detail cache entry; the mutation's own in-memory state and the
`useRef`-held previous-options value are unmounted along with the screen
on navigation away, with no additional clearing logic required.

## Invalidation on Upstream Context Change

Per contract-matrix.md's Revalidation Triggers finding, the real backend
performs **no automatic invalidation** of `price_snapshot` when address,
SLA, or provider context changes elsewhere in the draft. This sprint does
not fabricate a client-side invalidation mechanism to compensate — since
`PricingEstimateScreen` always recalculates fresh on every mount (above),
any upstream change that routes the customer back through
`AddressSelection`/`ServiceabilityCheck`/`ProviderPreview` and back to
this screen naturally produces a fresh, correct estimate the next time
this screen mounts. The one gap this does **not** cover: if a future
sprint allows editing address/SLA *without* leaving this screen (not
possible today — no such control exists here), a stale estimate could
persist until the explicit "Refresh estimate" action is used. Documented
in known-gaps.md.

## Tenant/Locale Scoping

The draft-detail cache patch reuses the exact key
(`draftQueryKeys.detail`) already scoped by `locale`/`tenantId ?? "no-tenant"`
since CUSTOMER-L5-06 — no new scoping logic was introduced or needed this
sprint.
