# Coverage and availability repair — 2026-09-08

## Findings and changes

- Time inputs previously sent a network mutation on every change while displaying the saved server value. They now use a local draft, including empty/partial edits, with explicit Save, Discard and unsaved-change feedback.
- Save draft previously reloaded data. Both onboarding and operational Coverage & hours now save all seven days plus booking controls in a single transaction through `PUT /v1/provider/availability/schedule`. Owner authorization and onboarding prerequisites remain enforced.
- Partial booking-control updates previously reset unrelated settings to defaults. Updates now merge with stored values.
- Reopening a closed day retains hours, breaks and daily limit. Historical duplicate rules are deactivated, not deleted; staff views prefer the active canonical rule.
- Added labeled opening/closing times, optional breaks, per-day limits, draft capacity chips and a responsive save bar. Monday copy includes breaks and limits, without intermediate server writes.
- Two-hour job windows consistently include travel buffer in both tenant previews and the shared customer slot engine. Limits cannot exceed funded technician capacity. Live capacity additionally requires verified technician documents.
- Holiday input rejects past dates and duplicate dates in the displayed list. Full-day closures win over other exceptions on the same date.

## Verification

- Tenant TypeScript typecheck passed.
- Full tenant frontend suite: 105 tests passed, including nine new schedule/editor tests.
- Targeted Python suites: 45 tests passed (`test_business_schedule.py`, `test_onboarding_team_coverage_finance_regressions.py`, `test_hs5b_availability_exceptions_coverage.py`).
- Opt-in local PostgreSQL integration (`RUN_LOCAL_SCHEDULE_DB_TEST=1`) tested partial-update preservation, close/reopen identity, duplicate prevention, invalid-save rollback, saved break/buffer slot mapping, daily capacity distribution, occupied-place deduction, and full-day holiday precedence. All fixture writes were rolled back; seat/readiness and booking counts were controlled test inputs.
- Browser inspection of the existing public page confirmed the original controls and layout. Before screenshot: `artifacts/coverage-availability/01-before.png` (local, ignored artifact).
- The updated localhost page redirects to login; an authenticated browser verification of the revised layout and a live-server save are still pending. No deployment or Git push was performed for this repair.

## Deployment check

Deploy backend and tenant frontend together (new atomic endpoint); no migration required. Log in as a provider, edit times and a break, Save, refresh, then verify technician hours and customer slot counts. Check mobile width and a holiday date. Existing bookings are not cancelled by schedule edits.
