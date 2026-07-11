# FINAL-L5-02B — Customer Booking Backend Alignment Report

## Evidence-driven conclusion: no backend changes were required this sprint

Per Part 12's own instruction ("Update only what the evidence requires"), this sprint's investigation found the backend already correctly aligned with the Model D decision (established in FINAL-L5-01D, re-verified this sprint with independent fresh evidence):

| Possible work item | Needed? | Evidence |
|---|---|---|
| 1. Correct customer booking list query | No | Already queries `ServiceBooking` exclusively; live-verified 5/5 correct |
| 2. Correct customer booking detail query | No | Already queries `ServiceBooking`+`ServiceJob`; live-verified |
| 3. Correct tracking query | No | Already joins `ServiceBooking`+`ServiceJob`; live-verified |
| 4. Correct cancellation ownership | **Partially — documented gap, not fixed** | No dedicated `POST /v1/customer/bookings/{id}/cancel` endpoint exists post-confirmation (only pre-confirmation draft cancel). The customer-app's own typed client already documents this honestly: `cancelCustomerBooking()` in `customer-home-services.ts:171` is a stub that returns `Promise<never>` with a comment explaining no such endpoint was found wired. This is a real, pre-existing product gap (not something this mission's scope — Tenant Jobs migration + booking source alignment — asks to build), left as-is and documented rather than silently patched with a fabricated endpoint (rule 8). |
| 5. Correct review relationship | No | Already correct — `POST/GET .../bookings/{id}/rating` against `ServiceBooking` |
| 6. Add/repair projection logic | No | No projection exists or is needed (Model D has no projection step) |
| 7. Repair missing transaction linkage | No | `service_jobs.booking_id → service_bookings.id` already correctly set for all 5 seeded rows, in the same transaction, by design |
| 8. Add compatibility adapter for legacy rows | No | `bookings` (0 rows) has no historical data requiring compatibility handling |

## Requirements re-verified
1. No duplicate booking creation — confirmed via `ConfirmationLockService` (idempotency lock) + live retry-determinism test + existing passing unit tests.
2. No orphan `service_job` — `booking_id` is a NOT NULL FK, created in the same transaction as the booking; cannot exist without a parent booking.
3. No wrong-customer access — live RBAC probe this sprint confirms Customer Two cannot see or fetch Customer One's booking (safe embedded not-found, zero data exposure).
4. No wrong-tenant access — N/A to this specific report (tenant isolation is the Tenant Jobs side); customer bookings are scoped by `customer_id`, not `tenant_id`, from the customer's perspective.
5. No data copied manually just to satisfy tests — confirmed; this report changed zero backend code.
6. Existing historical rows remain readable — all 5 seeded `service_bookings` rows remain fully readable via list/detail/tracking, verified live.
7. New flow is deterministic and idempotent — confirmed via the idempotency lock mechanism (unchanged, already correct).

## Result
No `NOT_READY_FINAL_L5_02B_CUSTOMER_BOOKING_API_FAILED` — the API layer was already correctly aligned; this sprint's contribution was verification with fresh, independent evidence plus honest documentation of the one real, pre-existing, out-of-scope gap (post-confirmation cancellation).
