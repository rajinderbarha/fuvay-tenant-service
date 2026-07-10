# Bargain Module — Remaining Blockers

None of these block `READY_BARGAIN_CUSTOMER_RANGE_PLATFORM_FEE_CERTIFIED` — honestly documented,
non-blocking notes.

## 1. No live customer-facing bargain UI component exists yet to update

Searched the whole frontend tree for a component displaying a customer-facing bargain/price
range; none exists in either `frontend/tenant-portal` or `frontend/super-admin` outside the
admin bargain-rules page (which is tenant/admin-facing, not customer-facing, and was updated).
The ticket's "Customer UI Display Rule" (show ₹385–₹450, never ₹350–₹450) is satisfied
structurally — the backend's `evaluate_bargain`/`BargainEvaluationResponse` now returns
`allowed_offer_min`/`allowed_offer_max` as the correct, fee-inclusive range — but there is no
existing customer-facing screen in this repo to visually verify the rule against. Any future
customer bargain UI built against this API will automatically show the correct range, since the
backend never exposes the pre-fee `customer_min_price` as if it were bookable.

## 2. Legacy flat-floor bargain rules coexist with the new customer-range rules

Rules created before this fix (no `customer_min_price` set) continue to evaluate against the
flat `floor_amount`, unchanged, for backward compatibility. This is intentional (not a defect)
but means the platform currently has two bargain-evaluation code paths side by side. A future
cleanup sprint could migrate all remaining flat-floor rules to the customer-range model once
admins have set a customer range for each.

## 3. `platform_fee_percent` duplication between `BargainRule` and `ServicePricingRule`

`BargainRule.platform_fee_percent` is a new, optional override; when unset, the evaluator falls
back to the linked `ServicePricingRule.platform_fee_percent`. This avoids requiring admins to
configure the fee twice, but means the effective fee for a given rule can come from either of two
tables — documented here for clarity, not a defect (the fallback order is explicit and tested).

## 4. Pre-existing, unrelated OpenAPI duplicate-operation-ID warnings

`app.openapi()` emits duplicate-operation-ID warnings for `service_option_admin_router.py` and
`service_setup/templates_router.py` — confirmed pre-existing (unrelated to any file this sprint
touched) and non-fatal (the schema still builds successfully). Not fixed here as out of scope for
the bargain module.
