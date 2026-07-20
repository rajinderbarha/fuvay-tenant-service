# Unit / Component Test Report

Round 2 update: re-run fresh, full-suite (`npx jest`, no path scoping) in WSL after all navigation/screen/
component/showcase additions:

```
PASS src/lib/ux05/__tests__/checklist.test.ts
PASS src/lib/ux05/__tests__/myWork.test.ts
PASS src/types/__tests__/provenance.test.ts
PASS src/lib/ux05/__tests__/permissions.test.ts
PASS src/components/ux05/__tests__/PipelineBadge.test.tsx

Test Suites: 5 passed, 5 total
Tests:       30 passed, 30 total
```

Round 1 (for reference): `npx jest src/lib/ux05 src/types/__tests__` — 2 suites, 12/12 passing.

## New this round (18 additional tests, real behavioral assertions)
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
`JobNoteComposer`, `MediaCaptureGrid`, or any full screen (e.g. rendering `ScheduleScreen`/
`InspectionChecklistShowcaseScreen` end-to-end with navigation/context providers mocked). `PipelineBadge`/
`PermissionRestrictedState` prove the RNTL render path itself works; extending render-test coverage to the rest
of the component set is listed in `deferred-items.md`.
