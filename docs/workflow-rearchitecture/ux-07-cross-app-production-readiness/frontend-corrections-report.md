# Frontend-Owned Corrections — Round 2 (Workstream 12)

## Correction made

**`frontend/tenant-portal/package.json`**: added
`"@testing-library/dom": "^10.4.0"` as an explicit devDependency.

- **Why this qualifies as frontend-owned, not a backend/contract issue**:
  `@testing-library/react@^16.0.1` (already pinned in this same
  `package.json`) requires `@testing-library/dom` as a peer dependency —
  the package itself declares this requirement. It was simply never added
  as an explicit dependency in `tenant-portal`'s own `package.json`, so npm
  never installed it. This is exactly the class of defect the brief
  authorizes fixing: "missing loading state" -> here, a missing test
  dependency that the code (test files) already assumed was present.
- **Not a version upgrade, not `--force`, not `legacy-peer-deps` misuse**:
  the added version (`^10.4.0`) is the exact peer version
  `@testing-library/react@16` itself specifies; nothing else was upgraded.
- **Verified impact**: before the fix, 12/16 tenant-portal test files
  failed outright (`Cannot find module '@testing-library/dom'`) and 13
  real `tsc --noEmit` errors existed purely because of the missing type
  exports this caused. After the fix: 0 typecheck errors, and 13/16 test
  files now run and pass (42 tests) — see
  `typecheck-build-test-baseline.md` for the full before/after breakdown.
  Re-run twice with identical results (see `repeated-test-stability.md`) —
  confirmed stable, not incidental.

## Correction considered but NOT made (documented reason)

**`frontend/tenant-portal/package.json`'s `react`/`react-dom` pin
(`19.2.7`) vs `frontend/super-admin`'s (`19.2.0`)**: this mismatch causes a
genuine duplicate-React-instance bug (`Invalid hook call`) in the 3
remaining failing test suites (`PartsRequestList`, `PartsRequestSummary`,
and others — see `typecheck-build-test-baseline.md`). This was NOT changed
this round because:
1. Both apps use the identical `next: 16.2.9`, so it's not obviously a
   required differing peer constraint — but I could not FULLY verify that
   downgrading tenant-portal to `19.2.0` (or upgrading super-admin to
   `19.2.7`) would not break either app's real Next.js production build
   within this round's remaining time budget.
2. The brief explicitly says not to "alter package versions merely to
   make one local environment pass" without full justification and
   verification — changing a pin without a follow-up `next build`
   verification on both apps would be exactly that.
3. This is precisely the same CLASS of incident already documented in this
   project's own memory (UX-05's react-test-renderer duplicate-instance
   incident) — the established, safe remediation pattern there was a
   full from-scratch-install verification cycle, which this round's time
   budget did not allow for this specific finding on top of everything
   else completed. Logged as a precise, actionable finding for a future
   round (`deferred-workstreams.md`) rather than a rushed, unverified pin
   change.

## No other frontend defects found/fixed this round

No wrong-endpoint, wrong-field-name, wrong-response-mapping, wrong-enum-
mapping, broken-navigation, lost-state-on-refresh, or unsafe-automatic-
selection defects were found in the code actually exercised this round
(the Round 1 E2E proof's endpoints, the Round 2 pricing-continuity
re-check, and the role-boundary checks) beyond what's documented above and
in `offering-type-contract-defect.md` (which is backend-owned, not
frontend-owned, and correctly NOT patched here).

## Round 4, Pass 1

Two files changed to fix the 3 previously-failing `frontend/super-admin`
vitest tests (full root-cause analysis in
`super-admin-test-failure-analysis.md`):

1. **`frontend/super-admin/test-setup.ts`** — added a minimal
   `ResizeObserver` mock (`observe`/`unobserve`/`disconnect` no-ops),
   guarded by `typeof globalThis.ResizeObserver === "undefined"`. jsdom
   does not implement `ResizeObserver`; recharts' `<ResponsiveContainer>`
   (used by `RoleDashboard`'s finance/risk widgets) calls it
   unconditionally on mount, which threw `ReferenceError:
   ResizeObserver is not defined` in both `RoleDashboard` tests. This is a
   test-environment gap, not a source defect — the mock only affects the
   `vitest`/jsdom test run, never the real browser (which always has a
   native `ResizeObserver`).
2. **`frontend/super-admin/__tests__/ux02/patterns.test.tsx`** — changed
   `fireEvent.click(screen.getByText("Section B"))` to
   `fireEvent.click(screen.getByRole("button", { name: "Section B" }))`
   in the `EnterpriseDetailPage` "switches sections via the nav buttons"
   test. `EnterpriseDetailPage` intentionally renders each section label
   twice — once in a desktop `<nav><button>` and once in a mobile
   `<select><option>` — toggled visually via a CSS `@media` query that
   jsdom does not evaluate, so both were simultaneously present in the
   test DOM and `getByText` (which matches by visible text content across
   any element) was ambiguous. Scoping to `getByRole("button", ...)`
   selects only the real, always-intended desktop nav button; the
   `<option>` isn't a button so it's excluded. This is a test-query bug,
   not a defect in `EnterpriseDetailPage.tsx` (source file was not
   changed).

No source component files were changed — both fixes are confined to test
infrastructure/test code. See `super-admin-test-report.md` for before/after
pass rates and `repeated-test-stability.md` for the 3-consecutive-run
stability check.

### Live-access verification note (Workstream 4)

No frontend source files needed changes to get login/dashboard/tenants/
pricing/packages/logout working live against the running backend — see
`super-admin-live-access.md`. One environment-specific finding worth
recording: the app's own onboarding/product "tour" overlay
(`useTour()` in `components/layout/AdminLayout.tsx`) renders a full-screen
`position: fixed` backdrop (`z-index: 498`) on first dashboard load that
intercepts pointer events on other chrome (including the header's "Log
out" button) until "Skip tour" (or completing the tour) is clicked. This
is expected onboarding-tour behavior, not a defect, and was handled in
verification by clicking "Skip tour" first — flagged here only so a future
round doesn't mistake it for a broken logout button if it's encountered
via a partial-interaction test.
