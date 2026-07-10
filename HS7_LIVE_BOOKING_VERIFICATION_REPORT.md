# HS7 — Live Booking Verification Report

All scenarios verified against the real running backend (`localhost:8000`)
and the real Postgres dev database — genuine HTTP `curl` round trips, not
direct function calls (a stronger guarantee than prior sprints used for
comparable checks).

Real fixtures: `customer@serviceos.in` / `Password123!`; tenant "Demo AC
Services" `34b427a7-b2be-496c-b826-6d51bb181248`; AC Repair
`a96e625a-60e1-46c0-bde4-ccbb88da50a2`; Split AC `c86dfcf3-53bd-4d83-bf0b-51257f382652`;
LG `64a3b25f-23aa-4639-8baf-f67def0f60db`; Ludhiana zipcode `141001`.

## 1-8. Full happy-path flow
1. `POST /booking-drafts` (category=home_services, offering=ac_repair) →
   **500** (`MasterOffering` empty table bug) → fixed → **200**, draft created.
2. `PUT /booking-drafts/{id}` (type/brand/issue/city/zip/name/phone) → **200**.
3. `POST /{id}/serviceability-check` → **false** (`Tenant.category_id` NULL
   bug) → fixed → **200 serviceable: true, matched_by: zipcode**.
4. `POST /{id}/match-and-price` → **422** (`bargain_rules` table empty —
   missing reference data, seeded one real row) → **200**, selected
   provider "Demo AC Services", `Low 770 / Mid 850 / High 935`.
5. `POST /{id}/confirm-price-choice` `{"price_tier":"mid"}` → **200**
   (also caught the internal-score-leak bug here, fixed).
6. `POST /{id}/summary` → **200** (caught the booking_summary-overwrite
   bug here — price selection was being destroyed — fixed).
7. `POST /{id}/confirm` (`Idempotency-Key: hs7-live-test-1`) → **500**
   (missing `updated_at` columns, 4 tables, migrations 122-125) → fixed
   → **200**, `booking_number: BK-20260709-000001`,
   `selected_price_option: mid`, `selected_price_amount: 850.0`,
   `payment_mode: customer_pays_provider_directly`.
8. Retry same `/confirm` with same `Idempotency-Key` → **200**,
   `idempotent: true`, same booking number (after fixing a second-order
   regression from the mark_ready_for_confirmation wiring — see main report).

## 9. Modified price amount is rejected
`POST /{id}/confirm-price-choice` `{"price_tier":"custom","amount":1}` →
**422 `INVALID_PRICE_TIER`**. Confirmed the extra `amount` field is never
read by any code path.

## 10. Non-bookable provider booking is rejected
Second draft matched + priced normally, then
`UPDATE provider_visibility_statuses SET is_bookable=false` for the
selected tenant, then `POST /{id}/confirm` → **422
`SELECTED_PROVIDER_NOT_BOOKABLE`**, message: "Selected provider is no
longer available. Please match again." `is_bookable` and `tenants.status`
restored to their original values afterward, confirmed via a final query.

## 11. Customer booking detail loads
`GET /v1/customer/bookings/a3e533c2-...` → **200**, full customer-safe
detail (provider name/rating/badges only, selected price, payment mode).
`GET /v1/customer/bookings/{id}/tracking` → **500** (missing `updated_at`
on `service_job_assignment_events`) → fixed → **200**, timeline `[{event:
"Booking confirmed", status: "confirmed"}]`.

## 12. Customer-safe UI hides internal data
No `internal_score` or `matching_score_snapshot` present in any
post-fix customer-facing response (confirm-price-choice, summary,
booking list, booking detail) — confirmed by direct inspection of each
JSON payload captured this pass.

## Additional scenarios verified
- **Unsupported zipcode**: `city="Mumbai", zipcode="400001"` →
  `serviceability-check` → **200 serviceable: false**, message "This
  service is not available in Mumbai yet. We're expanding soon!"
- **Second independent booking**: `BK-20260709-000002`, tier=low,
  amount=770.0 — confirms the flow is repeatable, not a one-off.

## Dev-data changes made and their disposition
| Change | Reversed after? |
|---|---|
| `tenants.status` → `active` (was `pending_setup`) | Yes, restored |
| `provider_visibility_statuses.is_bookable` → `false` (scenario 10) | Yes, restored to `true` |
| 1 `bargain_rules` row inserted (AC Repair/Split AC/LG, 700-850, 10%) | **No** — legitimate missing catalog reference data, kept (see main flow report) |
| Migrations 122-125 applied | **No** — real schema fixes, kept |
| 2 real bookings created (`BK-...-000001`, `BK-...-000002`) | **No** — real, valid records; left in dev DB as evidence |

## Verdict
Live verification: **passed**, with 6 real bugs found and fixed along
the way (documented in full in `HS7_CUSTOMER_BOOKING_FLOW_REPORT.md`).
