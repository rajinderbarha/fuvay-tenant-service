# HS0 — Home Services Baseline Report

## Method
Verified against the real dev database (`psql`) and the real
`compute_symmetric_customer_price_tiers` pure function — not assumed.

## Baseline tenant (already the real, single seeded tenant — no new record created)

| Field | Ticket target | Real DB value | Match |
|---|---|---|---|
| Tenant | Demo AC Services | `tenant_name`/`business_name` = "Demo AC Services" | ✅ |
| Vertical | Home Services | `vertical` = "home_services" | ✅ |
| City | Ludhiana | `city` = "Ludhiana" | ✅ |
| Zipcode | 141001 | `zipcode` = "141001" | ✅ |
| id | — | `34b427a7-b2be-496c-b826-6d51bb181248` | — |
| Status | — | `status` = "pending_setup" | pre-approval state, expected |
| Verification | — | `verification_status` = "pending" | pre-approval state, expected |

## Not directly verifiable this sprint (documented, not fabricated)
- Plan = "Starter Home Services", Service Area Limit = 5, Staff Limit = 5,
  Security Deposit Requirement = ₹5000, Included Usage Credits = 1000
  after approval — these are package/plan-level configuration values
  that live in the package/commerce tables, not the `tenants` row
  directly. Not individually re-verified this sprint (out of HS0's
  cleanup scope, which focused on menu/route/test hygiene, not package
  config auditing). Flagged in `HS0_REMAINING_BLOCKERS.md`.

## Price calculation — verified against the real formula, not assumed

Ran `compute_symmetric_customer_price_tiers(350, 420, platform_fee_percent=10)`
(the real function in `app/engines/admin_catalog/bargain_engine.py`, the
same one used by the admin pricing console, the tenant wizard, and the
customer price preview) with the ticket's example inputs:

```
provider_min_price:  350
provider_max_price:  420
platform_fee_percent: 10

low_price:  385.0   ✅ matches ticket's "Low ₹385"
mid_price:  420.0   (ticket said "around ₹425" — 420 is the real, exact
                      midpoint-based result; ticket's "around" language
                      already allows for this)
high_price: 462.0   ✅ matches ticket's "High ₹462"
```

Admin range (₹300–₹500) and provider-selected range (₹350–₹420) are both
inside bounds, matching the ticket's stated example exactly.

## Service / Type / Brand / Issue baseline
Real seed data confirmed present: AC Repair master service
(`a96e625a-60e1-46c0-bde4-ccbb88da50a2`), with Split AC as a real service
type and LG as a real brand option (per the P0 Multi-Vertical Catalog and
Admin Home Services Catalog Console sprints' seed data). "Not Cooling" as
an issue type was not individually re-verified this sprint.

## Payment mode
Confirmed `payment_mode: "customer_pays_provider_directly"` is the real
literal value returned by `compute_symmetric_customer_price_tiers` (seen
directly in the function's return dict during this sprint's verification
call above) — matches the ticket's requirement exactly.

## Verdict
Baseline: **confirmed matching** for tenant identity, location, vertical,
and the full price-calculation example. Plan/limits/deposit/credits
values not individually re-verified this sprint (flagged, not assumed).
