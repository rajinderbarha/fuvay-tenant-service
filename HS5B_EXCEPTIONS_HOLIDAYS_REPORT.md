# HS5B — Exceptions/Holidays Report

## Schema
New table `tenant_availability_exceptions` (migration 121) — real, all
ticket-required fields present.

## API — full CRUD, live-verified
- `GET /v1/provider/availability/exceptions` — lists active exceptions.
- `POST /v1/provider/availability/exceptions` — create, validates date
  required, reason required, and (for partial-day) start/end time
  required with `end > start`.
- `PUT /v1/provider/availability/exceptions/{id}` — update, re-validates
  the merged record.
- `DELETE /v1/provider/availability/exceptions/{id}` — soft delete
  (`status='deleted'`), history preserved.

## Real bug found and fixed mid-sprint
Initial implementation passed the `date` field as a bare ISO string to
an asyncpg-bound `date` column, causing a live `500 INTERNAL_ERROR`
(`'str' object has no attribute 'toordinal'`). Fixed with a
`_parse_date()` helper that accepts both an ISO string and an
already-parsed `datetime.date` (needed because the same value can come
from either a fresh payload or a re-read DB row during update). Both
paths re-tested live after the fix — full-day and partial-day exception
creation both succeeded.

## Live verification
- Full-day holiday (`{"date":"2026-08-15","reason":"Independence Day","full_day_closed":true}`)
  → 201, created correctly.
- Partial-day exception (`{"date":"2026-08-20", start:"09:00", end:"13:00"}`)
  → 201, created correctly.
- Invalid time range (`start:"15:00", end:"09:00"`) →
  `422 INVALID_EXCEPTION_TIME_RANGE`, exact ticket-required message,
  `request_id` present.

## No dedicated frontend UI built this sprint
Same as break/lunch — the "Exceptions/Holidays" UI section (Add/Edit/
Delete Exception) was not added to the availability page this sprint.

## Verdict
Exceptions/holidays: **schema + full CRUD API real, live-verified,
including a genuine bug found and fixed**. Frontend UI: **not built**.
