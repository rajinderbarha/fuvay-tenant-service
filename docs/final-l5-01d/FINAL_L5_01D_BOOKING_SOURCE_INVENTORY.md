# FINAL-L5-01D — Customer Booking Source Inventory

Real code inspection, not assumption.

| Aspect | `bookings` (booking engine) | `service_bookings` (final_records engine) |
|---|---|---|
| Model file | `app/engines/booking/models.py` | `app/engines/final_records/models.py:14` |
| Purpose | Generic cross-vertical booking-request table — consumed by `ai_chat`, `ai_conversation`, `admin_customers_router`, `booking/admin_router.py`, `compliance`, `dashboard_command_center` | Home-Services-specific execution projection, created via `FinalCreationService` from a confirmed `HomeServiceBookingDraft` |
| Primary key | `id` (UUID) | `id` (UUID) |
| Tenant/customer scope | `tenant_id`, `customer_id` columns present | `tenant_id`, `customer_id` columns present |
| Write path | `booking/service.py` (multiple engines write here) | `final_records/creation_service.py::confirm_home_service_draft()` — the **real, live confirmation flow** |
| `service_jobs` relationship | **None found** — no code creates a `service_jobs` row with `booking_id` pointing at a `bookings` row | **Confirmed direct**: `creation_service.py:150` — `ServiceJob(booking_id=booking.id, ...)` where `booking` is a `ServiceBooking` |
| Customer booking-list consumer | Not used by `/v1/customer/bookings` | **`app/engines/home_service_assignment/customer_router.py:52-57`** — `select(ServiceBooking).where(ServiceBooking.customer_id == customer_id)` |
| Customer tracking consumer | Not checked (out of scope — no evidence found) | `final_records/confirm_router.py`, `execution/home_service_service.py` |
| Reviews eligibility | Not referenced | `customer_reviews/eligibility_service.py` — imports `ServiceBooking` |
| Complaints eligibility | Not referenced | `complaints/eligibility_service.py` — imports `ServiceBooking` |
| Admin booking/job views | `booking/admin_router.py` (its own domain) | `final_records/admin_router.py` |
| Tenant booking/job views | Not applicable | `final_records/provider_router.py` (`/v1/provider/my-records/jobs`, `/bookings`) |
| Migrations/tests | Migration 008 (per FINAL-L5-01's DB inventory) | Migration 037 (Sprint 19, per FINAL-L5-01's DB inventory) |
| Row count before this sprint's fix | 5 (FINAL-L5-01's seed, incorrectly linked to `service_jobs`) | 0 |
| Row count after this sprint's fix | 5 (untouched, unrelated to jobs now) | **5** (correctly linked to `service_jobs`) |

## Machine-readable
`booking-source-inventory.json`.
