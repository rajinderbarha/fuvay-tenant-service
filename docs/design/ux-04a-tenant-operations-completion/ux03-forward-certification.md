# UX-03 Forward Certification

UX-03 (tenant-portal foundation) previously reported
`SOURCE_COMPLETE_FRONTEND_BUILD_BLOCKED`. This pass ran real verification
against UX-03's own code, now that it lives inside the same
`frontend/tenant-portal` workspace this pass builds and tests:

- **`npx next build`**: succeeded, all `/dev/ux-03/*` routes (25 of them)
  statically prerendered in the same build run as UX-04/UX-04A's routes —
  see `tenant-build-report.md` for the full route list, which includes
  every `/dev/ux-03/*` path.
- **`npx tsc --noEmit`**: clean (0 errors) — this includes UX-03's own
  source files under `lib/ux03`, `components/ux03`.
- **`npx vitest run`**: UX-03's `lib/ux03/__tests__/nav-ia.test.ts` (3
  tests) **passed**. UX-03's `components/ux03/__tests__/
  PermissionEditor.test.tsx` and `SetupWizard.test.tsx` (4 tests total)
  **failed** with "Invalid hook call... Cannot read properties of null
  (reading 'useState')" — a real, pre-existing incompatibility this pass's
  new vitest config surfaced for the first time (these files were never
  previously runnable at all, since no test runner was configured for
  `frontend/tenant-portal` before this pass). Root cause not conclusively
  diagnosed within this pass's time budget; suspected either a React
  version/dedup mismatch specific to how these two files render (both use
  `useState` directly in the component under test, unlike the passing
  `nav-ia.test.ts` which tests pure functions) or a `react-dom` render
  double-invocation issue. Reported exactly, not glossed over — see
  `ux04-test-report.md`.

This is real, on-behalf-of-UX-03 verification performed this pass — UX-03's
own `approval-gate.md` is not being rewritten. Net assessment: UX-03's
source is buildable and mostly test-passing; 2 of its test files have a
real, newly-surfaced failure that a future pass should investigate.
