# CUSTOMER-L5-11 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-10 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 564 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Real booking draft exists: confirmed.
4. Draft belongs to authenticated customer: confirmed — enforced server-side on every draft endpoint (`_require_draft`), unchanged pattern since L5-06.
5. Draft restoration: confirmed working.
6. Draft versioning: **confirmed absent**, unchanged finding since L5-06 — no `version`/`revision` counter anywhere on the draft.
7. Diagnostic stage complete: confirmed tracked via `_compute_missing_fields` (real, re-checked server-side by `mark_ready_for_confirmation` — see Central Findings).
8. Required media backend-confirmed: confirmed tracked the same way (part of `_compute_missing_fields`'s required-field check).
9. Address valid/customer-owned: confirmed (L5-07).
10. Serviceability current: **re-verified server-side, not just client-cached** — `mark_ready_for_confirmation` re-checks `draft.serviceability_status == SVCABILITY_SERVICEABLE` live, a real, important finding for this sprint's preflight design.
11. Zone/city tier current: still not applicable to the real Low/Mid/High flow (unchanged L5-09 finding).
12. Selected SLA valid/unexpired: still not applicable — unchanged L5-07/09/10 finding (no real SLA engine, no expiry).
13. Provider match valid/unexpired: **re-verified live, not just cached** — `mark_ready_for_confirmation` queries `provider_visibility_statuses.is_bookable` fresh at confirm-time, raising `SELECTED_PROVIDER_NOT_BOOKABLE` if the provider became non-bookable since matching. This is real, meaningful, server-side revalidation this sprint's client can trust rather than needing to reimplement.
14. Selected provider/Tenant remains eligible: same as above.
15. Pricing estimate current: confirmed present (`draft.price_snapshot.price_options`), re-checked for existence by `mark_ready_for_confirmation`.
16. Bargain result/fixed-price decision current: confirmed — `mark_ready_for_confirmation` requires `booking_summary.selected_price_tier` to be one of `"low"|"mid"|"high"`.
17. Negotiated price valid: same as above — the negotiated price (`booking_summary.customer_offer`) is carried forward verbatim into the created `ServiceBooking.price_snapshot` (see conversion-contract.md).
18. Booking-review endpoint identified: `POST /{draftId}/summary` (`build_booking_summary`, already partially documented by L5-10 for this sprint's benefit) — real, re-confirmed.
19. Booking-preflight endpoint identified: **`mark_ready_for_confirmation`** (called internally by `POST /{draftId}/confirm`, not a separately-callable endpoint) — real, thorough, and previously dead code until an "HS7 fix" wired it in (per its own docstring).
20. Canonical booking-create endpoint identified: **`POST /{draftId}/confirm`** (`confirm_draft` in `customer_router.py`) — real, calls `mark_ready_for_confirmation` then `HomeServiceFinalCreationService.finalize()`.
21. Idempotency support identified: real — `CustomerBookingConfirmation` table with a `UNIQUE(draft_type, draft_id)` constraint is the actual functional dedup guard (not the client-supplied `Idempotency-Key` header value itself, which is stored for audit/traceability only). See idempotency-contract.md.
22. Duplicate-booking protection identified: same mechanism — confirmed doubly-enforced (`ServiceBooking.draft_id` also has its own `UNIQUE` index).
23. Draft conversion behavior identified: real — `draft.status = "confirmed"` is set only after `ServiceBooking`+`ServiceJob` rows are successfully created, inside the same request (see conversion-contract.md for transaction-boundary caveats).
24. Direct-payment policy identified: confirmed unchanged — `payment_mode = "customer_pays_provider_directly"`, carried forward from L5-09/L5-10 into the final booking record.
25. Existing confirmation behavior identified: none in the mobile app before this sprint.
26. No fake booking confirmation in production paths: confirmed — no booking-review/confirm code exists anywhere in the mobile app yet.
27. Existing tests pass: confirmed — 564/564 at sprint start.
28. Working tree: understood — unrelated parallel work in other engines/frontends, none touched.
29. No unrelated changes overwritten: confirmed.

## Existing Booking-Review/Confirmation Implementation Found

None in the mobile app. `features/bargain/screens/BookingReviewBoundaryPlaceholderScreen.tsx` (L5-10) is a dev-only placeholder proving the route boundary reaches a typed route; no real review or confirmation logic exists anywhere yet.

## Central Findings — Real Backend Capability Is Substantial (Unlike L5-10's Bargain Sprint)

Unlike CUSTOMER-L5-10's finding (bargaining is a minimal tier-pick with no
session/counteroffer engine), this sprint's research found a genuinely
rich, production-grade real backend:

1. **`POST /{draftId}/confirm`** (`customer_router.py:283-326`) is real,
   documented in its own summary as *"Confirm booking — creates
   ServiceBooking + ServiceJob... Idempotent: retrying returns the
   existing booking number."* It (a) calls `mark_ready_for_confirmation`
   (the real preflight, skipped if the draft is already `"confirmed"` so
   idempotent retries fall through to the dedup path instead), then
   (b) calls `HomeServiceFinalCreationService.finalize()`.
2. **`mark_ready_for_confirmation`** (`service.py:801-871`) is a real,
   thorough preflight: required-field completeness, live serviceability
   re-check, live provider-bookability re-check (queries
   `provider_visibility_statuses` fresh), and a valid tier-choice check —
   all server-side, all re-validated at confirm-time, not merely inherited
   from earlier stages.
3. **`HomeServiceFinalCreationService.finalize()`** (`final_records/creation_service.py:67-210`)
   is a real, complete, well-engineered transaction: idempotency check via
   `CustomerBookingConfirmation` (unique on `(draft_type, draft_id)`) →
   load+validate draft → generate sequential `booking_number`/`job_number`
   (format `BK-YYYYMMDD-NNNNNN`/`JOB-YYYYMMDD-NNNNNN`) → create
   `ServiceBooking` (also uniquely indexed on `draft_id`) → create
   `ServiceJob` → mark `draft.status = "confirmed"` + emit a draft event →
   insert the `CustomerBookingConfirmation` lock row → write an audit log
   row → return a real result dict.
4. **A real canonical booking-retrieval endpoint exists**:
   `GET /v1/customer/my-activity/bookings/{booking_id}`
   (`final_records/customer_router.py:97-122`) — customer-ownership
   enforced, includes the linked `ServiceJob` if one exists. This is the
   endpoint this sprint's confirmation screen fetches from, rather than
   trusting the mutation response alone (per §45's requirement).
5. **Real, disclosed backend robustness gap**: `finalize()`'s own guard
   exceptions (`ValueError(ERR_DRAFT_NOT_FOUND/NOT_READY/ACCESS_DENIED)`)
   are **not** caught by any specific handler — they fall through to
   `app/exceptions.py`'s catch-all `Exception` handler, which returns a
   generic `INTERNAL_ERROR` (not the specific `FINAL_DRAFT_NOT_READY`
   code, and likely not a clean 4xx status). In practice this rarely
   fires in the real successful path, because `mark_ready_for_confirmation`
   (called first, and raising clean `ServiceOSException`s with real 422s)
   already screens out most of the same conditions — but it is a real,
   disclosed gap for the narrow race-condition window between the two
   calls. See known-gaps.md.
6. **`GET /bookings/{booking_id}` returns 200 with an `{"error": ...}` body**
   for not-found/access-denied cases, rather than a 404/403 HTTP status —
   a real, disclosed API design quirk this client must handle by checking
   the response body shape, not the HTTP status, for this specific
   endpoint.
7. **`ServiceBooking.provider_snapshot` is the raw, unstripped
   `draft.selected_provider_snapshot`** — confirmed to include
   `internal_score`/`matching_score_snapshot` (per L5-08's original
   finding about this exact draft field). This is a **new, important,
   disclosed finding**: unlike `booking_summary.selected_provider`
   (server-side stripped by `build_booking_summary`), the booking's own
   `provider_snapshot` field is NOT stripped server-side. This client must
   strip these two internal-only keys itself before rendering — the same
   discipline `build_booking_summary` already applies, just not yet
   applied to this specific field. Documented prominently in
   security-review.md.

## Cross-Check: Independent Research Pass — Confirmed, Plus New Corrections

An independent background research pass reached identical conclusions on
every point above, and additionally surfaced:

1. **A second, parallel confirm endpoint exists**:
   `POST /v1/customer/confirm/home-service-booking/{draftId}`
   (`final_records/confirm_router.py:49-88`) — calls the exact same
   `HomeServiceFinalCreationService.finalize()` directly, but expects the
   draft to already be `ready_for_confirmation` (it does not run
   `mark_ready_for_confirmation` itself first). This sprint uses the
   already-integrated `home_service_booking` router's own
   `POST /{draftId}/confirm` instead, since it performs the real preflight
   internally in one call — calling the `final_records` variant directly
   would require this client to call `mark_ready_for_confirmation`
   separately first, which has no dedicated customer-facing endpoint of
   its own (it's only reachable as a side effect of the
   `home_service_booking` confirm route).
2. **A second, app-wide idempotency layer exists**:
   `app/core/idempotency.py`'s `IdempotencyMiddleware` reads a
   **differently-named** header (`X-Idempotency-Key`, not
   `Idempotency-Key`) on any `POST`/`PUT`/`PATCH`/`DELETE`, caching full
   HTTP responses in Redis for 24h and replaying them
   (`X-Idempotency-Replayed: true`) on a repeated key. This is layered on
   top of (not a replacement for) the DB-level `CustomerBookingConfirmation`
   unique-constraint lock, which remains the authoritative guard. This
   sprint sends both headers (`Idempotency-Key` for the endpoint's own
   audit-trail storage, `X-Idempotency-Key` for the middleware's
   response-replay protection) with the same stable value, to get the
   full benefit of both real layers.
3. **The event mechanism is simpler than the spec's aspirational
   "outbox" model** — `finalize()` reuses the same
   `HomeServiceBookingDraftEvent` table draft-lifecycle events already
   use (`event_type="draft_confirmed"`), not a separate outbox/event-bus
   table. No `EVENT_BOOKING_CREATED` constant or generic outbox exists
   anywhere in the repo.
4. **No notification side effect exists on booking creation at all** —
   `creation_service.py`'s own module docstring states plainly: *"Does
   NOT push notifications or assign technicians (Sprint 20+)."* Confirmed
   by grep: zero notification/SMS/push/email calls anywhere in this
   transaction. This sprint therefore builds no notification-registration
   UI (§38 says "may register" — there is nothing real to register
   against yet); see known-gaps.md.
5. **Critical disambiguation**: `mobile/customer-app/src/screens/BookingsListScreen.tsx`/
   `BookingDetailScreen.tsx` **already exist**, but call a completely
   different, legacy `/v1/bookings*` engine (`app/engines/booking/`,
   nested under `LegacyApp`/`AppNavigator.tsx`) — fully disconnected from
   `home_service_booking`/`final_records`. This sprint's new
   `BookingSuccess` screen must call the real
   `/v1/customer/my-activity/bookings/{id}` endpoint, never the legacy
   `bookingsApi` client, and must not be confused with or route through
   those pre-existing legacy screens.

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code. `BookingReviewBoundaryPlaceholderScreen.tsx`
(L5-10) is replaced this sprint by the real `BookingReviewScreen` — an
expected, planned boundary promotion.

## Deferred Issues

See `CUSTOMER-L5-11-known-gaps.md`.
