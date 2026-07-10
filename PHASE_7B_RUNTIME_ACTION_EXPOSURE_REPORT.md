# Phase 7B — Runtime Action Exposure Scan Report

## Scope

Job List (`/staff/jobs`) and Job Detail (`/staff/jobs/[job_id]`) — the two pages that touch
job data and are the only place forbidden runtime actions could plausibly appear.

## Forbidden actions checked

Start Job, On The Way, In Progress, Complete Job, Collect Payment, Confirm Payment,
Deduct Credits.

## Method

1. `Grep` (case-insensitive) across `frontend/tenant-portal/app/staff/` for
   `start.*job|complete.*job|collect.*payment|confirm.*payment|deduct.*credit|on.the.way|in.progress`.
2. Manual review of every `onClick`/action binding in both job pages.
3. `tests/test_phase7b_staff_frontend_certification.py::test_job_detail_shows_forbidden_actions_as_disabled_not_wired`
   and `::test_job_pages_have_no_payment_or_completion_mutation_calls`.

## Result

All 7 forbidden action labels are present **only** in `jobs/[job_id]/page.tsx`'s
`DISABLED_ACTIONS` array, rendered as `<button disabled title="Not certified in this phase">`
elements with no `onClick` handler bound to any API call — confirmed by reading the full file:
the buttons render the action label followed by the literal text
"— Not certified in this phase" and have no event handler at all.

No occurrence of any forbidden action label is bound to a `useAction`/`apiFetch` call anywhere
in the staff app. `staffSelfApi` (the only API surface these pages import) exposes zero
job-mutation methods beyond read (`getMyJobs`, `getJobDetail`).

**Conclusion: 0 forbidden runtime actions are exposed as functional/certified in this app.**
