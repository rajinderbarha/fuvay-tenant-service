# CUSTOMER-L5-06 — Local Persistence Policy

## What Is Stored Locally

| Data | Storage | Scope | Cleared on |
|---|---|---|---|
| Active draft ID | `AsyncStorage` (`draft-local-store.ts`) | Per `customerId` | Logout, logout-all, draft cancellation |

That is the **entire** local persistence footprint this sprint adds. No
draft content, no diagnostic answers, no media binaries, no signed
URLs/preview URLs, and no tokens are ever written to local storage — only
an opaque ID pointer used solely to know *which* draft to ask the backend
about on the next app open.

## Why Plain (Non-Secure) Storage Is Correct Here

A draft ID is not a credential and does not, on its own, grant access to
anything — every draft endpoint independently enforces ownership
server-side (`_require_draft`, 403 `HOME_BOOKING_DRAFT_ACCESS_DENIED` on
mismatch). Even if this ID were somehow read off the device, it would only
let an attacker attempt a request that the backend would still reject for
any customer but its real owner. This matches the same reasoning already
established for `recent-search-storage.ts` (CUSTOMER-L5-04) — plain
`AsyncStorage`, customer-scoped keys, explicit clearing on logout.

## Not Implemented — and Why

- **No local queue of pending draft mutations or uploads.** No reliable
  background/offline queue infrastructure exists in this app (no
  task-queue library, no background-fetch registration) — building one
  would mean fabricating "offline support" that silently drops work on app
  kill, which is worse than being honest that a failed mutation must be
  retried by the customer while back online (CUSTOMER-L5-06 §45's "if no
  reliable queue infrastructure exists, keep selected files in safe
  pending state and require the customer to retry" — followed literally).
- **No local cache of draft *content*.** `useDraft`'s `staleTime: 0` means
  every screen mount re-fetches; the local pointer is never treated as
  content, only as an address to ask about.
- **No encrypted storage for the draft ID.** Per the reasoning above, the
  ID is not sensitive enough to warrant `expo-secure-store`'s overhead
  (which is reserved for tokens/device-binding IDs per this app's existing
  `storage-keys.ts` convention, unmodified this sprint).

## Migration

The storage key (`serviceos.pref.activeDraftId.v1:<customerId>`) is
versioned (`.v1`) following this app's existing convention
(`storage-keys.ts`) — a future shape change would bump to `.v2` and treat
the old key as absent rather than attempting an in-place migration,
consistent with every other preference key in this app.

## Corruption Handling

`getActiveDraftId`/`setActiveDraftId`/`clearActiveDraftId` all wrap
`AsyncStorage` calls in `try/catch` and fail closed to `null` / a silent
no-op on any error (matching `recent-search-storage.ts`'s established
pattern) — a corrupted or inaccessible value is treated as "no cached
draft," which safely falls through to creating a new one rather than
crashing.
