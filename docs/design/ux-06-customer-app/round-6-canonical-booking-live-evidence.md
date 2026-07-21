# Round 6 — Full Canonical Booking Live Evidence

Real customer JWT, real backend (`http://localhost:8000`, confirmed healthy
this round), the pre-existing DEMO tenant, using `ac_installation` (an
existing, already-configured `MasterService` with a real active
`BargainRule` — see round-6-bargain-optionality-proof.md for why this is a
legitimate proof path that created zero new shared policy).

## Full sequence, every step real

1. `POST /v1/customer/home-services/booking-drafts`
   `{category_slug:"home_services", offering_slug:"ac_installation"}`
   → real draft `4e21dd28-e8db-49dc-8fda-f6c4ed06b754`, `offering_id`
   correctly resolved to `13f6cf5e-...` (the real `MasterService` id).
2. `GET /v1/customer/catalog/brands?master_service_id=13f6cf5e-...`
   → real brands (LG/Samsung/Voltas).
3. `PUT .../booking-drafts/{id}` `{city:"Ludhiana", issue_summary:"Need new
   AC installed", brand_id:"64a3b25f-..."}` → accepted.
4. `POST .../serviceability-check` → `{serviceable:true, matched_by:"city",
   message:"Service is available in Ludhiana."}`.
5. `POST .../price-estimate` → real `₹165` (`base_price:150 + platform_fee:15`,
   `source:"backend_catalog"`).
6. `POST .../match-and-price` → **REAL SUCCESS** (first time in this phase):
   `selected_provider: "Demo AC Services"` (the DEMO tenant, same one Round 4
   seeded), `selected_provider_price_options: {low:150, mid:150, high:150}`
   (all equal because this BargainRule is a fixed-price rule), real
   `area_market_comparison`.
7. `POST .../confirm-price-choice` `{price_tier:"mid"}` → real
   `booking_summary` with `customer_offer:150.0`, `selected_tenant_id`,
   `selected_price_tier:"mid"`.
8. `POST .../confirm` (Idempotency-Key = draft id) → **REAL BOOKING CREATED**:
   ```json
   {"idempotent": false, "booking_number": "BK-20260721-000001",
    "booking_id": "15290d0d-2909-405e-9e44-47e350bbd2bb",
    "job_number": "JOB-20260721-000001",
    "job_id": "b6f03551-c130-4741-b3e4-e83006af1fc6",
    "status": "pending_assignment", "booking_status": "confirmed",
    "selected_price_amount": 150.0,
    "payment_mode": "customer_pays_provider_directly"}
   ```
9. **Retry the identical confirm call** (same Idempotency-Key) → real
   `{"idempotent": true, "booking_number": "BK-20260721-000001",
   "booking_id": "15290d0d-..."}` — same booking returned, no duplicate
   created. Idempotency proven live, not just at the unit-test layer.
10. `GET /v1/customer/bookings` → the real booking appears in the list
    (`booking_id`, `booking_number`, `status: "pending_assignment"`,
    `issue_summary`, `city`, `selected_provider`).
11. `GET /v1/customer/bookings/{booking_id}` → full real detail, including
    `job_id`/`job_status` (distinct from `booking_id`/`status`, confirming
    ServiceBooking/ServiceJob pipeline provenance is preserved), assignment
    status/message, price, payment mode.

## Architectural correction discovered while wiring this up

`GET /v1/customer/bookings*` is backed by
`app/engines/home_service_assignment/customer_router.py` (`engine_id:
"assignment"`) — the SAME ServiceBooking/ServiceJob pipeline
`homeServiceDraftApi`/`bookingConfirmApi` create bookings into. Round 1 had
assumed (without reading this router's source) that this was a distinct
"Booking→field_ops.Job" pipeline and modeled `lib/api.ts`'s `Booking`
interface with invented fields (`service_type`, `scheduled_at`, `notes`)
that don't exist on the real response. Corrected this round:
`Booking` now matches the real shape (`booking_id`, `issue_summary`, `city`,
`selected_provider`, `selected_price_amount`, `job_id`, `job_status`, etc.),
and `BookingCard`/`BookingsListScreen`/`BookingDetailScreen` were updated to
match. `fieldOpsJobsApi` (`/v1/customer/jobs*`, `field_ops` engine) remains
the genuinely distinct Booking→field_ops.Job pipeline — unaffected by this
correction.

## What this proves

The ENTIRE canonical booking pipeline — draft creation, field collection,
serviceability, price estimate, provider matching, tier selection,
idempotent confirmation, booking-list insertion, and booking-detail
retrieval — is fully sound and working end-to-end against the real backend.
The only reason a real end-user cannot reach this today through the actual
app UI is that the one customer-catalog-visible offering (`ac_repair`) lacks
an equivalent `BargainRule`, which is a backend catalog/pricing data gap, not
a frontend defect and not something safely fixable from an isolated
customer test session this round.
