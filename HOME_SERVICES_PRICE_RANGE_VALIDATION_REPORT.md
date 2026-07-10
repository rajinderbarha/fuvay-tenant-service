# Home Services Price Range Validation Report

## Backend validation (source of truth — not just frontend)

`app/engines/admin_catalog/tenant_service.py::set_type_pricing` /
`set_brand_pricing` (built in the prior sprint, re-verified live this
sprint):

1. Loads the real admin pricing rule for the service/type(/brand) —
   `admin_floor = rule.min_price`, `admin_ceiling = rule.max_price`.
2. If no admin rule exists yet: `ADMIN_PRICE_RANGE_NOT_CONFIGURED` (422)
   — tenant cannot set a price until admin defines a range (matches
   ticket rule 5: "Reject missing admin rule unless draft allowed" — no
   draft-allowed exception exists, since publishing an unpriced type is
   separately blocked at publish time, not at price-entry time).
3. `tenant_min > tenant_max` → `INVALID_PRICE_RANGE` (422).
4. `tenant_min < admin_floor` → `TENANT_PRICE_BELOW_ADMIN_MIN` (422),
   message: *"Your minimum price cannot be below the admin floor (Rs.
   {admin_floor})."*
5. `tenant_max > admin_ceiling` → `TENANT_PRICE_ABOVE_ADMIN_MAX` (422),
   message: *"Your maximum price cannot exceed the admin ceiling (Rs.
   {admin_ceiling})."*
6. Every error response includes `request_id` (via the platform-wide
   `ServiceOSException` → RFC 7807 problem+json handler).

Brand override additionally requires `MasterServiceBrand.can_override_price
== True` (`BRAND_OVERRIDE_NOT_ALLOWED`, 422) before any range check runs —
routing-only brands can never receive a price override, by construction.

## Live re-verification this sprint

```
PUT .../types/{Window AC}/pricing {100, 200}   → 422 TENANT_PRICE_BELOW_ADMIN_MIN (admin floor Rs. 550.00)
PUT .../types/{Window AC}/pricing {600, 9999}  → 422 TENANT_PRICE_ABOVE_ADMIN_MAX (admin ceiling Rs. 1500.00)
```

Both errors returned real `request_id` values (`req_44188ca6f80e`,
`req_54ba19952382`), confirming the platform-wide error envelope is
intact.

## Formula verification (Customer Low/Mid/High)

`compute_symmetric_customer_price_tiers(800, 1000, 10)` (the exact
provider range from this ticket's own example) returns `low_price=880.0,
mid_price=990.0, high_price=1100.0` — an exact match to the ticket's
"Customer sees after platform fee: Low ₹880 / Mid ₹990 / High ₹1100."
Confirmed `low_price != 800.0` (the raw provider min) — the hard "Customer
Low must not show provider min before fee" rule holds.

## Result

**PASS** — the platform floor (no tenant can undercut the admin minimum)
and ceiling (no tenant can overcharge past the admin maximum) are both
enforced server-side, independent of any frontend validation, and were
never touched or weakened by this sprint's menu-reorganization work.
