# Tenant Service Setup — API Mapping Report

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/tenant/context` | `useTenant()` (localStorage) |
| `GET /v1/tenant/catalog/available-services` | `GET /v1/provider/offerings/available` (`providerOfferingsApi.listAvailable`) — real, fixed in the My Offerings sprint |
| `GET /v1/tenant/services` | `GET /v1/provider/offerings/enabled` (`providerOfferingsApi.listEnabled`) |
| `POST/PUT .../services/{id}` | `providerOfferingsApi.enable` / `.update` |
| `.../enable` / `.../disable` | `providerOfferingsApi.activate` / `.deactivate` |
| Service Type coverage | `GET /v1/admin/master-services/{id}/types` (`offeringCoverageApi.getTypes`) |
| Brand coverage | `GET /v1/provider/brands/services/{id}/available` (`providerBrandApi.getAvailableForService`) |
| Issue types | `GET /v1/customer/catalog/issue-types?service_id=` (`customerServiceDiagnosticsApi.getIssueTypes`) — **was live-500ing, fixed this sprint** |
| Service options | `GET /v1/customer/catalog/service-options?service_id=` and `GET /v1/provider/setup/services/{id}/available-options` (`providerServiceOptionApi.getAvailableForService`) — **both were live-500ing, fixed this sprint** |
| `GET /v1/tenant/service-areas` | `myStatusApi.getServiceAreas` / `providerServiceAreasApi.list` |
| `GET /v1/tenant/staff` | `myStatusApi.getTeamMembers` / `providerTeamMembersApi.list` |
| `POST /v1/tenant/pricing/platform-preview` | `POST /v1/pricing/tenants/{id}/price-preview` (`offeringPricingApi.preview`) |
| `POST /v1/tenant/availability/preview-slots` | `myStatusApi.getAvailability` / `providerAvailabilityApi.list` (existence check, not a slot-preview computation — no such endpoint exists) |
| `GET /v1/tenant/setup/checklist` | Computed client-side from the same real data sources (type/brand/area/technician/availability presence) — no dedicated checklist endpoint exists, consistent with the My Status sprint's approach |
| `GET /v1/tenant/activity` | `myStatusApi.getAuditLog` (`GET /v1/tenants/{id}/audit-log`) |

## Summary

This page (and its 10-step wizard) already existed in the codebase, built on
top of the real API surface established across the My Status, My Offerings,
and Bargain Module sprints. This sprint's work was verification + bug-fixing,
not a rewrite — see `TENANT_SERVICE_SETUP_BUG_FIX_REPORT.md`.
