# CUSTOMER-L5-10 — Cache Policy

## No Dedicated Query Key for Bargain State

Both mutations used this sprint (`useCalculatePriceEstimate`, reused from
CUSTOMER-L5-09, and the new `useConfirmPriceChoice`) are `useMutation`s —
there is no GET-able "current bargain state" resource anywhere in this
backend (no session, no offer record — contract-matrix.md). All bargain
UI state lives in:

1. The two mutations' own in-memory `data`/`error`/`status`, composed by
   `useBargain` into the centralized `BargainState` via the pure
   `deriveBargainState` function.
2. A `useState`-held `selectedTier`, local to the hook/screen, cleared on
   unmount.

## No Draft-Cache Patch This Sprint

Unlike L5-08/L5-09's `useMatchProvider`/`useCalculatePriceEstimate`, this
sprint's `useConfirmPriceChoice` does **not** patch the shared
`draftQueryKeys.detail(...)` cache entry — `booking_summary` was never
part of the `bookingDraftSchema` any screen parses (unchanged since
CUSTOMER-L5-06), and no other screen currently reads it, so there is
nothing to keep in sync. This is a deliberate scope decision, not an
oversight — see `bargain-architecture.md`.

## Re-entering the Screen Re-runs the Estimate Fetch (Not the Confirmation)

`BargainScreen` triggers `useCalculatePriceEstimate` fresh on every mount
(mirroring L5-08/L5-09's identical auto-trigger-once pattern) — navigating
away and back re-fetches the current real Low/Mid/High. It does **not**
re-run `confirm-price-choice` automatically — that only happens on an
explicit tier tap, since (unlike the estimate) confirming a tier is a real
customer decision with a real, if minor, side effect (an audit event),
not a passive read.

## Logout / Account Switch

No new local persistence was added this sprint. The existing unconditional
`queryClient.clear()` (CUSTOMER-L5-02 pattern) discards any patched cache
entries from the reused `useCalculatePriceEstimate`; both this sprint's
mutations' own in-memory state and the `selectedTier` local state unmount
along with the screen on navigation away, with no additional clearing
logic required.

## Tenant/Locale Scoping

No new query keys were introduced this sprint (mutations only) — nothing
new to scope. The reused `useCalculatePriceEstimate` mutation's own draft
cache patch (when it succeeds) continues to use the existing
locale/tenant-scoped `draftQueryKeys.detail` key, unchanged from L5-09.
