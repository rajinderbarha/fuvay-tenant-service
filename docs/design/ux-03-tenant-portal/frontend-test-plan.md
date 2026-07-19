# Frontend Test Plan

Tests written this phase (Mode B — written, not executed; see
frontend-test-report.md):

- `lib/ux03/__tests__/nav-ia.test.ts` — canonical role enforcement, forbidden
  role-name absence, unique nav item ids.
- `lib/ux03/__tests__/permissions-and-pipelines.test.ts` — StaffPermission
  explicit-deny precedence, denied_override vs not_granted distinction,
  booking/job pipeline tagging, unsupported-cancellation-action absence,
  ServiceJob-only PartsRequest referential integrity, no premature
  technician-install decision, package/deposit field separation.
- `components/ux03/__tests__/SetupWizard.test.tsx` — progress indicator
  text, goNext/onSaveDraft wiring, blocked-step disabling.
- `components/ux03/__tests__/PermissionEditor.test.tsx` — denied vs
  not-granted label distinction, search input presence.

## Still to write (deferred — see deferred-items.md)

- Dashboard pre-approval/approved state-switching test.
- Team filter/search behavior test beyond PermissionEditor.
- Pricing below-platform-minimum validation test.
- Media secret-redaction test (asserting no signed-URL-shaped string ever
  renders).
- Light/dark rendering snapshot, keyboard-navigation, and long-localized-text
  tests for the shared patterns.

## Commands to run once npm install works

```
npm --workspace frontend/tenant-portal run test
npm --workspace frontend/packages/design-system run test
```
