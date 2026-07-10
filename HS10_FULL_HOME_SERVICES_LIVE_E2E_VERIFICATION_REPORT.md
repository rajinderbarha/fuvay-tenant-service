# HS10 — Full Home Services Live E2E Verification Report

## Baseline scenario used
Tenant "Demo AC Services" (`34b427a7-b2be-496c-b826-6d51bb181248`),
Ludhiana 141001, AC Repair / Split AC / LG, admin range ₹600–950,
provider range ₹700–850, 10% platform fee → Low ₹770 / Mid ₹850 / High
₹935 (matches the ticket's baseline exactly, live-confirmed). Completed
Job Deduction: 21 usage credits (real, configured on the Split-AC+LG
pricing rule this session, matching the ticket's own example number).

## One continuous, unbroken live chain (booking `BK-20260709-000004` / `JOB-20260709-000004`)

1. **Customer booking creation** — `POST .../booking-drafts` →
   `PUT .../booking-drafts/{id}` (type/brand/issue/zip) →
   `POST .../serviceability-check` → `serviceable: true`.
2. **Provider-first matching** — `POST .../match-and-price` → selected
   provider "Demo AC Services" returned **before** any price is shown;
   `selected_provider_price_options: {low_price: 770.0, mid_price:
   850.0, high_price: 935.0}` — exact baseline match.
3. **Price selection** — `POST .../confirm-price-choice`
   `{"price_tier": "mid"}`.
4. **Booking confirmation** — `POST .../confirm` → `200`,
   `booking_number: BK-20260709-000004`, `job_number:
   JOB-20260709-000004`, `selected_price_option: mid`,
   `selected_price_amount: 850.0`, `payment_mode:
   customer_pays_provider_directly`.
5. **Job assignment** — `POST /v1/provider/service-jobs/{id}/assign`
   → real technician "Demo Staff" assigned.
6. **Technician lifecycle** — `accept → on-the-way → reached-site →
   start-inspection → complete-inspection → start-service`, each a real
   `200` with the correct new status.
7. **Invalid transition hard test** — `POST .../on-the-way` again
   (already at `service_started`) → **clean `422
   EXECUTION_INVALID_STATUS_TRANSITION`**, `request_id` present.
8. **Completion** — `POST .../complete`
   `{"work_summary": "...", "collected_amount": 850, "technician_note":
   "..."}` → `200`, `status: completed`, full `completion_data`
   persisted, `payment_mode` unchanged.
9. **Usage credit deduction** — same response includes
   `usage_credit_deduction: {credit_delta: -21.0, balance_before:
   3979.0, balance_after: 3958.0, deduction_source: <real Split-AC+LG
   pricing rule id>}` — atomic with completion, no separate call needed.
10. **Idempotency hard test** — retried `/complete` on the now-completed
    job → `422 JOB_NOT_COMPLETABLE` (job-status-layer guard) — ledger
    re-queried afterward: still exactly the entries from steps above,
    no duplicate.
11. **Customer tracking** — `GET /v1/customer/bookings/{id}` →
    `status: completed`, `job_status: completed`, `selected_price_amount:
    850.0`, `payment_mode: customer_pays_provider_directly` — all
    correctly reflecting the live job state, no internal data present.
12. **Customer review** — `POST .../rating` `{"rating": 5, "comment":
    "Fast and professional."}` → `200`, real `Review` row created.
13. **Final ledger check** — `GET /v1/provider/usage-credits/ledger` →
    **exactly 2 entries** across this session's two completed jobs
    (`6628eb52...` and `34fc415e...`), each `-21.0`, correct sequential
    `balance_before`/`balance_after` chaining (`4000→3979→3958`) — no
    double-counting, no missing entries.

## Additional scenarios verified earlier this session (not re-run in this chain, still valid)
- Rejected-parts-cannot-be-installed gate (HS8B).
- Unresolved-parts-blocks-completion gate (HS8B/HS9).
- Low-credit tenant excluded from matching, then restored (HS9B) —
  `INSUFFICIENT_USAGE_CREDITS` reason code confirmed at the matching layer.
- Duplicate customer review rejected with `409 REVIEW_ALREADY_SUBMITTED` (HS9B).
- Rating on an incomplete booking rejected with `422 BOOKING_NOT_COMPLETED` (HS9B).
- Window-AC-vs-Split-AC deduction specificity — two different real
  pricing rules resolve independently (HS9).

## Not live-verified this pass
- Admin catalog/pricing creation flow (assumed pre-existing from
  HS2/HS3, not re-exercised).
- Full audit-trail enumeration across all 12 ticket-listed event types
  (only booking/assignment/status/completion/deduction events were
  directly observed via their own API responses this session — no
  single "audit log" endpoint was queried to confirm all 12 types
  produce a row there specifically; see `HS10_AUDIT_OBSERVABILITY_REPORT.md`).
- Frontend click-through (browser session) for any of the pages built
  this session — verified via TypeScript compile + source inspection only.

## Verdict
**Backend E2E: genuinely complete, live-verified, unbroken, real
database, real API calls, zero mock data** — booking through completion
through deduction through review, in one continuous session.
