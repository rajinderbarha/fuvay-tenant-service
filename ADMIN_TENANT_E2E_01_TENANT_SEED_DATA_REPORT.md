# ADMIN_TENANT_E2E_01 — Tenant/Provider Seed Data Report

Tenant: **Demo AC Services** (`34b427a7-b2be-496c-b826-6d51bb181248`), verified live via psql + real API,
not assumed.

| Requirement | Verified state |
|---|---|
| Tenant active/approved | `status='active'`, `verification_status='approved'` (confirmed via `tenants` table and `/v1/provider/business-profile`) |
| Business profile complete | business_name, owner_name, phone, email, gst_number, address, city (Ludhiana), state (Punjab), zipcode 141001, logo, description all populated |
| Service area covers 141001 | confirmed — match-and-price returns this tenant for zipcode 141001 |
| Home Services enabled | `category_type: "home_services"` in `/v1/tenant/dashboard/runtime` |
| AC Repair published, Split AC enabled, LG brand enabled, Not Cooling issue enabled | confirmed via real `match-and-price` call with `offering_slug=ac_repair`, `offering_type_id` (Split AC), `brand_id` (LG), `issue_summary="Not Cooling"` — returned a `selected_provider` |
| Type-specific price rule for Split AC + LG | confirmed — `selected_provider_price_options` returned `low_price=770, mid_price=850, high_price=935 INR` |
| Usage credit balance sufficient / bookable | `selected_provider` present in match result = bookable |
| Matching returns selected provider | `selected_provider.tenant_id == 34b427a7-b2be-496c-b826-6d51bb181248`, `provider_name: "Demo AC Services"` |

## Real API call used for verification (twice — before and after Part 8's read-only probe)
```
POST /v1/customer/home-services/booking-drafts {category_slug:"home_services", offering_slug:"ac_repair"}
PUT  /v1/customer/home-services/booking-drafts/{id} {issue_summary, city, zipcode, offering_type_id, brand_id}
POST /v1/customer/home-services/booking-drafts/{id}/match-and-price
-> {"selected_provider":{"tenant_id":"34b427a7-...","provider_name":"Demo AC Services", ...},
    "selected_provider_price_options":{"low_price":770.0,"mid_price":850.0,"high_price":935.0,"currency":"INR"}}
```

## Incident during this sprint (found and fixed, not left broken)
Part 8's read-only-permission-smoke test discovered that `PUT /v1/provider/business-profile` has **no
access_scope enforcement** — a `customer_support_limited` user was able to change `business_name` to
`"Should Not Be Allowed"` and trigger `verification_status='changes_pending_review'` for real. This was
caught, the tenant row was restored (`business_name='Demo AC Services'`, `verification_status='approved'`)
via direct SQL, and bookability was re-verified end-to-end (see call above) after the restore. The test
itself was then patched to read-before-write and restore the original `business_name` after each probe so
future runs do not corrupt seed data (residual `verification_status` side-effect still requires a DB
fix after each run — documented in READONLY_PERMISSION_SMOKE_REPORT.md as a known limitation of this
particular endpoint, not of the E2E harness).

## Result
PASS — no genuine seed gaps found; tenant was already fully bookable from the prior customer-app sprint.
One real backend RBAC gap found, documented, and the accidental data mutation it caused was fully
reverted and re-verified.
