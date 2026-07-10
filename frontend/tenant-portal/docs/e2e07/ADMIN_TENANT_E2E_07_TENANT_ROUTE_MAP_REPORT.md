# E2E-07 Tenant Route Map Report
**Date:** 2026-07-10  
**Sprint:** E2E-07 Certification  
**Portal:** Tenant Portal (`frontend/tenant-portal`)  
**Analysis:** Static analysis only — browser verification pending

---

## Route Map — `app/(tenant)/`

All routes are under the `(tenant)` route group, wrapped by `app/(tenant)/layout.tsx` which renders `TenantLayout`.

| URL Path | File | Type |
|---|---|---|
| `/dashboard` | `app/(tenant)/dashboard/page.tsx` | Content |
| `/profile` | `app/(tenant)/profile/page.tsx` | Content |
| `/account` | `app/(tenant)/account/page.tsx` | Content |
| `/account/credits` | `app/(tenant)/account/credits/page.tsx` | Content |
| `/account/privacy` | `app/(tenant)/account/privacy/page.tsx` | Content |
| `/account/privacy/requests` | `app/(tenant)/account/privacy/requests/page.tsx` | Content |
| `/account/privacy/requests/[id]` | `app/(tenant)/account/privacy/requests/[id]/page.tsx` | Content |
| `/activity` | `app/(tenant)/activity/page.tsx` | Content |
| `/ai-chat` | `app/(tenant)/ai-chat/page.tsx` | Content |
| `/analytics` | `app/(tenant)/analytics/page.tsx` | Content |
| `/analytics/financial` | `app/(tenant)/analytics/financial/page.tsx` | Content |
| `/analytics/staff` | `app/(tenant)/analytics/staff/page.tsx` | Content |
| `/analytics/quality` | `app/(tenant)/analytics/quality/page.tsx` | Content |
| `/analytics/complaints` | `app/(tenant)/analytics/complaints/page.tsx` | Content |
| `/analytics/alerts` | `app/(tenant)/analytics/alerts/page.tsx` | Content |
| `/appointments` | `app/(tenant)/appointments/page.tsx` | Content |
| `/bookings` | `app/(tenant)/bookings/page.tsx` | Content |
| `/bookings/[id]` | `app/(tenant)/bookings/[id]/page.tsx` | Content |
| `/catalog` | `app/(tenant)/catalog/page.tsx` | Content |
| `/chat` | `app/(tenant)/chat/page.tsx` | Content |
| `/customers` | `app/(tenant)/customers/page.tsx` | Content |
| `/customers/[id]` | `app/(tenant)/customers/[id]/page.tsx` | Content |
| `/dispatch` | `app/(tenant)/dispatch/page.tsx` | Content |
| `/documents` | `app/(tenant)/documents/page.tsx` | Content |
| `/finance` | `app/(tenant)/finance/page.tsx` | Content |
| `/finance/package` | `app/(tenant)/finance/package/page.tsx` | Content |
| `/finance/security-deposit` | `app/(tenant)/finance/security-deposit/page.tsx` | Content |
| `/finance/usage-credit-ledger` | `app/(tenant)/finance/usage-credit-ledger/page.tsx` | Content |
| `/insights` | `app/(tenant)/insights/page.tsx` | Content |
| `/inventory` | `app/(tenant)/inventory/page.tsx` | Content |
| `/jobs` | `app/(tenant)/jobs/page.tsx` | Content |
| `/jobs/[id]` | `app/(tenant)/jobs/[id]/page.tsx` | Content |
| `/marketing` | `app/(tenant)/marketing/page.tsx` | Content |
| `/marketing/campaign-impact` | `app/(tenant)/marketing/campaign-impact/page.tsx` | Content |
| `/marketing/visibility` | `app/(tenant)/marketing/visibility/page.tsx` | Content |
| `/media` | `app/(tenant)/media/page.tsx` | Content |
| `/notifications` | `app/(tenant)/notifications/page.tsx` | Content |
| `/onboarding-status` | `app/(tenant)/onboarding-status/page.tsx` | Content |
| `/packages` | `app/(tenant)/packages/page.tsx` | Content |
| `/provider/availability` | `app/(tenant)/provider/availability/page.tsx` | Content |
| `/provider/chat` | `app/(tenant)/provider/chat/page.tsx` | Content |
| `/provider/complaints` | `app/(tenant)/provider/complaints/page.tsx` | Content |
| `/provider/compliance` | `app/(tenant)/provider/compliance/page.tsx` | Content |
| `/provider/compliance/requests/[id]` | `app/(tenant)/provider/compliance/requests/[id]/page.tsx` | Content |
| `/provider/customer-price-preview` | `app/(tenant)/provider/customer-price-preview/page.tsx` | Content |
| `/provider/marketing` | `app/(tenant)/provider/marketing/page.tsx` | Content |
| `/provider/notifications` | `app/(tenant)/provider/notifications/page.tsx` | Content |
| `/provider/offerings` | `app/(tenant)/provider/offerings/page.tsx` | Content |
| `/provider/pricing` | `app/(tenant)/provider/pricing/page.tsx` | Content |
| `/provider/refund-requests` | `app/(tenant)/provider/refund-requests/page.tsx` | Content |
| `/provider/reviews` | `app/(tenant)/provider/reviews/page.tsx` | Content |
| `/provider/reviews/summary` | `app/(tenant)/provider/reviews/summary/page.tsx` | Content |
| `/provider/reviews/staff-summary` | `app/(tenant)/provider/reviews/staff-summary/page.tsx` | Content |
| `/provider/rework-requests` | `app/(tenant)/provider/rework-requests/page.tsx` | Content |
| `/provider/service-areas` | `app/(tenant)/provider/service-areas/page.tsx` | Content |
| `/provider/service-coverage` | `app/(tenant)/provider/service-coverage/page.tsx` | Content |
| `/provider/service-invoices` | `app/(tenant)/provider/service-invoices/page.tsx` | Content |
| `/provider/service-options` | `app/(tenant)/provider/service-options/page.tsx` | Content |
| `/provider/service-setup` | `app/(tenant)/provider/service-setup/page.tsx` | Content |
| `/provider/services` | `app/(tenant)/provider/services/page.tsx` | Content |
| `/provider/staff` | `app/(tenant)/provider/staff/page.tsx` | Content |
| `/provider/status` | `app/(tenant)/provider/status/page.tsx` | Content |
| `/provider/subscription-status` | `app/(tenant)/provider/subscription-status/page.tsx` | Content |
| `/provider/team-members` | `app/(tenant)/provider/team-members/page.tsx` | Content |
| `/provider/wallet` | `app/(tenant)/provider/wallet/page.tsx` | Content |
| `/reports` | `app/(tenant)/reports/page.tsx` | Content |
| `/reviews` | `app/(tenant)/reviews/page.tsx` | Content |
| `/service-areas` | `app/(tenant)/service-areas/page.tsx` | Content |
| `/service-jobs` | `app/(tenant)/service-jobs/page.tsx` | Content |
| `/service-jobs/[id]` | `app/(tenant)/service-jobs/[id]/page.tsx` | Content |
| `/service-jobs/[id]/execution` | `app/(tenant)/service-jobs/[id]/execution/page.tsx` | Content |
| `/service-jobs/[id]/quotes` | `app/(tenant)/service-jobs/[id]/quotes/page.tsx` | Content |
| `/services` | `app/(tenant)/services/page.tsx` | Content |
| `/settings` | `app/(tenant)/settings/page.tsx` | Content |
| `/settings/engines` | `app/(tenant)/settings/engines/page.tsx` | Content |
| `/setup/service-coverage` | `app/(tenant)/setup/service-coverage/page.tsx` | Content |
| `/staff` | `app/(tenant)/staff/page.tsx` | Content |
| `/staff/[id]` | `app/(tenant)/staff/[id]/page.tsx` | Content |
| `/tenant/setup/availability` | `app/(tenant)/tenant/setup/availability/page.tsx` | Content |
| `/tenant/setup/services` | `app/(tenant)/tenant/setup/services/page.tsx` | Content |
| `/users` | `app/(tenant)/users/page.tsx` | Content |
| `/wallet` | `app/(tenant)/wallet/page.tsx` | Content |

## Non-Tenant Routes (Auth / Staff)

| URL | File |
|---|---|
| `/` | `app/page.tsx` (redirect to `/dashboard` or `/login`) |
| `/login` | `app/login/page.tsx` |
| `/register` | `app/register/page.tsx` |
| `/onboarding` | `app/onboarding/page.tsx` |
| `/forgot-password` | `app/forgot-password/page.tsx` |
| `/change-password` | `app/change-password/page.tsx` |
| `/change-password-required` | `app/change-password-required/page.tsx` |
| `/staff/*` | `app/staff/*/page.tsx` (Staff sub-portal) |

## Summary

- **Total tenant routes:** 80 (content-rendering)
- **Total non-tenant routes:** 21
- **Route groups:** `(tenant)` for all authenticated tenant owner pages
- **Dynamic segments:** `/bookings/[id]`, `/customers/[id]`, `/jobs/[id]`, `/service-jobs/[id]`, `/service-jobs/[id]/execution`, `/service-jobs/[id]/quotes`, `/staff/[id]`, `/provider/compliance/requests/[id]`, `/account/privacy/requests/[id]`

**Status: PASS** — All routes are file-based; no orphaned route files detected.
