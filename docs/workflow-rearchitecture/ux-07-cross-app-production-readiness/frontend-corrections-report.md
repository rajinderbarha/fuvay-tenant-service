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
