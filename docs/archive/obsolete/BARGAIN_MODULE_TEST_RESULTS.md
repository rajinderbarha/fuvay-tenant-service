# Bargain Module — Customer Range + Platform Fee Floor Fix — Test Results

## Pure-function unit tests (no DB required)

`pytest tests/test_bargain_customer_range_platform_fee.py`: **19/19 passed.**

Covers all 8 required ticket cases plus formula/validation/schema checks:

| Case | Scenario | Expected | Result |
|---|---|---|---|
| 1 | offer ₹350 | rejected (below ₹385 floor) | ✅ |
| 2 | offer ₹384 | rejected | ✅ |
| 3 | offer ₹385 | accepted (boundary, inclusive) | ✅ |
| 4 | offer ₹400 | accepted | ✅ |
| 5 | offer ₹451 | rejected (above customer max) | ✅ |
| 6 | customer_min ₹250 < admin_min ₹300 | rejected at config time | ✅ |
| 7 | customer_max ₹550 > admin_max ₹500 | rejected at config time | ✅ |
| 8 | customer ₹450–₹460, fee 10% → floor ₹495 | invalid — "Customer range is too narrow after platform fee." | ✅ |

Plus: formula correctness (`350 * 1.10 = 385`, fixed-fee variant), base price never
used as floor, admin-range validation, customer-range validation, negative-fee
rejection, full response-shape field-name check, exact ticket JSON example
match (offer 380 → rejected with all fields matching the ticket's example
byte-for-byte on values), `provider_approval_required` decision path.

## Live evidence-based smoke test (DB-backed service + real API)

Authenticated as `admin@serviceos.in` (super_admin). Real service: AC Repair
(`a96e625a-60e1-46c0-bde4-ccbb88da50a2`), real pricing rule (min ₹600, max
₹1200, base ₹800). Updated the existing "AC Repair Bargain" rule with
`customer_min_price=650, customer_max_price=1100, platform_fee_percent=10`:

```
PUT /v1/admin/pricing/bargain-rules/{id} → floor_amount computed as 715.0 (650 × 1.10) ✅

POST /v1/admin/pricing/bargain/evaluate-preview {offer_price: 700}  → decision: rejected,
  reason: "Offer is below the minimum allowed price after platform fee.", bargain_floor: 715.0 ✅
POST .../evaluate-preview {offer_price: 715}  → decision: accepted,
  reason: "Offer is within the allowed bargain range." ✅
POST .../evaluate-preview {offer_price: 1150} → decision: rejected,
  reason: "Offer is above selected customer range." ✅

PUT .../bargain-rules/{id} {customer_min_price: 1100, customer_max_price: 1150, platform_fee_percent: 10}
  → 422 CUSTOMER_RANGE_TOO_NARROW,
    "Customer range is too narrow after platform fee. Increase max price or reduce min price." ✅
```

All values match the pure-function tests' formula exactly; the DB-backed path and
the pure `bargain_engine` path are provably consistent (the service delegates
directly to the pure function).

## Regression check

`pytest tests/test_bargain_customer_range_platform_fee.py tests/test_tenant_my_offerings_enterprise_ui.py tests/test_tenant_my_status_enterprise_ui.py tests/test_phase7_staff_app_certification.py tests/test_phase7b_staff_frontend_certification.py`:
**98/98 passed** — 0 regressions from this sprint's changes.

## TypeScript

`npx tsc --noEmit` in `frontend/super-admin`: **0 errors, exit code 0** (updated
`BargainRule`/`BargainEvaluationResult` interfaces, bargain-rules admin page
form + preview breakdown).

## OpenAPI / Swagger

Verified via `app.openapi()` directly: `BargainEvaluationResponse` schema is
registered and its `properties` include `bargain_floor`, `allowed_offer_min`,
`allowed_offer_max`, `customer_min_price`, `customer_max_price`,
`platform_fee_percent`, `platform_fee_amount` — confirmed programmatically,
not just by inspection of the source.

## Backend import/startup sanity

`python -c "from app.main import app; app.openapi()"` — succeeds, app builds
its full route table and OpenAPI schema without error (pre-existing, unrelated
duplicate-operation-ID warnings for `service_option_admin_router.py`/
`templates_router.py` observed — not introduced by this sprint, not fatal).
