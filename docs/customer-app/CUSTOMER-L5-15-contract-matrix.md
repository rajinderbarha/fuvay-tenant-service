# CUSTOMER-L5-15 — Contract Matrix

Per §5's required format: `MATCHED | MISMATCHED | MISSING_CLIENT |
MISSING_BACKEND | UNREACHABLE | UNVERIFIED | NOT_APPLICABLE`.

| Concept | Real backend endpoint found | Status | Notes |
|---|---|---|---|
| Get cancellation eligibility (for the real booking) | None | **MISSING_BACKEND** | No endpoint anywhere computes eligibility for `ServiceBooking`/`ServiceJob` |
| Get cancellation policy (real booking) | None reachable | **UNREACHABLE** | `GET /v1/bookings/tenants/{tenant_id}/cancellation-policy` exists but belongs to the disconnected `booking` engine (see baseline-verification.md) — its `tenant_id` scope has no relationship to a real `ServiceBooking`'s tenant either, since that engine never receives real bookings |
| Get cancellation reasons | None | **MISSING_BACKEND** | No reason-code catalog exists anywhere in the repo for cancellation |
| Customer cancel booking (real booking) | `POST /v1/bookings/{booking_id}/cancel` | **UNREACHABLE** | Real endpoint, real customer permission (`P.BOOKING_CANCEL`), but resolves against the `bookings` table, never populated by the real booking pipeline — confirmed 404 for any real `ServiceBooking.id` |
| Customer cancel booking (provider-side equivalent) | `POST /v1/provider/service-jobs/{job_id}/cancel` | **NOT_APPLICABLE** | Real and reachable, but provider-role only — not a customer capability |
| Cancellation-pending / approval-required state | None | **MISSING_BACKEND** | `booking` engine's cancel is atomic/immediate only (no approval step); no equivalent exists for the real pipeline |
| Cancellation fee | `booking` engine's policy string only (English sentence, no amount field) | **MISSING_BACKEND** (for real booking) | No `fee_amount`/`currency` field anywhere |
| Service-credit boundary | None | **MISSING_BACKEND** | No service-credit-on-cancellation model found (the `customer_credits` engine exists for other purposes — not wired to cancellation) |
| Refund boundary | None | **MISSING_BACKEND** | No refund-on-cancellation model found |
| Reschedule eligibility (real booking) | None | **MISSING_BACKEND** | — |
| Reschedule policy (real booking) | None | **MISSING_BACKEND** | — |
| Replacement SLA/window retrieval | None | **MISSING_BACKEND** | No capacity/availability-driven replacement-window endpoint exists tied to a real `ServiceJob` |
| Reschedule request (real booking) | `POST /v1/bookings/{booking_id}/reschedule/request` | **UNREACHABLE** | Same disconnected-table problem as cancel |
| Provider reacceptance after reschedule | `POST /v1/bookings/reschedule/{id}/accept` (tenant-only) | **NOT_APPLICABLE** | Tenant-facing, not customer; also unreachable for real bookings regardless |
| Technician reassignment on reschedule | None | **MISSING_BACKEND** | — |
| Serviceability revalidation on reschedule | CUSTOMER-L5-07's own real serviceability endpoints exist independently, but no code path wires them into a reschedule flow | **MISSING_BACKEND** | Serviceability itself is real (L5-07); the *reschedule-triggered revalidation* orchestration is not |
| Pricing/bargain revalidation on reschedule | CUSTOMER-L5-09/10's own real pricing/bargain endpoints exist independently, same gap | **MISSING_BACKEND** | — |
| Parts-request conflict on cancel/reschedule | None | **MISSING_BACKEND** | `execution` engine's `PartsRequest`/`complete_job`'s resolution gate (CUSTOMER-L5-14) only concerns job *completion*, never cancellation/reschedule |
| Idempotency-Key support on cancel/reschedule | Not supported by any real endpoint (`booking/router.py`'s cancel/reschedule bodies take no idempotency header) | **MISSING_BACKEND** | — |
| Booking/job optimistic-concurrency version field | None on `ServiceBooking`/`ServiceJob`; none on `booking` engine's own `Booking` either | **MISSING_BACKEND** | Grepped `version` across both models — zero matches in either |
| Notification events for cancel/reschedule | `booking/service.py` calls `self._publish("booking.cancelled", ...)` / `"booking.reschedule_requested"` / `"booking.rescheduled"` (lines 768, 951, 977) | **NOT_APPLICABLE** | These publish against the disconnected engine's own events; irrelevant to the real pipeline's notifications |
| Timeline event for cancel/reschedule (real booking) | None | **MISSING_BACKEND** | `final_records`'s own booking/job models have no cancellation timeline hook |

## What this client implements as a result

Given the above, this sprint's honest, shippable scope is:

1. **Verification and hardening of the existing informational treatment**
   (`BookingDetailScreen`'s "Cancel or reschedule" row, in place since
   CUSTOMER-L5-12) — confirmed correct, not a regression, not a
   placeholder that should have become a real button.
2. **Regression tests** proving no fake/interactive cancel or reschedule
   action is ever rendered for any booking status, closing the loop on
   this sprint's own "no fake cancellation, no fake reschedule" mandate.
3. **Exhaustive documentation** of the disconnected `booking` engine so a
   future sprint does not waste effort wiring the client to it before the
   backend gap (mirroring real bookings into that engine's table, or
   rebuilding its logic against `ServiceBooking`/`ServiceJob` directly) is
   closed.

No new API client, query, mutation, or screen is introduced this sprint
— there is no real endpoint to wrap. This mirrors CUSTOMER-L5-10's
"entire bargain-session model is feature-flagged off" and CUSTOMER-L5-13's
"no technician profile exists" outcomes: the correct sprint deliverable
when the real backend has nothing to build against is rigorous proof of
that fact, not a convincing-looking fake.
