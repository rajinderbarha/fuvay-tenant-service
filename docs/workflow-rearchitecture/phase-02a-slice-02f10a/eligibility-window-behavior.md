# Eligibility Window Behavior — Slice 2F-10A (Workstream 5)

## Window definition
- **Start**: `record.created_at` (the linked booking/job/invoice/
  appointment/lead/review's own creation timestamp) — not the record's
  completion timestamp. This is the actual repository behavior; the
  mission's phrasing ("filing window") could be read as starting at
  completion, but the code uses `created_at` for every record type
  uniformly.
- **End**: `created_at + complaint_window_hours` (default 168h / 7 days,
  overridable per category or globally via `ComplaintPolicy`).
- **Timezone handling**: naive timestamps are defensively coerced to UTC
  (`created_at.replace(tzinfo=timezone.utc)`) before comparison against
  `datetime.now(timezone.utc)` — no naive/aware comparison crash risk.
- **Boundary**: strictly exclusive at the end (`if age > timedelta(hours=window_hours)`)
  — exactly at the boundary (`age == window_hours`) is still eligible.
- **Missing `created_at`**: the window check is skipped entirely
  (`if created_at:` guards the whole block) — a record with no creation
  timestamp is treated as having no window restriction, not rejected.

## Not present (confirmed absent)
- No warranty-specific window extension.
- No rework-triggered window reset.
- No administrator override path within `check_eligible` itself.

## Frontend
The customer-app never calls the `check-eligible` preflight endpoint at
all (see `frontend-preflight-alignment.md`), so there is no frontend
display of window results to compare against.

## Fix applied
The window was canonical (see `complaint-eligibility-contract.md`) but
bypassed entirely by direct `create_complaint` calls before this slice
(only the separate, un-consulted `check-eligible` endpoint evaluated it).
Now enforced via the same `check_eligible` call `create_complaint` uses
for every other rule — no separate, duplicate window-check code was
written; the existing service method is the single source of truth.
