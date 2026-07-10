# E2E-09 Service Setup Routes Report

## Routes Found

| Route | File | API Used | Notes |
|-------|------|----------|-------|
| `/provider/service-setup` | `app/(tenant)/provider/service-setup/page.tsx` | `providerOfferingsApi`, `myStatusApi`, `offeringCoverageApi`, `providerBrandApi`, `providerServiceOptionApi`, `offeringPricingApi`, `providerServiceAreasApi`, `providerTeamMembersApi`, `providerAvailabilityApi`, `customerServiceDiagnosticsApi` | Deprecated — shows banner redirecting to `/tenant/setup/services` |
| `/provider/service-coverage` | `app/(tenant)/provider/service-coverage/page.tsx` | `homeServicesSetupApi`, `offeringCoverageApi`, `providerBrandApi`, `providerStatusApi`, `myStatusApi` | Main service coverage page |
| `/tenant/setup/services` | `app/(tenant)/tenant/setup/services/page.tsx` | `homeServicesSetupApi`, `providerServiceAreasApi`, `providerStatusApi` | Primary Home Services setup wizard (5-step) |
| `/setup/service-coverage` | `app/(tenant)/setup/service-coverage/page.tsx` | (not checked — older redirect) | |
| `/provider/services` | `app/(tenant)/provider/services/page.tsx` | (listing page) | |

## Summary

- **Primary setup wizard**: `/tenant/setup/services` — 5-step: Overview → Types → Pricing → Brands → Review
- **Coverage page**: `/provider/service-coverage` — Service cards grid + active services table + slide-over config panel
- **Old setup page**: `/provider/service-setup` — deprecated, shows banner redirect to `/tenant/setup/services`
