# Customer Price Experience — Test Results

## TypeScript

`npx tsc --noEmit` in `frontend/super-admin`: **0 errors, exit code 0**
(confirmed after the page rewrite and the `lib/api.ts` type changes).

## New certification tests

`pytest tests/test_customer_price_experience_calculation_fix.py`:
**21/21 passed.** Covers all 6 ticket test cases directly against the
real `compute_symmetric_customer_price_tiers` function (cases 1/2/3 exact
value assertions, case 6 validation-error assertion, plus explicit "High
!= pre-fee selected max" and "Low != raw selected min" hard-gate checks),
confirms the already-certified Tenant Wizard/Admin Catalog Console
examples are unaffected by the new `rounding_increment` parameter
(default unchanged), confirms the router uses the symmetric formula (not
the old asymmetric one) and validates the selected range against the
admin range before computing, confirms the full required response shape
(all 10 corrected fields + 5 backward-compat aliases), confirms the
frontend uses the renamed labels (Admin Allowed Min/Max, Selected Range
Min/Max) and no longer shows the confusing "Customer Min/Max Price"
labels, confirms the breakdown card shows fee-on-min and fee-on-max
separately (not the old wrong "Minimum/Maximum Allowed Customer Offer"
fields), confirms the API client sends `selected_min_price`/
`selected_max_price` not the old `customer_min_price`/`customer_max_price`
names, and confirms no forbidden/manual-bargain wording.

## Live evidence-based smoke test

Authenticated as `admin@serviceos.in` (super_admin):

```
POST /v1/admin/home-services/price-experience/preview
     {admin_min:300, admin_max:500, admin_base:400, selected_min:350, selected_max:420, fee:10}
  → 200 customer_low_price=385.0, customer_mid_price=425.0, customer_high_price=462.0
     (exact match to the ticket's bug-report example — this is the fix, live-verified)

POST .../preview {selected_min:350, selected_max:450, fee:10}
  → 200 customer_low_price=385.0, customer_mid_price=440.0, customer_high_price=495.0

POST .../preview {selected_min:250, selected_max:420}   (below admin min 300)
  → 422 SELECTED_RANGE_BELOW_ADMIN_MIN, request_id present

POST .../preview {selected_min:350, selected_max:520}   (above admin max 500)
  → 422 SELECTED_RANGE_ABOVE_ADMIN_MAX, request_id present

POST /v1/tenant/catalog/price-options/preview {tenant_min:350, tenant_max:420, fee:10}
  → 200 low_price=385.0, high_price=462.0
     (tenant side already used the correct symmetric formula before this
     ticket — confirmed still correct, untouched by this fix)
```

## Regression check

`pytest tests/test_customer_price_experience_calculation_fix.py
tests/test_deactivate_manual_bargain_auto_price_options.py
tests/test_bargain_customer_range_platform_fee.py
tests/test_provider_first_matching_and_price_choice.py
tests/test_home_services_only_bargain_scope.py
tests/test_home_services_menu_and_price_range.py
tests/test_admin_home_services_catalog_setup.py
tests/test_tenant_home_services_service_setup_wizard.py`:
**193/193 passed.**

Two pre-existing tests in `test_deactivate_manual_bargain_auto_price_options.py`
asserted the OLD, buggy wording/field names on this exact page
(`"customer minimum + platform fee"`, `"Minimum Allowed Customer Offer"`)
— updated to assert the corrected wording instead, since those old
assertions were literally describing the bug this ticket fixes. This is
a test-file update reflecting an intentional behavior change, not a
regression.

## Backend

No dedicated backend pytest file beyond the shared static-inspection +
direct-function-call file above — `compute_symmetric_customer_price_tiers`
is a pure, already-unit-testable function and is called directly (not
just grepped) in the new test file to verify exact numeric output.
