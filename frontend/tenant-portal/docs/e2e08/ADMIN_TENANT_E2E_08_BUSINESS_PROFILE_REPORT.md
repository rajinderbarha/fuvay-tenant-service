# ADMIN-TENANT-E2E-08: Business Profile Report

**Date:** 2026-07-10  
**File:** `app/(tenant)/profile/page.tsx`

## Page Structure
5-tab layout: Overview | Legal & Verification | Address & Service Areas | People & Access | Activity

## API Usage
- `profileApi.getProfile()` — personal info
- `businessProfileApi.get()` — business info
- `providerStatusApi.get()` — bookability/visibility status
- `tenantSetupApi.getActivity(1)` — activity feed
- `myStatusApi.getTeamMembers()` — staff list
- `myStatusApi.getServiceAreas()` — area summary
- `authApi.me()` — current user/permissions
- `mediaAssetApi.uploadBusinessLogo()` + `uploadShopPhoto()` — media uploads

## Profile Completion Engine
`computeCompletion()` checks 11 items: owner name, owner phone, business name, email, phone, GST, address, city+state, logo, description, storefront photo. Shows missing items with "Add Now" / "Upload" CTAs.

## Mutations
- Save personal details: `profileApi.updateProfile()`
- Save business info: `businessProfileApi.update()` — triggers re-verification warning if critical fields changed
- Save address: `businessProfileApi.update()` (separate dirty tracking)
- Submit for review: `businessProfileApi.submitForReview()`
- Logo upload: `mediaAssetApi.uploadBusinessLogo()`
- Cover photo upload: `mediaAssetApi.uploadShopPhoto()`
- Owner phone save: `profileApi.updateProfile({ phone })`

## HeroCard
Dark panel with inline clickable logo/cover upload. Hover overlays show camera icon. Completion ring (SVG) shows profile % complete.

## Forbidden Labels Scan
No "Cash Wallet", "Wallet Balance", "Withdraw" (financial), "Escrow", "Bargain" found.  
"Your Business" appears as a fallback inside `safeText(biz?.business_name, "Your Business")` — this is a valid UI fallback, not hardcoded non-API data.

## Direct fetch() Scan
Zero direct `fetch()` calls. All `.refetch()` calls are from `useApi` hook.

## Known Hardcoded Values
- `Category` field shows "Air Conditioner Services" — this is a placeholder. Should read from `bizApi.data` or be removed.
- Address tab shows `totalAreas / 5 areas used` — hardcodes the 5-slot limit. The service-areas page reads this from `providerServiceAreasApi.getLimits()` correctly; the profile page uses a hardcoded `5`.

## Issues
- Category field hardcodes "Air Conditioner Services" (line ~739, ~1083) — should come from API or be removed. **Non-blocking P2.**
- Address tab hardcodes 5-slot area limit — should use `limitsApi` or leave dynamic. **Non-blocking P2.**
