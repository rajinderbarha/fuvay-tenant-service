# Tenant Business Profile — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. No dedicated Cover Photo upload capability

`ProfilePhotoUploader`'s `OwnerType` union only supports logo
(`provider_business`) and storefront photo (`provider_shop`) — there is no
`provider_cover` variant or backend endpoint. The hero banner and preview
modal both reuse the storefront photo as the cover background. If the
product wants a genuinely separate cover image, that requires a new backend
media endpoint + `OwnerType` addition — out of this ticket's scope to
fabricate.

## 2. No Gallery Images support

The Branding & Media tab shows an honest "not yet supported" placeholder
card instead of a working gallery uploader, since no backend endpoint exists
for multi-image galleries on the tenant business profile.

## 3. No PAN / Business Registration Number fields on the backend

The Legal & Verification tab shows these as read-only "Not collected" per
the ticket's field list, since `BusinessProfile`/`Tenant` has no column for
either — only GST number exists. Documented rather than fabricated as an
editable (but silently-discarded) input.

## 4. No public-preview or verification-document backend endpoints

`GET /v1/tenant/business-profile/public-preview` and document-upload
capability for the Legal & Verification tab don't exist. The preview modal
composes from already-fetched client state instead of a dedicated backend
call; the Verification Documents card shows an honest "no upload capability
exists yet" message rather than a fake upload button.

## 5. Total Services / Total Bookings / Average Rating show "—" in Quick Summary

No single endpoint on this page's data surface currently returns these 3
aggregate numbers for the tenant (they live in other, page-specific systems
— Offerings, Bookings, Reviews). Rather than call 3 more unrelated APIs
just to populate a summary card (and risk drifting from those pages' own
source of truth), they're shown as "—" with a hint pointing to the
canonical page. If desired, wiring 3 lightweight count endpoints could
replace these placeholders in a follow-up.

## 6. Permission model is coarse

Same limitation documented in the My Offerings/My Status sprints —
`/v1/auth/me` doesn't currently return a granular permissions array to this
frontend. Edit/Submit actions are gated on `canUpdate`/`canSubmit`, which
currently defaults to `true` for any authenticated tenant user (matching the
backend's actual `require_technician` gate on these endpoints, which allows
both `tenant_owner` and `technician` roles) rather than a finer-grained
`tenant.business_profile.update` check that doesn't exist yet client-side.

## 7. Pre-existing, unrelated build/tooling gaps

Same `useSearchParams`/`EnterpriseDataGrid` Suspense issue on
`/service-jobs` (unrelated to this page), no ESLint config, no `npm test`
script — all previously documented, all confirmed untouched by this sprint.
