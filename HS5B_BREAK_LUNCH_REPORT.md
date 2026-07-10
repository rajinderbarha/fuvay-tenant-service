# HS5B — Break/Lunch Time Report

## Schema
`provider_availability_rules.break_start_time`/`break_end_time`
(migration 121) — real columns, applied.

## Validation (`_validate_break_time`, live-verified)
- Both-or-neither: if only one of break_start/break_end is set, rejects
  with `INVALID_BREAK_TIME_RANGE`.
- `break_end > break_start` required.
- Break must fall inside `[start_time, end_time]` — confirmed live:
  a 20:00–21:00 break on a 09:00–19:00 day was correctly rejected
  ("Break time must be inside working hours.").
- A valid 14:00–15:00 break inside a 09:00–19:00 day was correctly
  accepted (live-verified, real DB row created).

## Wired into both create and update
Both `POST /v1/provider/availability` and `PUT /v1/provider/availability/
{id}` validate break time — update correctly merges partial payloads
with the existing row's start/end/break values before validating, so a
partial update can't slip an invalid combination past the check.

## No dedicated frontend UI built this sprint
The ticket's UI fields ("Break Enabled" toggle, Break Start/Break End
inputs per day) were **not added** to `/provider/availability`'s
1953-line page this sprint — backend implementation and live
verification consumed the sprint's time budget. The API is real and
ready to be wired into the existing weekly-schedule UI.

## Verdict
Break/lunch: **schema + validation + API real and live-verified**.
Frontend UI: **not built this sprint** — honest gap, not claimed done.
