# Tenant Availability — API Mapping Report

## Route
`/provider/availability` → `app/(tenant)/provider/availability/page.tsx`

## API Mapping

| Spec API | Actual API | Client | Status |
|---|---|---|---|
| GET /v1/tenant/availability/rules | GET /v1/provider/availability | providerAvailabilityApi.list() | ✅ Used |
| POST /v1/tenant/availability/rules | POST /v1/provider/availability | providerAvailabilityApi.create() | ✅ Used |
| PUT /v1/tenant/availability/rules/{id} | PUT /v1/provider/availability/{id} | providerAvailabilityApi.update() | ✅ Used |
| DELETE /v1/tenant/availability/rules/{id} | DELETE /v1/provider/availability/{id} | providerAvailabilityApi.delete() | ✅ Used |
| GET /v1/tenant/availability/exceptions | NOT IMPLEMENTED | — | ⚠ Frontend uses session-local state |
| POST /v1/tenant/availability/exceptions | NOT IMPLEMENTED | — | ⚠ Frontend uses session-local state |
| DELETE /v1/tenant/availability/exceptions/{id} | NOT IMPLEMENTED | — | ⚠ Frontend uses session-local state |
| POST /v1/tenant/availability/validate | NOT IMPLEMENTED | — | ⚠ Client-side validation used |
| POST /v1/tenant/availability/preview-slots | NOT IMPLEMENTED | — | ⚠ Client-side slot generation used |
| GET /v1/provider/status | GET /v1/provider/status | providerStatusApi.get() | ✅ Used (bookability) |
| GET /v1/provider/team-members | GET /v1/provider/team-members | providerTeamMembersApi.list() | ✅ Used (staff selector) |
| GET /v1/tenant/service-areas | GET /v1/tenant/service-areas | providerServiceAreasApi.list() | ✅ Used (area selector) |
| GET /v1/tenant/activity | GET /v1/provider/activity | tenantSetupApi.getActivity() | ✅ Used |

## Missing Backend Endpoints (documented as partial)

### 1. Slot Preview: `/v1/provider/availability/preview-slots`
- **Status**: Not implemented
- **Workaround**: Client-side slot generation using `generateSlots(start, end, duration)` function
- **Impact**: Preview is accurate for non-overlapping rules; does not account for server-side booking constraints

### 2. Validate Endpoint: `/v1/provider/availability/validate`
- **Status**: Not implemented
- **Workaround**: Client-side validation (`detectIssues()` function)
- **Impact**: Partial — detects invalid_time_range, slot_duration_out_of_bounds, max_bookings_invalid, scope_id_missing

### 3. Holiday Exceptions: `/v1/provider/availability/exceptions`
- **Status**: Not implemented
- **Workaround**: Session-local state (`holidays` array, not persisted to backend)
- **Impact**: Holidays reset on page refresh — backend endpoint required for persistence

## Rule Scope Types

| Backend value | Frontend label |
|---|---|
| provider | All Services |
| offering | Specific Service |
| staff_member | Staff Member |
| service_area | Service Area |

## Multi-day Creation
The backend stores one rule per `day_of_week`. When the tenant selects multiple days in the wizard, the page calls `POST /v1/provider/availability` once per selected day using `Promise.all()`.

## TypeScript: 0 new errors.
