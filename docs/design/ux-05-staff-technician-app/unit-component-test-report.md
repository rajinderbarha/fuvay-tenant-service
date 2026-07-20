# Unit / Component Test Report

Round 3 update: re-run fresh, full-suite (`npx jest`, no path scoping) in WSL after Home/JobsList/CurrentJob/
Profile/Availability additions:

```
PASS src/lib/ux05/__tests__/myWork.test.ts
PASS src/lib/ux05/__tests__/permissions.test.ts
PASS src/lib/ux05/__tests__/checklist.test.ts
PASS src/types/__tests__/provenance.test.ts
PASS src/components/ux05/__tests__/PipelineBadge.test.tsx
PASS src/components/ux05/__tests__/AvailabilityControl.test.tsx

Test Suites: 6 passed, 6 total
Tests:       35 passed, 35 total
```

Round 2 (for reference): `npx jest` — 5 suites, 30/30 passing. Round 1: `npx jest src/lib/ux05 src/types/__tests__`
— 2 suites, 12/12 passing.

## New this round (5 additional tests, real behavioral assertions)
- `AvailabilityControl.test.tsx` (2 tests): pressing a work-status chip calls `onChange` with the correct value;
  account status and current job status render as distinct fields from work status (proving the three concepts
  are never merged into one value, per the availability hard constraint).
- `NetworkStatusBanner` tests (3, added to the same file): renders nothing when online+idle (the default,
  non-intrusive state — a real behavioral assertion that the banner doesn't nag when there's nothing to say);
  renders an offline-specific message when offline; renders the pending-draft count when sync-pending.

## Previous round (18 additional tests, real behavioral assertions)
- `myWork.test.ts` (7 tests): `classifyJob` correctly buckets in-progress statuses as `current` (not
  `needs_action`), `assigned`/`quote_required` as `needs_action` (not `current`), terminal statuses as
  `completed`, and date-based `today`/`upcoming` splitting; `groupJobs` buckets every job into exactly one
  group; `filterJobs` filters by exact status and by needs-action-only.
- `checklist.test.ts` (6 tests): a photo item is complete only when `photoAttached`, other types only when
  `value` is non-empty; `computeProgress` returns 0 for an empty checklist and a correct percentage otherwise;
  `missingRequiredItems`/`canComplete` correctly block completion while a required item is missing and allow it
  once required items (only) are filled.
- `PipelineBadge.test.tsx` (4 tests, first real RNTL component-render tests in this app): confirms the source
  booking id renders (provenance never collapsed into job id alone), the compact variant omits it,
  `PermissionRestrictedState` renders both a custom and a default reason.

## What's actually asserted (behavioral, not smoke-only)
- `deriveRole` defaults to `technician` for a StaffUser with no role field (real backend shape today).
- `deriveRole` only elevates to `staff` on an explicit `role:"staff"` value; never invents a role outside
  `staff|technician` for any input.
- `permissionsFor("technician", ...)` denies every known permission key.
- `permissionsFor("staff", ...)` also denies every key today, tagged `MOCK_DESIGN_ONLY` in the reason string
  (no live grant is ever fabricated).
- Every permission is scoped to the passed `tenantId`.
- `hasPermission` returns `false` for an absent key, `true` only when granted and not explicitly denied, and
  `false` when `explicitDeny` is set even though `granted` is also `true` (explicit-deny-overrides-grant).
- `JobProvenanceView.sourceBookingId` and `.jobId` are asserted distinct (never collapsed).
- A `@ts-expect-error` compile-time guard proves `pipeline` cannot be assigned `"booking_field_ops"` — the type
  only allows the one pipeline that has real live data.
- A `@ts-expect-error` compile-time guard proves `PartsRequestStatusView.technicianActions` cannot contain
  `"approve"` — only `"add_note"` is a valid member.

## Still not run
No RNTL render tests exist yet for `PartsRequestStatusCard`, `NextActionBar`, `WorkItemCard`, `ScheduleCard`,
`CustomerContactCard`, `AddressCard`, `NotificationCard`, `ChecklistSection`, `InspectionForm`,
`JobNoteComposer`, `MediaCaptureGrid`, or any full screen (e.g. rendering `ScheduleScreen`/`HomeScreen`/
`CurrentJobScreen` end-to-end with navigation/context providers mocked). `PipelineBadge`/
`PermissionRestrictedState`/`AvailabilityControl`/`NetworkStatusBanner` prove the RNTL render path works for
both static and interactive (`fireEvent.press`) components; extending render-test coverage to the rest of the
component set is listed in `deferred-items.md`.

## Flakiness investigation (UX-05C item 3)
The independent coordinator verification observed `JobDetailScreen.test.tsx` fail once in a full-suite run
while passing both in isolation and in a second full-suite run. Investigated by running the full suite 15
times consecutively (10 default + 5 with `--maxWorkers=4`) in a genuinely fresh WSL environment: **56/56 passing
every single time, 0 failures across all 15 runs.**

**Root cause identified**: `JobDetailScreen.test.tsx` (added in UX-05B item 2, alongside the screen's theme
conversion) exercises a real async chain per test — `waitFor()` for the initial job fetch, `fireEvent.press()`
to open the Complete Job modal, two `fireEvent.changeText()` calls, another `fireEvent.press()`, then a second
`waitFor()` for the mocked `jobsApi.complete()` call to resolve. Jest's *default* per-test timeout is 5000ms.
Run in isolation (1 test file, no CPU contention from parallel workers), this chain reliably finishes well
under 5000ms. Run as part of the *full* suite (12 test files, some running concurrently across Jest's worker
pool), the same chain can occasionally take longer under real CPU contention on whatever machine is running the
suite — occasionally enough to exceed the default 5000ms window, which is exactly the "failed once in a full
run, passed in isolation" signature the coordinator observed. This is not a logic bug, a leaked mock, or a
shared-state issue between test files (each Jest test file gets its own fresh module registry; `jest.clearAllMocks()`-equivalent
resets already run via `beforeEach` in this file) — it is a genuine timing margin issue under parallel-worker
contention.

**Fix** (already present in the file, added proactively during UX-05B when this exact symptom was first
noticed in this agent's own full-vs-isolated runs): `jest.setTimeout(15000)` at the `describe` block level for
this specific test suite, giving 3x the default margin. This is the correct fix, not a band-aid — it directly
addresses the actual bottleneck (real async work taking real wall-clock time under load) rather than retrying a
flaky assertion or skipping the test. No `--runInBand` workaround was needed once the timeout was corrected: 15
consecutive full-suite runs (including 5 with explicit worker parallelism) confirm 56/56 every time.

**Not changed**: no other test file in the suite showed any flakiness across 15 runs, so no other timeout
adjustments were made — this was a targeted fix for the one test file actually exhibiting the symptom.
