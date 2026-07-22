# Alternate Cancellation Route Audit — Slice 2F-12A (Workstream 10)

## Search
Repository-wide grep for CoachingAppointment cancellation capabilities
across `execution.coaching_router`, `app.engines.coaching_appointment`,
customer/provider/admin routers, scheduling/booking engines, and
background tasks.

## Findings

| Route | Model/table | Capability | Persona | Reaches CoachingAppointment? | Classification |
|---|---|---|---|---|---|
| `POST /v1/provider/coaching-appointments/{id}/cancel` (this router) | `CoachingAppointment` | provider operational cancel | owner/staff (technician/customer denied) | YES | PROVIDER_OPERATIONAL_CANCEL — canonical, now verified business-wide |
| `POST /v1/customer/real-estate/... ` / `coaching_appointment.customer_router` `cancel_draft` | `CoachingAppointmentDraft` (distinct model) | customer cancels their own pre-confirmation DRAFT | customer (own draft, `customer_id`-filtered) | NO — operates on `CoachingAppointmentDraft`, not the confirmed `CoachingAppointment` | CUSTOMER_SELF_SERVICE_CANCEL / DISTINCT_MODEL_DISTINCT_CAPABILITY |
| `admin_router` (this module) | `CoachingAppointment` | GET execution-timeline only | super_admin | read-only, no cancel | n/a (no cancel capability) |
| Background draft expiry (`coaching_appointment` service `expires_at` handling) | `CoachingAppointmentDraft` | auto-expire stale drafts | system/worker | NO — drafts only | DISCONNECTED (distinct model, not the confirmed appointment) |

## No weaker alternate route reaching the same record
The only route that cancels a confirmed `CoachingAppointment` is
`provider_cancel` (this router), now fully verified. `cancel_draft`
reaches a different model (`CoachingAppointmentDraft`) via a different,
customer-owned filter — it cannot cancel a confirmed appointment and is
not a weaker path to the same record. No booking/scheduling/generic
cancellation service was found reaching `CoachingAppointment`.

## Disposition
**ALTERNATE_ROUTE_CLOSED** — no weaker live route reaches the same
`CoachingAppointment` cancellation capability. `coaching_appointment`'s
draft cancellation is `DISTINCT_MODEL_DISTINCT_CAPABILITY` /
`REQUIRES_FUTURE_DEDICATED_SLICE` if that module is ever independently
hardened (out of scope here).
