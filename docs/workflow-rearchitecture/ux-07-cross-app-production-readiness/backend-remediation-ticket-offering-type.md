# Backend Remediation Ticket — offering_type_id Required-Field Contract Gap

**NOT implemented this round** (backend remediation is explicitly out of
UX-07 Round 2's scope) — specification only, for whoever owns
`app/engines/home_service_booking` / `app/engines/admin_catalog` next.

## Root cause

See `offering-type-contract-defect.md` for the full investigation. Summary:
`master_services.is_type_required = False` for `ac_repair`
(`a96e625a-60e1-46c0-bde4-ccbb88da50a2`), but its only 2 real
`ServicePricingRule` rows are both `service_type_id`-scoped with no
unscoped fallback — so `match-and-price` fails whenever `offering_type_id`
is omitted, even though the draft's own `required_fields` response (driven
by the same `is_type_required` flag) does not ask for it.

## Affected endpoints

- `GET`/derived `required_fields` field on
  `POST /v1/customer/home-services/booking-drafts` and
  `PUT /v1/customer/home-services/booking-drafts/{id}`
- `POST /v1/customer/home-services/booking-drafts/{id}/match-and-price`

## Affected service functions

- `app/engines/home_service_booking/service.py::_get_required_field_list`
- `app/engines/home_service_booking/service.py::_compute_missing_fields`
- `app/engines/home_service_booking/service.py`'s pricing-rule resolution
  block (`_spr_specificity` and its caller, ~lines 669-714)

## Reproduction steps (real, live-verified this round)

1. `POST /v1/customer/home-services/booking-drafts`
   `{category_slug:"home_services", offering_slug:"ac_repair"}`.
2. `PUT .../{id}` `{city:"Ludhiana", issue_summary:"...", brand_id:<LG>}`
   — deliberately omit `offering_type_id` (the response's own
   `required_fields` list does not include it).
3. `POST .../serviceability-check` -> succeeds.
4. `POST .../match-and-price` -> real
   `422 PRICE_OPTIONS_UNAVAILABLE: "This service does not have pricing
   configured yet."`
5. Repeat step 2 with `offering_type_id` set to the real "Split AC"
   `service_types` row (`c86dfcf3-53bd-4d83-bf0b-51257f382652`) -> step 4
   now succeeds with a real matched price.

## Expected vs actual behavior

- **Expected**: either `offering_type_id` is listed in `required_fields`
  for this offering (so clients ask for it upfront), OR a pricing rule
  exists that doesn't require it (so it's genuinely optional as promised).
- **Actual**: neither — the contract says optional, the pricing data says
  mandatory.

## Proposed contract fix (pick one, see full tradeoffs in
`offering-type-contract-defect.md`)

- **Recommended minimal fix**: set `master_services.is_type_required =
  True` for `ac_repair`, and audit all other offerings for the same
  pattern (any offering whose real `ServicePricingRule` set is 100%
  type-scoped with no unscoped fallback, but whose `is_type_required` flag
  is `False`).
- **Alternative**: add an unscoped fallback `ServicePricingRule` for
  `ac_repair` if "AC type optional for repair" is the actual desired
  product behavior.

## Required tests for the backend slice

1. A contract-consistency test across ALL real offerings: for any offering
   where every eligible `ServicePricingRule` is type-scoped, assert
   `is_type_required` is `True`.
2. A specific regression test for `ac_repair`'s `match-and-price` behavior
   with and without `offering_type_id`.
3. A write-time validation test: changing `is_type_required` to `False`
   for an offering whose pricing rules are all type-scoped should be
   rejected or warned at the catalog-config layer.

## Compatibility impact

Low. Setting `is_type_required = True` for `ac_repair` only changes the
`required_fields` response (additive — existing clients that already send
`offering_type_id`, like this round's manual verification, are unaffected;
clients that don't yet send it will start being told to, which is the
CORRECT, desired behavior change). No breaking schema change; no existing
booking/job data affected.
