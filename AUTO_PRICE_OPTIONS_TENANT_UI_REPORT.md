# Automatic Price Options — Tenant UI Report

## New page: `/provider/customer-price-preview` — Customer Price Preview

Replaces the (non-existent) "Tenant Bargain Settings" concept with a
read-only preview page. Added to the tenant sidebar's "Setup" group right
after "Pricing Setup".

## What the tenant can see

- A service picker (chips) across all their enabled offerings.
- For the selected service: Low / Mid / High price cards (Mid highlighted as
  the recommended tier), "Customer pays provider directly after service.",
  and "N usage credits will be deducted" after completion (from the real
  `ServicePricingRule.completed_job_deduction_credits` field).
- An explanation banner: "ServiceOS automatically creates customer price
  options from platform pricing and platform fee. You do not need to set up
  bargaining manually."
- A "Provider Matching Readiness" panel — real-time check of whether the
  tenant currently passes provider-matching eligibility, with a plain-English
  message (not raw gate codes).

## What the tenant cannot do

- **Cannot edit platform fee** — no input field exists anywhere on this page
  bound to `platform_fee_percent`; it's rendered read-only inside the
  computed price-tier response only.
- **Cannot configure a manual bargain rule** — the page never imports
  `bargainRulesApi`, never calls any bargain-rule create/update endpoint, and
  has no form for `customer_min_price`/`customer_max_price`/floor
  configuration. All 3 confirmed via static-inspection test.
- Both endpoints it calls (`customer-price-preview`, `matching-readiness`)
  are backend `GET`-only — verified via static inspection of the router
  source (no `@tenant_router.post`/`.put` in that section of the file).

## Live verification

`GET /v1/tenant/home-services/customer-price-preview?master_service_id=...`
(as `provider@serviceos.in`) → 200, returns Low ₹715 / Mid ₹910 / High ₹1100
for the real AC Repair bargain rule + pricing rule combination, plus
`completed_job_deduction_credits: 21` — matches the real seeded data exactly.

`GET /v1/tenant/home-services/matching-readiness?master_service_id=...` →
200, correctly reports `matching_ready: false` with an honest explanation
(the real test tenant's package is not yet active).

## Home Services scope guard

If `tenant.vertical !== "home_services"`, the page renders a blocked-state
card instead of any price/matching UI — same pattern used on the Service
Setup page from the prior sprint.
