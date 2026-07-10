# Tenant Business Hours — API Mapping Report

## Spec vs Actual

| Spec Route | Actual Route Used | Notes |
|---|---|---|
| GET /v1/tenant/home-services/availability | GET /v1/provider/availability | providerAvailabilityApi.list() |
| PUT /v1/tenant/home-services/availability | — | Not needed; rule-level updates used |
| POST /v1/tenant/home-services/availability/rules | POST /v1/provider/availability | providerAvailabilityApi.create() |
| PUT /v1/tenant/home-services/availability/rules/{id} | PUT /v1/provider/availability/{id} | providerAvailabilityApi.update() |
| DELETE /v1/tenant/home-services/availability/rules/{id} | DELETE /v1/provider/availability/{id} | providerAvailabilityApi.delete() |
| GET /v1/tenant/home-services/availability/exceptions | Not available | Holidays stored locally (frontend-only) |
| POST /v1/tenant/home-services/availability/exceptions | Not available | Holiday backend endpoint not implemented |
| POST /v1/tenant/home-services/availability/slot-preview | Not available | Slots generated client-side via generateSlots() |
| GET /v1/tenant/home-services/readiness | GET /v1/provider/status | providerStatusApi.get() |
| GET /v1/tenant/setup/checklist | GET /v1/tenant/setup/activity | tenantSetupApi.getActivity(1) |

## Preset Endpoints
| Route | Status |
|---|---|
| POST /v1/provider/availability/preset/{key} | ✅ Implemented (idempotent apply) |
| DELETE /v1/provider/availability/preset/{key} | ✅ Implemented (bulk delete) |

Both have client-side fallback if backend endpoint is not yet live.

## Slot Preview
Slots are generated client-side using:
```
generateSlots(start_time, end_time, slot_duration_minutes)
```
No `/slot-preview` backend endpoint exists. Client-side generation is accurate for the configured rules.

## Holiday Exceptions
- Backend endpoint for holiday exceptions is **not implemented**.
- Holidays are stored in React state only (lost on page refresh).
- A warning banner is shown to the user.
- Documented in TENANT_BUSINESS_HOURS_REMAINING_BLOCKERS.md.
