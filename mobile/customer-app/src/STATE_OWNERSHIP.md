# State Ownership — Phase D

Three tiers, matching the storage/query primitives already established in
Phase A-C (`src/api/queryClient.ts`, `src/storage/secureStorage.ts`,
`src/storage/localStorage.ts`).

## Server state → `@tanstack/react-query`, keyed via `src/api/queryKeys.ts`

Everything the backend is authoritative for: customer profile, catalog/
verticals, serviceability, addresses (once fetched), booking drafts (once
server-created), pricing/estimate results, bookings, service jobs, quotes,
reviews, conversations, notifications. A screen must never keep a second
copy of this data in local component state beyond the query cache's own
lifetime — no global Zustand/Redux mirror "just in case."

## Local application state → React state / `src/storage/localStorage.ts`

Non-sensitive only: theme preference (already implemented, Phase A-C),
temporary UI toggles, unsaved form progress, the pre-sync booking draft
(`src/storage/draft/bookingDraftPersistence.ts`), pending media selection
before upload, onboarding flags. Never a token, never a full server
response cached indefinitely "for offline."

## Secure state → `src/storage/secureStorage.ts`

Access token, refresh token, session metadata, trusted-device state only.
Nothing else may be written here — enforced by the two modules exposing
disjoint APIs with no shared key namespace (see
`src/storage/__tests__/storageSeparation.test.ts` from Phase A-C, extended
this phase by `bookingDraftPersistence.test.ts`'s ownership-isolation
tests).

## Rule of thumb

If the backend can tell you the current truth, it owns the copy — you hold
a cache with a TTL, not a store. If it's presentation-only or literally
cannot exist server-side yet (an in-progress draft before its first save),
it's local. If leaking it would compromise the account, it's secure.
