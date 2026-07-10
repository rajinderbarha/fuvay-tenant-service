# Manual Bargain Module Deactivation Report

## Decision implemented

Manual bargain rule setup (admin-authored `BargainRule` records with a flat
floor or manually-entered customer range) is no longer the customer-facing
mechanism for Home Services pricing. It is replaced by fully automatic
Low/Mid/High price options, computed from admin platform pricing + platform
fee, after backend provider-first matching selects the provider — no manual
"bargain rule" authoring step in the flow customers or tenants interact with.

## What was deactivated

- **Admin navigation**: "Bargain Rules" removed from the "Pricing & Rules"
  nav group in `AdminLayout.tsx`.
- **Admin route** `/admin/pricing/bargain-rules`: kept working (backward
  compatible, per instruction not to delete certified backend logic) but now
  shows a deprecated banner ("Manual Bargain Rules are disabled. ServiceOS
  now automatically creates Low, Mid, and High customer price options for
  Home Services.") with a link to the new Customer Price Experience page,
  and its header/subtitle are marked `[Deprecated]`.
- **Tenant side**: no "Tenant Bargain Settings" page existed to begin with
  (confirmed via repo-wide search) — nothing to remove there. A new
  **read-only** "Customer Price Preview" page was added instead.

## What was kept (per instruction — do not delete certified backend logic)

- `BargainRule` model, `bargain_engine.py`, `evaluate_bargain` service
  method, and all `/v1/admin/pricing/bargain-rules/*` CRUD endpoints — fully
  intact and functional. They remain the actual data source the new
  automatic engine reads from (`customer_min_price`/`customer_max_price`/
  `platform_fee_percent` on `BargainRule`, linked `ServicePricingRule` for
  the admin range) — "deactivating manual setup" means removing the
  *human workflow* of authoring/browsing bargain rules as a primary UI, not
  deleting the data model that powers the automatic calculation.
- `matching_engine.py` (provider-first matching, Low/Mid/High formula, area
  comparison, Home Services scope guard) — unchanged, reused directly.

## Feature flags

Used the real, existing feature-flag system (`app.engines.settings_engine`,
table `feature_flags`) rather than inventing a parallel config file. New
helper `app/core/feature_flags.py::get_home_services_pricing_flags(db)`
reads (or defaults, if unseeded):

```
manual_bargain_rules_enabled    = False
auto_price_options_enabled      = True
provider_first_matching_enabled = True
home_services_only              = True
```

Exposed via `GET /v1/admin/home-services/config` — live-verified returning
exactly this shape.

## Verification

- Live-tested: `GET /v1/admin/home-services/config` → 200, correct defaults.
- Static-inspection test confirms "Bargain Rules" is absent from the admin
  Pricing & Rules nav group and the Home Services nav group exists with all
  3 new pages.
- Static-inspection test confirms the tenant nav has no "Bargain Settings"/
  "Bargain Rules"/"Manual Bargain" item anywhere.
