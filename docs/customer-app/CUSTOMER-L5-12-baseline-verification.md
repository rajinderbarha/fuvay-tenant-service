# CUSTOMER-L5-12 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-11 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 584 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Canonical booking creation works: confirmed (L5-11, real `ServiceBooking`+`ServiceJob` transaction).
4. Exactly one booking created: confirmed via real DB-unique constraints (L5-11's idempotency-contract.md).
5. Draft conversion works: confirmed (`draft.status = "confirmed"`).
6. Booking reference is real: confirmed (`booking_number`, format `BK-YYYYMMDD-NNNNNN`).
7. Initial booking status is real: confirmed (`"pending_assignment"`).
8. Booking cache initializes correctly: confirmed (L5-11's `useBookingDetail`).
9. Draft cache clears: confirmed (L5-11's `useInvalidateDraftAfterBooking`).
10. Booking list endpoints identified: **two real, independent candidates found** — see Central Findings below.
11. Booking-detail endpoint identified: same — two real candidates.
12. Service-job relation identified: confirmed, `ServiceJob.booking_id` (unchanged since L5-11).
13. Lifecycle-event source identified: **a real, substantial finding** — `ServiceJobAssignmentEvent` (append-only, real), exposed via a real customer-facing tracking endpoint. See Central Findings.
14. Provider-acceptance source identified: **re-scoped this sprint** — the real backend models "acceptance" at the **technician/staff** level (`ServiceJobAssignment.assignment_status` — `assigned`/`accepted`/`rejected`), not a separate "provider/tenant accepts the booking" concept the spec's aspirational model implies. See status-projection.md.
15. Technician-assignment source identified: confirmed real and **actively written** — `home_service_assignment/service.py` genuinely assigns/reassigns/accepts/rejects (unlike several "column exists but dead" findings in earlier sprints).
16. Status-history source identified: confirmed real (`ServiceJobAssignmentEvent`).
17. Notification deep-link infrastructure exists: confirmed — `navigation/deep-links/` and `navigation/notification-intent.ts` already exist from CUSTOMER-L5-01; this sprint extends them with a real "booking" intent type rather than building new infrastructure.
18. No fake timeline in production paths: confirmed — no bookings-list/detail/timeline code exists anywhere in the mobile app before this sprint (L5-11 built only a post-confirmation detail fetch, not a list or timeline).
19. Existing tests pass: confirmed — 584/584 at sprint start.
20. Working tree: understood — unrelated parallel work in other engines/frontends, none touched.
21. No unrelated changes overwritten: confirmed.

## Existing Bookings-List/Detail Implementation Found

None real. `mobile/customer-app/src/screens/BookingsListScreen.tsx`/
`BookingDetailScreen.tsx` **already exist** but call a completely
different, legacy `/v1/bookings*` engine (flagged as a real risk by
CUSTOMER-L5-11's own known-gaps.md) — this sprint does not reuse, extend,
or route through them. `features/booking-confirmation/` (L5-11) has a
`useBookingDetail` hook calling `GET /v1/customer/my-activity/bookings/{id}`
— real, but superseded this sprint by a richer, purpose-built router (see
below); L5-11's own usage (fetching the just-created booking immediately
after confirmation) is left unchanged, since it works correctly for that
narrow purpose and this sprint does not need to touch L5-11's code.

## Central Findings — Two Real, Parallel Customer-Facing Booking Routers

This sprint's research uncovered **two independent, real, customer-facing
routers** that both read `ServiceBooking`/`ServiceJob`:

### (a) `final_records/customer_router.py` — `/v1/customer/my-activity/bookings*` (used by CUSTOMER-L5-11)

- `GET /bookings` (list, `status`/`limit`/`offset` params), `GET /bookings/{id}` (detail, raw `provider_snapshot` — **not** server-side stripped, a real gap L5-11 already documented and mitigated client-side via schema stripping).
- No timeline endpoint exists in this router at all.

### (b) `home_service_assignment/customer_router.py` — `/v1/customer/bookings*` (new this sprint's primary source)

- `GET ""` (list, `page`/`page_size` params, **already server-side customer-safe** — `_customer_safe_provider()` strips to exactly `provider_name`/`rating`/`public_badges`).
- `GET /{bookingId}` (detail — includes real `assignment_status` + a real, backend-authored customer-safe `assignment_message`, plus `job_status`/`scheduled_date`/`scheduled_time_window` when a job exists).
- `GET /{bookingId}/tracking` (**a real, genuine lifecycle timeline** — built from `ServiceJobAssignmentEvent` rows, mapped through a real, backend-authored customer-safe label dictionary; always includes a synthetic first "Booking confirmed" entry).
- `GET /{bookingId}/rating` / `POST /{bookingId}/rating` (real review read/submit, wrapping the real `ReviewService` — submission is out of this sprint's scope, but the **read** endpoint is used to determine review-boundary visibility honestly, since it tells this client whether a review already exists).

**This sprint uses router (b) as the primary, canonical source** for the
list, detail, and timeline — it is more complete (already includes
assignment/job status and a real timeline endpoint router (a) entirely
lacks) and already performs server-side provider-field stripping that
router (a) does not. Router (a) remains exactly as CUSTOMER-L5-11 left it
(untouched), since it correctly serves L5-11's own narrow purpose
(immediate post-confirmation fetch).

## A Third, Deeper Real System Exists — Deliberately Out of Scope

`app/engines/execution/` has its own, richer real event/note/media system
(`ServiceJobExecutionEvent`, `ServiceJobExecutionNote`,
`ServiceJobMediaUpload`), exposed via
`GET /v1/customer/service-jobs/{jobId}/tracking`. This is confirmed real
and customer-reachable, but is **deliberately not used this sprint** —
its event vocabulary (dispatched/on-the-way/arrived/in-progress) is
exactly the "live tracking" experience the spec explicitly assigns to
CUSTOMER-L5-13, and its notes/media are customer-facing execution detail
adjacent to the technician-tracking experience, not this sprint's
"lifecycle timeline" (assignment/acceptance/scheduling) scope. Documented
in `booking-job-contract.md`/`known-gaps.md` as a real, available, and
deliberately deferred capability — not an oversight.

## Cross-Check: Independent Research Pass — Confirmed, Plus Decisive Corrections

An independent background research pass reached identical conclusions on
the two real routers and the real `ServiceJobAssignmentEvent` timeline,
and additionally surfaced two decisive corrections:

1. **The real, reachable status vocabulary is smaller than
   `final_records/constants.py`'s own defined constants suggest.**
   `BOOKING_STATUS_IN_PROGRESS`/`BOOKING_STATUS_COMPLETED`/
   `BOOKING_STATUS_CANCELLED` and `JOB_STATUS_DISPATCHED`/
   `JOB_STATUS_IN_PROGRESS`/`JOB_STATUS_COMPLETED`/`JOB_STATUS_CANCELLED`
   are all **defined but never assigned by any real code path anywhere in
   the repository** (confirmed by an exhaustive, targeted grep excluding
   their own definition site). The only real, reachable values —
   confirmed by reading every real assignment site in
   `home_service_assignment/service.py` — are:
   `pending_assignment → assigned → accepted → scheduled`, with a
   real path back to `pending_assignment` on cancellation/rejection. This
   sprint's status registry (`status-projection.md`) documents the full
   aspirational set for forward-compatibility (so a booking is never
   shown as a raw, untranslated string if a future sprint wires up
   execution status transitions) but discloses honestly that
   `completed`/`in_progress`/`dispatched`/`cancelled` are currently
   unreachable — meaning this sprint's **review boundary** (§36,
   gated on `status === "completed"`) and **cancellation-boundary
   messaging** (gated on non-terminal status) can be built correctly but
   cannot be exercised by any real booking today. Documented prominently
   in known-gaps.md.
2. **No real push-notification delivery exists anywhere** —
   `app/engines/platform_notifications/channel_providers.py`'s push
   channel is a permanent stub (`PushNotificationProviderStub`, always
   returns `PROVIDER_NOT_CONFIGURED`). This sprint therefore builds no
   "enable notifications" registration UI (nothing would ever be
   delivered to it) — it only wires the existing, already-tested,
   already-real `resolveNotificationIntent()`/deep-link infrastructure to
   consume a hypothetical future booking-status payload, should a real
   push channel ever be configured. The `bookingDetail` route is already
   pre-configured `notificationEnabled: true` in the route registry from
   an earlier sprint, in anticipation of this.
3. **Two separate legacy tables** (`app/engines/booking/models.py`'s
   `Booking`/`BookingStatusHistory` and `app/engines/field_ops/models.py`'s
   `Job`/`JobStatusHistory`) are confirmed **decoys** — structurally
   similar-sounding but entirely unrelated to `ServiceBooking`/
   `ServiceJob`, and are exactly what the legacy
   `BookingsListScreen.tsx`/`BookingDetailScreen.tsx` (already flagged as
   a risk in L5-11's known-gaps.md) actually call. This sprint does not
   touch either.
4. A real `tracking` route is also already reserved
   (`notificationEnabled: true`, `productionEnabled: false`) — this
   sprint deliberately does **not** promote it: it most naturally maps to
   live GPS/map tracking (CUSTOMER-L5-13's explicit scope), which does
   not exist in the real backend today, whereas this sprint's real
   assignment-event timeline is embedded directly as a section within the
   booking-detail screen instead (see `list-architecture.md`).

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code.

## Deferred Issues

See `CUSTOMER-L5-12-known-gaps.md`.
