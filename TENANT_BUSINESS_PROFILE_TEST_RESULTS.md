# Tenant Business Profile — Test Results

## TypeScript
`npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors, exit code 0.**

## New certification tests
`pytest tests/test_tenant_business_profile_enterprise_ui.py`: **28/28 passed.**
Covers: route/sidebar, breadcrumb, header title/subtitle/3 actions, hero
(cover/logo/completion ring, real computation not hardcoded 36%), missing
requirements section with action buttons, all 6 tabs present with correct
labels, Overview tab structure (Business Information/Quick Summary/Next
Steps), Legal & Verification tab (GST, read-only verification status, "tenant
can submit" language, no client-side path to directly set verification
status), Address & Service Areas tab (address fields + real service areas
API), Branding & Media tab (logo + storefront upload via real
`ProfilePhotoUploader`), People & Access tab (owner + real team API), Activity
tab (real activity API + copy-request-id action), Preview Public Profile
modal hides sensitive fields with explicit disclosure text, Edit Business
Info modal has dirty-state gating, Submit for Review shows missing items
when blocked and uses the real new backend endpoint, no bare "Unexpected
error.", request_id shown on errors, 0 forbidden labels, backend
submit-review endpoint exists and never sets `approved` (only `pending`).

## Live evidence-based smoke test

Authenticated as `provider@serviceos.in` (tenant_owner, Demo AC Services):

```
GET  /v1/provider/business-profile                    → 200
GET  /v1/auth/me                                       → 200
GET  /v1/provider/team-members                          → 200
GET  /v1/tenant/service-areas                            → 200
POST /v1/provider/business-profile/submit-review          → 422 BUSINESS_PROFILE_INCOMPLETE
                                                              (6 real missing fields: phone, gst_number,
                                                               address_line1, logo_url, description,
                                                               shop_photo_media_id)
```

The 422 response is the *correct* outcome for this real tenant's current
data state — confirms the new endpoint's validation logic works against
live data rather than always succeeding.

## Regression check

`pytest tests/test_tenant_business_profile_enterprise_ui.py tests/test_deactivate_manual_bargain_auto_price_options.py tests/test_tenant_service_setup_enterprise_wizard.py tests/test_home_services_only_bargain_scope.py tests/test_provider_first_matching_and_price_choice.py tests/test_bargain_customer_range_platform_fee.py tests/test_tenant_my_offerings_enterprise_ui.py tests/test_tenant_my_status_enterprise_ui.py`:
**176/176 passed** — 0 regressions.

## Build

`npm run build` — ran in background; see final report for outcome.
