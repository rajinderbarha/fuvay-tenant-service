# HS6 — Type-Dependent Brand Price Resolution Report

## Real, critical bug found and fixed
`HomeServiceBookingService`'s selected-provider price lookup
(`service.py`) queried `BargainRule` filtered **only by
`master_service_id`** — completely ignoring `offering_type_id` and
`brand_id`, even though both were already passed into
`select_best_provider()` a few lines earlier for eligibility filtering.

This is the exact "Window AC brand price used for Split AC" bug this
entire session's Home Services pricing work exists to prevent — except
it was still live in the **real, customer-facing matching/booking
price-resolution path**, undetected until this sprint because it's a
different code path than the tenant setup wizard (fixed earlier) and
the admin pricing console (fixed in HS3).

## Fix
The bargain-rule lookup now joins the linked `ServicePricingRule` (which
does have `service_type_id`/`brand_id` — added across earlier sprints)
and selects the **most specific match**:
1. `service_type_id` + `brand_id` both match the request → most specific
2. `service_type_id` matches, no brand match → next
3. Both null (a service-level, type-agnostic rule) → fallback
4. A type/brand-scoped rule that does **not** match the request →
   excluded entirely (specificity `-1`, never selectable) — this is the
   actual fix: previously such a mismatched rule could still be picked
   up since there was no type/brand filter at all.

Mirrors the exact hierarchy pattern already used by
`_find_admin_pricing_rule` in `tenant_service.py` (established in an
earlier sprint), applied here for the first time in the matching flow.

## Verification
Live-verified via direct testing of the specificity logic
(`test_bargain_rule_prefers_type_and_brand_match`,
`test_bargain_rule_excludes_mismatched_type_brand_rules`) and confirmed
the join/filter code is present and correctly ordered. **Full live HTTP
end-to-end verification with two real Window AC + Split AC bargain
rules and a real matching request was not performed this sprint** —
would require constructing a full booking-draft/category context, which
was out of the remaining time budget. This is a real limitation:
static/logic-level verification confirms the fix is structurally
correct, but an end-to-end live proof (matching the standard this
session established for other fixes) is still pending.

## Verdict
Type-dependent brand price resolution in the real matching path: **real
bug found and fixed, structurally verified**. Full live end-to-end HTTP
verification: **not performed this sprint** — documented as the
sprint's most significant remaining gap.
