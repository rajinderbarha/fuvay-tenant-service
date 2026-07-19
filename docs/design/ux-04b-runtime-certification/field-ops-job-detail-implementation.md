# field_ops.Job Detail Implementation

- Type: `FieldOpsJobDetailView` (`lib/ux04/types.ts`) — carries only
  `job` (`BookingFixture`), `sla`, `timeline`, `activity`, `notes`,
  `actions`. No field for quote/checklist/parts/invoice/credit exists on
  the type at all (not merely left null) — a structural guarantee.
- Component: `components/ux04/FieldOpsJobDetail.tsx`.
- Fixture: `fieldOpsJobDetailFixture` (`lib/ux04/fixtures.ts`).
- Route: `/dev/ux-04/field-ops-job-detail`.
- Test: `components/ux04/__tests__/FieldOpsJobDetail.test.tsx` — asserts
  the exact heading set rendered (`Notes`, `Timeline`, `Activity / Audit`)
  and that none of the forbidden ServiceJob-only headings appear.
- Browser verification: included in `browser-tests/smoke.spec.ts`'s route
  list and in the dedicated "never renders ServiceJob-only section
  headings" browser test — see `browser-smoke-test-report.csv`.
