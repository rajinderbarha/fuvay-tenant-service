# CUSTOMER-L5-06 — Draft Architecture

## Ownership

```
backend booking-draft engine (home_service_booking)
  → canonical persisted draft state (id, status, all fields)

mobile local store (draft-local-store.ts)
  → a single draft ID pointer only, for restoration — never a competing
    source of truth for the draft's content

booking assistant (CUSTOMER-L5-05)
  → collects answers in-memory, hands off a small, safe subset to the draft
    on completion (assistant-answer-mapping.ts)

media engine (Phase 0A)
  → stores uploaded files; the draft only stores the resulting URL strings
```

There is exactly one persistence system for canonical draft state — the
backend. The local store never holds draft content, only the ID needed to
re-fetch it.

## Creation

`useBookingDraft` (`hooks/use-booking-draft.ts`) implements CUSTOMER-L5-06
§13's restoration sequence: resolve a locally-cached draft ID for this
customer → if present, fetch and let the backend's own ownership/status
checks validate it → if absent, or the fetch fails, create a new draft via
`POST /v1/customer/home-services/booking-drafts`. The draft ID is never
generated client-side.

**The most consequential real constraint**: `category_slug`/`offering_slug`
in the create request must resolve against `admin_catalog`'s `MasterService`
table — a different, unrelated table from the `MasterOffering` catalog that
CUSTOMER-L5-04's real `ServiceDetailScreen` is built on (see
contract-matrix.md). This client passes the real, already-fetched
`category.slug`/`service.slug` faithfully; if the backend responds with
`HOME_BOOKING_OFFERING_INVALID` (422), `BookingDraftScreen` shows an honest
"this service isn't available for booking yet" error rather than crashing
or fabricating a draft.

## Assistant Synchronization

`domain/assistant-answer-mapping.ts#mapAssistantAnswersToDraftUpdate` maps
CUSTOMER-L5-05's collected answers onto exactly the fields the real `PUT`
endpoint accepts: `brand` → `brand_id`, `service_type` → `offering_type_id`
(carrying forward CUSTOMER-L5-05's own documented naming assumption), and
`issue_description`/`customer_note` → a joined `issue_summary` string.
`issue_type_id` and `service_option_ids_json` are deliberately never sent —
both are real columns on the draft model but neither is in the `PUT`
endpoint's accepted-field allowlist (verified by reading
`service.py#update_draft_fields`), so sending them would silently do
nothing. `BookingDraftScreen` performs this sync exactly once per resolved
draft (`syncedAnswersRef`), only for fields the draft doesn't already have a
value for, avoiding a needless overwrite of server state.

## Autosave

There is no field-by-field autosave in this sprint — the only mutation this
sprint performs against the draft is the one-time assistant-answer sync on
arrival, plus the append-only photo-link calls from the media step. There is
no free-text draft field this sprint exposes for the customer to type into
directly (the address/notes stage is CUSTOMER-L5-07's scope), so there is no
debounced-autosave surface to build yet — documented honestly rather than
building a UI-less autosave mechanism with nothing to save.

## Versioning and Conflict Handling

**Not applicable.** No `version`/`revision`/`ETag` column exists anywhere on
`HomeServiceBookingDraft` — confirmed absent from the model, not merely
unparsed by this client. There is therefore no conflict to detect beyond
"the server rejected my mutation" (e.g. `HOME_BOOKING_DRAFT_TERMINAL_STATUS`
if the draft moved to a terminal state elsewhere) — handled as a normal
mutation error, refetching the authoritative draft on failure via React
Query's cache invalidation.

## Restoration

On every mount, `useBookingDraft` re-fetches the draft from the backend
(`useDraft`, `staleTime: 0`) — the local ID is a pointer only, never treated
as trustworthy content. `draftLoaded()` (`domain/draft-session.ts`) fails
closed to `EXPIRED`/`CANCELLED` states if the authoritative draft is already
terminal, so a stale local pointer can never present a closed draft as
active.

## Expiry

`expires_at` (24 hours from creation, real backend constant
`DRAFT_EXPIRY_HOURS`) is checked client-side (`isPastExpiry()`) defensively,
since the backend only flips `status` to `"expired"` via an async scheduler
job that may not have run yet — the client treats "past `expires_at`" as
expired in the UI immediately, without waiting for that job, while any
mutation attempt still trusts the server's actual response as ground truth.

## Cancellation

`useCancelDraft` calls the real `POST /{id}/cancel` endpoint before clearing
the local pointer — cancellation is always a real backend operation, never a
local-only discard.

## Local Cache

See `CUSTOMER-L5-06-local-persistence-policy.md`.

## Isolation

The local draft-ID pointer is keyed by `customerId`
(`draft-local-store.ts`) and explicitly cleared on both `logout` and
`logoutAll` (`use-logout.ts`/`use-logout-all.ts`) — an account switch on a
shared device can never resume a different customer's draft. Server-side,
every draft endpoint enforces ownership (`_require_draft`,
`HOME_BOOKING_DRAFT_ACCESS_DENIED` on mismatch) — verified by reading
`service.py`, not assumed.
