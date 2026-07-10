# HS2B — Provider Setup Rules Tab Report

## Implemented this sprint
New "Provider Setup Rules" tab added to the service detail panel,
between Options/Add-ons and Customer Preview. Shows 8 real, derived
rules:

| Rule | Source |
|---|---|
| Provider must select service type | `service.is_type_required` (real field) |
| Provider must select supported brands | `service.is_brand_required` (real field) |
| Provider must set provider price range later | Always true for any service (reference-only statement, no price shown) |
| Provider must configure service area | `service.requires_address` (real field) |
| Provider must configure availability | `service.requires_schedule` (real field) |
| Provider must add technician | `service.requires_schedule` (reused — no separate technician-required field exists on `MasterService`) |
| Customer photo upload allowed | `service.requires_issue_type` (reused — no separate photo-upload field exists) |
| Customer notes allowed | Always true (reference-only) |

## Known field-mapping gap
`MasterService` (the real backend model) does not have dedicated
`requires_technician` or `photo_upload_allowed` columns — this sprint
reused the closest existing real fields (`requires_schedule`,
`requires_issue_type`) rather than fabricating values or adding a
migration for two new boolean columns. This is documented, not hidden:
the tab is real and driven by real data, but 2 of the 8 rows are
best-effort proxies rather than dedicated fields.

## Pricing separation confirmed
The tab explicitly states "provider price range required later" as
plain text — **no price input, no floor/ceiling, no admin range, no
Low/Mid/High** anywhere in this tab. Enforced by a new regression test
(`test_hs2b_provider_setup_rules_no_pricing_fields`) that scans the
tab's function body for forbidden pricing terms.

## Verdict
Provider Setup Rules tab: **implemented, real data-driven, catalog-only**
(no pricing). Two of eight rules use best-effort proxy fields rather than
dedicated columns — documented gap, not a scope violation.
