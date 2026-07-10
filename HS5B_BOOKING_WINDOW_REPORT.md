# HS5B — Booking Window Report

## Schema
New table `tenant_booking_window_settings` (migration 121), one row per
tenant, all 7 ticket fields with the ticket's exact suggested defaults.

## API — live-verified
- `GET /v1/provider/booking-window` — returns the tenant's row, or the
  documented safe defaults if no row exists yet (never a 404/error for
  a not-yet-configured tenant).
- `PUT /v1/provider/booking-window` — upsert (create-or-update),
  validates every field per the ticket's rules.

## Validation — all 4 rules live-verified
- `minimum_notice_minutes >= 0`
- `maximum_advance_booking_days >= 1`
- `slot_duration_minutes > 0` — live-verified: `{slot_duration_minutes:
  0}` correctly rejected with `422 INVALID_SLOT_DURATION`.
- `buffer_minutes_between_jobs >= 0`

Save with the ticket's exact default values
(`{120, 7, 60, 30}`) live-verified: `200`, all fields persisted
correctly.

## No "emergency booking can only be enabled if policy allows" check
The ticket mentions this rule but doesn't specify what the policy gate
actually is — no such policy flag exists elsewhere in the codebase.
`emergency_booking_allowed` is accepted as a plain boolean tenant
preference; documented as an open question rather than a fabricated
policy check.

## No dedicated frontend UI built this sprint
The "Booking Rules" UI section was not added to the availability page
this sprint.

## Verdict
Booking window: **schema + API + validation real, live-verified**.
Frontend UI: **not built**.
