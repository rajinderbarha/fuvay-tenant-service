# Unit / Component Test Report

Run for real in WSL: `npx jest src/lib/ux05 src/types/__tests__`

```
PASS src/lib/ux05/__tests__/permissions.test.ts
PASS src/types/__tests__/provenance.test.ts

Test Suites: 2 passed, 2 total
Tests:       12 passed, 12 total
```

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

## Not run this pass
No React Native Testing Library component-render tests were written (e.g. rendering `PartsRequestStatusCard`,
`PermissionRestrictedState`, `NextActionBar`, or the showcase screen) — only pure-function/type-level tests. This
is listed in `deferred-items.md`.
