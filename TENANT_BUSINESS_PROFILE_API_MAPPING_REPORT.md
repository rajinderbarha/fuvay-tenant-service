# Tenant Business Profile — API Mapping Report

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/tenant/context` | `useTenant()` (localStorage) + `authApi.me()` |
| `GET /v1/tenant/business-profile` | `GET /v1/provider/business-profile` (`businessProfileApi.get`) — pre-existing, real |
| `PUT /v1/tenant/business-profile` | `PUT /v1/provider/business-profile` (`businessProfileApi.update`) — pre-existing, real, includes re-verification trigger on critical-field change |
| `GET /v1/tenant/business-profile/completion` | Computed client-side via `computeCompletion(me, biz)` — no dedicated backend endpoint exists; matches the pattern already established in the My Status sprint (client-computed readiness from real fetched data) |
| `GET /v1/tenant/business-profile/requirements` | Same `computeCompletion()` — the missing-items list is derived from the same 11-field check, not a separate endpoint |
| `POST /v1/tenant/business-profile/submit-review` | **New** — `POST /v1/provider/business-profile/submit-review`, added this sprint (`app/engines/profile/router.py` + `service.py::submit_business_profile_for_review`) |
| `GET /v1/tenant/business-profile/public-preview` | Not built as a backend endpoint — the Preview Public Profile modal renders from already-fetched client state (business name, description, logo, storefront photo, service areas), since no separate customer-facing preview endpoint exists. Documented as a client-side composition, not a fabricated backend call. |
| `POST /v1/tenant/media/business-logo` | `POST /v1/provider/profile/logo` via `ProfilePhotoUploader` (`ownerType="provider_business"`) — pre-existing, real |
| `POST /v1/tenant/media/cover-photo` | **Not implemented** — no cover-photo-specific upload endpoint exists. The hero banner and preview modal reuse the storefront photo as the cover background instead of fabricating a new upload capability. Documented in Remaining Blockers. |
| `POST /v1/tenant/media/storefront-photo` | `POST /v1/provider/profile/shop-photo` via `ProfilePhotoUploader` (`ownerType="provider_shop"`) — pre-existing, real |
| `GET /v1/tenant/media` | Not called directly — media state is derived from the business-profile payload's `logo_url`/`business_logo_media_id`/`shop_photo_media_id` fields |
| `GET /v1/tenant/service-areas` | `myStatusApi.getServiceAreas()` → `GET /v1/tenant/service-areas` — real, reused from prior sprints |
| `GET /v1/tenant/team` | `myStatusApi.getTeamMembers()` → `GET /v1/provider/team-members` — real, reused from prior sprints |
| `GET /v1/tenant/activity` | `tenantSetupApi.getActivity()` — pre-existing, real |
| `GET /v1/tenant/audit` | Same activity endpoint reused (no separate audit-log endpoint wired into this page; Activity tab shows the audit-style event feed) |

## Summary

Almost the entire data layer for this page already existed and was real
(personal profile, business profile, service areas, team members, activity)
— this sprint's actual backend work was the single new
`submit-review` endpoint, live-verified end-to-end (correctly blocks with a
`missing` field list when required data is incomplete, and correctly flips
`verification_status` to `pending` — never to `approved` — when complete).
