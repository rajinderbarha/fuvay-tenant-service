# CUSTOMER-L5-08 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-08-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **This client cannot distinguish the two real 422 match-failure reasons**
   (`HOME_BOOKING_NO_PROVIDER_AVAILABLE` vs. `PRICE_OPTIONS_UNAVAILABLE`),
   and cannot show the real, more specific backend detail message for
   either — a pre-existing, cross-cutting limitation of `api-client.ts`'s
   error normalization (it never reads the failure response body), not
   introduced or fixed this sprint. See contract-matrix.md's Error
   Contract and security-review.md's Error Body Discard section.
3. **`"Verified"` badge is not actually a verification signal** — the
   backend hardcodes it unconditionally into every match's `public_badges`
   list regardless of `Tenant.verification_status`. This client renders it
   as an honest passthrough of real (if misleadingly-named) backend data;
   fixing the semantics is a backend change out of this sprint's scope.
   See provider-model.md.
4. **No component/render tests** for `ProviderPreviewScreen` — same,
   now-consistent-across-eight-sprints deprioritization pattern.
5. **The break/holiday/booking-window eligibility checks are real but
   currently unreachable** from this client's call pattern, because
   `match-and-price` never passes a `requested_at` value (no real UI
   concept of an exact requested date/time exists in this flow yet — only
   the free-text `preferred_time_window` from CUSTOMER-L5-07, which is
   never forwarded into the matching call). See availability-contract.md.

## P2

6. **`providerPreview`'s pre-reserved route-param shape
   (`{ providerId: ProviderId }`) was wrong** and has been corrected this
   sprint to `{ draftId: BookingDraftId }`, matching what the real backend
   contract actually needs (there is no provider-preview-by-ID lookup —
   only draft-scoped matching). Documented here since a future reader
   might otherwise wonder why the originally-reserved shape changed.
7. **No repeated-tap debounce** on the "Try again" action — each tap
   re-runs the real, non-idempotent-but-safe-to-repeat backend call. Low
   severity since the backend itself treats repeated calls as safe
   re-derivation (contract-matrix.md's Idempotency section), and no data
   corruption or duplicate side effect results from it — only redundant
   event-log rows on the backend.
8. **No analytics events actually wired to a vendor** — same
   now-eight-sprints-running gap: no analytics SDK is integrated in this
   app at all; `logger.*` calls are structured logs only.
9. **`customer_visible_reason` has no localization key on the backend
   side** — real English text is rendered verbatim to Hindi/Punjabi
   customers, since the backend never returns a translatable key or
   per-locale variant. Same category of gap as CUSTOMER-L5-07's
   `preferred_time_window` free text.

## P3

10. **No provider-matching-api.ts unit test** — consistent with the
    established, repo-wide pattern that thin `*-api.ts` wrappers around
    `apiClient` are not independently tested (verified against
    `draft-api.ts`/`address-api.ts`, neither of which has one either).
11. **No test exercises genuine multi-candidate scoring** (would require a
    live backend with two or more real, competing eligible tenants) — see
    runtime-evidence.md.
