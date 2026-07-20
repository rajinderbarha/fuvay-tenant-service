# CUSTOMER-L5-08 — Matching Architecture

## Client Architecture

`features/provider-matching/` follows the exact directory pattern
established in every prior sprint:

```
domain/   provider-match-schema.ts       zod schema, fail-closed parse
          badge-label-mapping.ts         literal-string → i18n key map, fail-safe
api/      provider-matching-api.ts       one function, calls the real endpoint
queries/  provider-matching-queries.ts   useMatchProvider mutation
screens/  ProviderPreviewScreen.tsx      auto-triggers the match on mount
```

## Why This Is a Mutation, Not a Query

The real backend has no GET-able "current match" resource — matching is
always a `POST` that re-derives and overwrites draft state (see
contract-matrix.md's Idempotency section). `useMatchProvider` is therefore
a `useMutation`, matching the exact pattern `useCheckServiceability`
established in CUSTOMER-L5-07 for the same reason (a `POST`-only,
re-runnable check with no independent cacheable GET).

## Screen Flow (mirrors ServiceabilityScreen's established pattern)

1. `ServiceabilityScreen`'s real "Continue" action (after a serviceable
   result) now navigates to `ProviderPreview` instead of directly to the
   dev-only `Pricing` placeholder — provider matching is the real next
   stage the backend actually supports between serviceability and pricing.
2. `ProviderPreviewScreen` auto-triggers `useMatchProvider.mutate(draftId)`
   on mount (identical `useEffect`-once pattern to
   `ServiceabilityScreen`'s auto-check) — there is no "tap to start
   matching" button, since the backend has no session/queue to enter first;
   the single call *is* the match.
3. On success, renders `selected_provider`'s five real fields (see
   provider-model.md) and a "Continue" action to the dev-only `Pricing`
   placeholder (CUSTOMER-L5-09 boundary, same pattern as every previous
   sprint's next-stage placeholder).
4. On failure (any 422, or any other error — see contract-matrix.md's
   Error Contract for why the two real 422 reasons cannot be
   distinguished at this client's current error-handling layer), renders
   one generic "couldn't find a match" state with "Try again" (re-runs the
   same mutation) and "Change address" (navigates back to
   `AddressSelection`) — mirroring `ServiceabilityScreen`'s own
   not-serviceable state's action pair exactly.

## No Candidate List, No Ranking UI (by design, not by omission)

The spec's aspirational model anticipated a richer matching experience
(candidate comparison, ranking explanation, availability calendar). None of
that exists in the real backend (see contract-matrix.md's "Fields that do
NOT exist" section) — building UI for it would mean fabricating data. This
sprint's screen is intentionally a single-provider preview card, nothing
more, because that is the entirety of what the real contract provides.

## Draft Cache Update

`useMatchProvider`'s `onSuccess` mirrors `useCheckServiceability`'s
established pattern: it patches the existing `draftQueryKeys.detail(...)`
cache entry in place (`status`, `selected_tenant_id`,
`provider_match_status`) rather than invalidating and refetching — avoiding
an extra round trip for fields this client already has from the mutation's
own response.
