# HS5 — Tenant Availability Report

## Real route
`/provider/availability` (1953 lines, real, substantial page — weekly
schedule UI confirmed present via `day_of_week`/schedule-related
content).

## Real bug found and fixed this sprint
`create_availability`/`update_availability`
(`app/engines/provider_portal/router.py`) had **zero time-range
validation** — an availability rule could be created or updated with
`end_time` before `start_time` (e.g., "18:00–09:00"), silently accepted
and stored. Fixed:
```python
def _validate_availability_time_range(start_time, end_time):
    if end_time <= start_time:
        raise ServiceOSException("INVALID_AVAILABILITY_TIME_RANGE",
            "End time must be after start time.", status_code=422)
```
Wired into both create (always validates) and update (fetches existing
row's times when only one of start/end is being changed, so a partial
update can't slip an invalid combination past the check).

## Live-verified
```
POST /v1/provider/availability {day_of_week:1, start_time:"18:00", end_time:"09:00"}
→ 422 INVALID_AVAILABILITY_TIME_RANGE, "End time must be after start time.", request_id present

POST /v1/provider/availability {day_of_week:1, start_time:"09:00", end_time:"18:00"}
→ 200, created successfully
```

## Not implemented (real, honest gaps)
- **No break/lunch fields exist on `provider_availability_rules`** —
  the table has `day_of_week`/`start_time`/`end_time`/
  `slot_duration_minutes`/`max_bookings_per_slot` only. The ticket's
  "Break Start/Break End" fields would require a schema migration — not
  done this sprint (no evidence of demand/existing UI for it beyond the
  ticket's own spec).
- **No exceptions/holidays table or endpoints found** — the ticket's
  "Exceptions/Holidays" section (date-specific closures) has no backing
  data model in this codebase today.
- **No booking-window settings** (minimum notice, advance-booking days,
  buffer time) found as a distinct configurable entity — `slot_duration_
  minutes` exists per-rule but the other booking-window concepts from
  the ticket aren't modeled.

## Verdict
Availability: **real page exists**, one real backend validation bug
found and fixed (live-verified). Break/holiday/booking-window features
from the ticket's spec don't exist in this codebase — documented as
gaps requiring new schema, not silently claimed as done.
