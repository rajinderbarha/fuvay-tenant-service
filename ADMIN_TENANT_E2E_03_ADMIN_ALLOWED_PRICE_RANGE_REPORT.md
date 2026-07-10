# Admin Allowed Price Range Verification (Part 6)

`/admin/home-services/pricing-rules` table columns (verified live and in source): Service, Type, Brand, Zone/Tier, **Admin Min**, **Admin Max**, **Platform Fee**, **Completed Job Deduction**, Status, Actions. Edit modal field labels are explicitly "Admin Minimum Price" / "Admin Maximum Price" / "Platform Fee %" / "Completed Job Deduction Credits" — never called "customer price", clearly namespaced as admin/platform-controlled boundaries.

DB baseline for Split AC + LG (`2ef804e7-...`): min_price 600, max_price 950, platform_fee_percent 10.00. Spec's illustrative baseline (Provider range 700-850) sits inside this admin-allowed band — consistent with the architecture: `service_pricing_rules` stores the **admin allowed range**, and the **provider's own selected range** (700-850) is a separate tenant-level record (`provider_pricing_overrides` / tenant service type price), validated to fall inside the admin range. This separation is real and matches the "Admin Allowed Range" vs "Provider Price Range" vs "Customer Price Options" distinction required by the spec.

`price-experience` page (`/admin/home-services/price-experience`) uses exactly the required labels: "Admin Allowed Min/Max", "Admin Base Price", "Selected Range Min/Max" (provider's chosen sub-range), "Platform Fee %", and outputs "Customer Low / Customer Mid / Customer High" — with an explicit "Payment Mode: Customer pays provider directly" row. No conflation of admin vs customer price observed anywhere in either page's labels.

City tier/zone/zipcode applicability: `pricing-rules` table's "Zone/Tier" column reads `r.zone ?? r.city` else "All Zones"; DB confirms `service_pricing_rules.zone`/`city`/`zipcode` columns exist and Ludhiana/141001 is tier-mapped via `tier_locations` (Mid tier) which the pricing rule model can reference by `tier_id`.

Result: PASS — admin price range terminology is clear, consistently separated from customer-facing pricing throughout both pages.
