# CUSTOMER-L5-13 — ETA and Route Contract

## No Real ETA or Route Capability Exists for This Pipeline

Exhaustively verified (own research + independent cross-check):

- The only ETA calculation anywhere in this codebase
  (`app/engines/geo/service.py`'s `eta_minutes = round(road_dist / 0.5, 0)`
  heuristic) exists solely to support a dispatch-radius "find nearby
  staff" search in the orphaned legacy stack — it is never computed for,
  or exposed to, a customer's specific assigned technician.
- No `mapbox`/`google maps`/directions-API integration exists anywhere in
  `app/`.
- A notification-template string
  (`app/engines/tenant_engine/provisioning.py`: `"{staff_name} is on the
  way. ETA: {eta} minutes."`) references an `{eta}` placeholder, but no
  real code anywhere computes a value to substitute into it — confirmed
  aspirational/unfulfilled, consistent with this project's repeatedly-observed
  "template exists, computation doesn't" pattern from prior sprints.

## Consequence

This sprint renders no ETA, no "expected arrival window," no distance,
and no route geometry anywhere. The `technician_on_the_way` /
`technician_reached_site` execution events (real, timestamped) are the
only real signal this sprint can honestly show — "Technician is on the
way" (a real, occurred fact) rather than "Technician arrives in ~15
minutes" (a fabricated prediction with no backend support).

## Customer-Safe Labels Actually Used

Per §28's own guidance for when no real ETA exists
("Arrival time unavailable"), this sprint's copy never implies a time
estimate — it states only real, already-occurred milestones
(`serviceTracking.event.onTheWay`: "Technician is on the way",
`serviceTracking.event.reachedSite`: "Technician has arrived") with a
real timestamp of when that event was recorded, never a predicted future
time.

## What Would Close This Gap (Not This Sprint's Scope)

A real backend change connecting the `geo` engine's real (if currently
orphaned and crude) ETA heuristic — or a proper directions-API
integration — to the actual `home_service_assignment`/`execution`
pipeline, plus a new customer-facing endpoint exposing it per-job. Neither
exists today.
