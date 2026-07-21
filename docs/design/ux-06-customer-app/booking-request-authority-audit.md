# Booking Request Authority Audit — UX-06 Round 5 (Workstream 6)

Real source inspection (`app/engines/home_service_booking/{customer_router,service}.py`,
`app/engines/final_records/creation_service.py`):

| Requirement | Verified | Evidence |
|---|---|---|
| Customer identity server-derived | Yes | Every draft/confirm route takes `customer_id = uuid.UUID(user.user_id)` from `get_current_user`'s JWT — never a body field |
| Address belongs to customer | Partial | `ac_repair` has `requires_address:false` (confirmed real), so this path wasn't exercised; drafts that DO require an address use `address_id` (a UUID field on the draft), not raw text — ownership check not traced this round (no offering requiring it was available to test) |
| Tenant/provider selection follows canonical logic | Yes | `match_provider_and_price()`'s own docstring: "the backend runs the full eligibility gate ... and selects exactly ONE provider — the customer never sees or picks from a list" |
| Offering ID canonical | Yes | Draft creation resolves `offering_slug` server-side against `MasterService`; confirm accepts no raw offering ID at all |
| Serviceability authoritative | Yes | Computed server-side (`draft.serviceability_status`), confirm reads this field, never a client-echoed value |
| Price authoritative | Yes | `resolve_price_estimate()`'s own comment: "Backend is source of truth. Frontend price is NEVER trusted." Confirmed live: `price_snapshot.source: "backend_catalog"` |
| Bargain result authoritative when present | Yes (by design, unverified live this round) | `confirm_price_choice()` only accepts a tier NAME (`low`/`mid`/`high`), never a raw amount — the real amount is resolved server-side from the stored `price_options`. Could not exercise live this round since `match-and-price` itself is blocked (no `BargainRule`) |
| Client cannot set tenant ID | Yes | No `tenant_id` field anywhere in any draft/confirm request body |
| Client cannot set final amount | Yes | `confirm_draft` (`/{draft_id}/confirm`) takes **no body at all** — literally nothing for the client to override |
| Duplicate submission prevented | Yes | Real `Idempotency-Key` header + `ConfirmationLockService.check_and_raise_if_duplicate()`, confirmed present in source (Round 3/4) |
| Retry follows real idempotency behavior | Yes (by code reading) | Same idempotency key on retry returns the existing booking (`idempotent: true` in the response), not a new one — proven via a unit test (`bookingContract.test.ts`'s "duplicate submission" case) at the request-construction layer; not yet exercised against a real duplicate live call (booking submission itself is blocked) |
| Correct pipeline used | Yes | `home_service_booking` → `final_records.HomeServiceFinalCreationService` → creates `ServiceBooking` + `ServiceJob`, confirmed via the route's own response fields (`booking_id`+`job_id`, both present, both distinct) |
| Booking and job IDs remain distinct | Yes | Confirmed in the real response schema — `booking_id`/`booking_number` and `job_id`/`job_number` are always separate fields, never merged |

## Preserved pipeline separation

`bookingsApi`/`fieldOpsJobsApi` (Booking→field_ops.Job, read-only, `/v1/customer/bookings*`
and `/v1/customer/jobs*`) remain completely separate exports from
`homeServiceDraftApi`/`bookingConfirmApi` (ServiceBooking→ServiceJob,
`/v1/customer/home-services/booking-drafts/*`) in `src/lib/api.ts` — never
adapted into one another, consistent with the canonical domain rule.
