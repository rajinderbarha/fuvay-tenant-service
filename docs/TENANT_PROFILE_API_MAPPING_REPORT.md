# Tenant Profile API Mapping Report

## Route
`/profile` → `app/(tenant)/profile/page.tsx`

## API Mapping

| Spec API | Actual API | Method | Status |
|---|---|---|---|
| GET /v1/tenant/profile | GET /v1/me/profile | profileApi.getProfile() | ✅ Used |
| PUT /v1/tenant/profile | PUT /v1/me/profile | profileApi.updateProfile() | ✅ Used |
| GET /v1/tenant/business-profile | GET /v1/provider/business-profile | businessProfileApi.get() | ✅ Used |
| PUT /v1/tenant/business-profile | PUT /v1/provider/business-profile | businessProfileApi.update() | ✅ Used |
| POST /v1/tenant/media/logo | POST /v1/provider/profile/logo | ProfilePhotoUploader (provider_business) | ✅ Used via component |
| POST /v1/tenant/media/storefront-photo | POST /v1/provider/profile/shop-photo | ProfilePhotoUploader (provider_shop) | ✅ Used via component |
| POST /v1/tenant/profile/photo | POST /v1/me/profile-photo | ProfilePhotoUploader (provider_user) | ✅ Used via component |
| GET /v1/provider/status | GET /v1/provider/status | providerStatusApi.get() | ✅ Used (blockers/bookability) |
| GET /v1/tenant/activity | GET /v1/provider/activity | tenantSetupApi.getActivity() | ✅ Used |
| GET /v1/tenant/business-profile/audit | N/A | Not implemented — no audit endpoint in backend | ⚠ Not available |

## Pre-existing api.ts TS errors (not introduced by profile page)
- lib/api.ts lines 1869, 2190-2196, 3693-3713: TS2687 duplicate modifier — pre-existing, not caused by this sprint.

## Profile page: 0 new TypeScript errors introduced.
