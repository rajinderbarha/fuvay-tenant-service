# Frontend Test Plan (planned; largely NOT executed this pass — see report)

Per the brief, a UX-04 suite should cover:

- **Domain identity preservation**: a booking row's `pipeline` is always
  `"booking_field_ops"` and a job row's is always
  `"service_booking_service_job"`; no view model ever accepts the other
  fixture type (type-level, could be asserted at runtime by a test that
  imports both fixture arrays and checks `.pipeline` on every row).
- **Authorization presentation**: `PartsRequestSummary` renders Approve/
  Reject only when `actions` contains an available `approve` entry;
  otherwise renders the reason string, never a disabled button masquerading
  as available.
- **Workflow behavior**: `ChecklistProgress` in `customer_summary` mode
  never renders an item where `customerVisible === false`, and never
  renders `technicianNote`/`reviewerNote` in that mode.
- **SLA states**: `SLAIndicator` renders the correct color/label pairing
  for all 9 `SLAState` values.
- **UI behavior**: components render without throwing given each fixture;
  no raw hex color literals in any `components/ux04/*` file (grep-based
  check).

No `vitest`/`jest` config exists for `frontend/tenant-portal` (checked
`package.json` — only `next lint`/`next build`/`dev`/`start` scripts are
defined, no test runner script). UX-03 has `__tests__` directories with
`.test.tsx` files but they were reported failing to type-check even
before this phase's build fix pass (see `build-report.md`) due to missing
jest-dom type augmentation — meaning even UX-03's existing test files were
never confirmed running, only present as source.
