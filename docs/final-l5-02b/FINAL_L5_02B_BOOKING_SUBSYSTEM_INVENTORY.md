# FINAL-L5-02B — Booking Subsystem Inventory

Live row counts captured this sprint (post FINAL-L5-01E's reset+reseed cycle, unchanged since):

| Table | Rows |
|---|---|
| `jobs` (legacy field_ops) | 0 |
| `service_jobs` (canonical) | 5 |
| `bookings` (generic booking engine) | 0 |
| `service_bookings` (canonical) | 5 |
| `home_service_booking_drafts` | 74 |
| `booking_drafts` | **does not exist** — this literal table name from the mission spec is not a real table; the real draft table is `home_service_booking_drafts` |

## Table-by-table

### `home_service_booking_drafts`
- **Purpose**: the customer-facing, multi-step in-progress booking flow (category/offering selection → issue/brand/address → serviceability → price estimate → provider matching → confirmation).
- **Migration introduced**: Sprint 16 (`migration 034`).
- **PK**: `id` (uuid). **FKs**: `customer_id → users`, `category_id → service_categories`, `offering_id → master_services`, `selected_tenant_id → tenants` (nullable until matched).
- **Tenant scope**: not fixed until a provider is matched (`selected_tenant_id` nullable).
- **Customer scope**: `customer_id` NOT NULL — always customer-owned.
- **Status/lifecycle**: `draft → collecting_details → price_estimated → matched → ready_for_confirmation → confirmed` (or `cancelled`/`expired`).
- **Write endpoints**: `POST /v1/customer/home-services/booking-drafts` (start), `PUT .../{id}` (update fields), `POST .../{id}/serviceability-check`, `.../price-estimate`, `.../match-and-price`, `.../confirm-price-choice`, `.../confirm` (terminal — converts to `service_bookings`+`service_jobs`), `.../cancel`.
- **Read endpoints**: `GET .../{id}`, `.../{id}/summary`.
- **Frontend consumers**: `frontend/customer-app/lib/api/customer-home-services.ts` (fully typed, real, matches every endpoint above).
- **Job relationship**: `service_bookings.draft_id → home_service_booking_drafts.id` (one draft → at most one confirmed booking; 74 draft rows vs 5 confirmed bookings reflects normal abandonment — most started drafts are never confirmed, which is expected real-world behavior, not a bug).
- **Status**: **CANONICAL** for the pre-confirmation flow. Row count (74) is high relative to confirmed bookings (5) because it accumulates every started-but-abandoned flow across this project's entire testing history (the reset script does not truncate it — see Idempotency report).

### `bookings`
- **Purpose**: a generic, cross-vertical booking engine table (used by non-Home-Services verticals per the multi-vertical catalog architecture, e.g. `project_p0_vertical_catalog` memory).
- **Tenant/customer scope**: generic, vertical-agnostic schema.
- **Write/read endpoints**: none in the Home Services flow write or read this table (confirmed via code trace — `home_service_assignment/customer_router.py` imports `ServiceBooking`, never `Booking`).
- **Frontend consumers (Home Services)**: none.
- **Status**: **LEGACY / OTHER-DOMAIN for Home Services** — real table, real purpose for other verticals, but not part of the Home Services booking lifecycle. 0 rows currently because no other-vertical bookings have been seeded in this environment.

### `service_bookings`
- **Purpose**: the confirmed, Home-Services-specific booking record — the customer-facing "your booking" entity.
- **Migration introduced**: `final_records` engine (Sprint 19, `migration 037`).
- **PK**: `id`. **FKs**: `draft_id → home_service_booking_drafts.id` (NOT NULL), `customer_id → users`, `tenant_id → tenants`, `category_id`, `offering_id`.
- **Tenant scope**: `tenant_id` NOT NULL, set at confirmation (the matched provider).
- **Customer scope**: `customer_id` NOT NULL.
- **Status/lifecycle**: `converted` (active/normal), `cancelled`.
- **Write endpoints**: created exclusively by `POST .../booking-drafts/{id}/confirm` (via `HomeServiceFinalCreationService.finalize()`), never written directly by any other endpoint.
- **Read endpoints**: `GET /v1/customer/bookings`, `GET /v1/customer/bookings/{id}`, `GET /v1/customer/bookings/{id}/tracking`, `POST/GET /v1/customer/bookings/{id}/rating`.
- **Frontend consumers**: `frontend/customer-app/lib/api/customer-home-services.ts` (`getCustomerBookings`, `getCustomerBookingDetail`, `getCustomerBookingTracking`, `submitCustomerBookingReview`).
- **Job relationship**: `service_jobs.booking_id → service_bookings.id`.
- **Status**: **CANONICAL** — confirmed via live DB query, live API response inspection, and source-code trace (Part 11 decision).

### `service_jobs`
- **Purpose**: the tenant/technician-facing execution record — assignment, scheduling, status, completion.
- **Migration introduced**: `final_records` engine (Sprint 19/20, `migration 037`/`038`).
- **PK**: `id`. **FKs**: `booking_id → service_bookings.id` (NOT NULL), `customer_id`, `tenant_id`, `assigned_staff_id`.
- **Status/lifecycle**: `new → assigned → in_progress → completed` / `cancelled`.
- **Write endpoints**: created by the same `finalize()` transaction that creates the `service_bookings` row (one booking → one job, 1:1 in this seed and in the real `finalize()` code path).
- **Read endpoints**: `/v1/provider/my-records/jobs*` (Tenant Jobs).
- **Job relationship**: this *is* the job.
- **Status**: **CANONICAL**.

## Customer flow trace (Parts 1-12 of the mission's required trace)
1. Draft created — `POST .../booking-drafts` → `home_service_booking_drafts` row, `status=draft`.
2. Service/type/brand/issue selected — `PUT .../booking-drafts/{id}` → same row updated, `status=collecting_details`.
3. Address/zipcode selected — same `PUT` call (address fields are part of the same update payload).
4. Matching performed — `POST .../match-and-price` → `provider_options`/`selected_provider_snapshot` populated on the draft; live-tested this sprint, correctly returns `422 HOME_BOOKING_NO_PROVIDER_AVAILABLE` when no eligible provider exists (a real, separate provider-bookability gate — see Booking Draft Workflow Report).
5. Price selected — `POST .../confirm-price-choice`.
6. Draft confirmed — `POST .../confirm`.
7. Final booking persisted — `service_bookings` row created (in the same transaction as step 8).
8. Provider/tenant job created — `service_jobs` row created (same transaction, via `HomeServiceFinalCreationService.finalize()`).
9. Customer booking list reads it — `GET /v1/customer/bookings` → `service_bookings` — **verified live this sprint, 5/5 seeded bookings visible to Customer One**.
10. Customer detail/tracking reads it — `GET /v1/customer/bookings/{id}` / `.../tracking` → joins `service_bookings` + `service_jobs` — **verified live this sprint**.
11. Cancellation updates it — `service_bookings.status = 'cancelled'` (seed demonstrates this for `L501-BK-0005`); no dedicated customer-facing cancel-after-confirmation endpoint currently exists (see Backend Alignment Report — documented gap, not fabricated).
12. Review links to it — `POST /v1/customer/bookings/{id}/rating`, reads/writes against the `service_bookings` row.

Machine-readable version: `booking-subsystem-inventory.json`.
