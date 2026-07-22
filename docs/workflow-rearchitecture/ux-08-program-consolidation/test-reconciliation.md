# Test Reconciliation (UX-08)

Fresh, independently-run this pass (not cited from docs):

| App | Install | Typecheck | Tests | Method |
|---|---|---|---|---|
| Customer app | fresh WSL npm install --legacy-peer-deps | 0 errors | 76/76 | genuinely fresh install, matches UX-07 closure exactly |
| Super Admin | fresh WSL workspace npm install (root + design-system + super-admin) | not separately re-run this pass (0 errors at UX-07 Round 4 Pass 1 closure) | 13/13 | genuinely fresh install + `npx vitest run` |

Cited from prior UX-phase closures (not re-run this pass, given time
constraints and since no code changed in those apps during UX-07/UX-08):

| App | Tests | Source |
|---|---|---|
| Tenant Portal | passing (UX-04 closure: 53/53 unit + 87/87 Playwright) | UX-04 approval-gate docs |
| Staff/Technician app | 56/56 | UX-05 closure docs |
| Shared design-system | not independently re-run this pass | consumed by Super Admin/Tenant Portal builds, which were verified |

## Known baseline conditions (not regressions)

- ThemeContext test stability fix (UX-07 Pass 3c) remains in place —
  proven with 25/25 + 10/10 + 5/5 repeated runs at the time; not
  re-run to that full depth this pass, but the full customer suite
  (which includes `ThemeContext.test.tsx`) passed cleanly in this pass's
  fresh install (76/76), which is consistent with no regression.
- No skips, retries, or timeout inflation were used in any test run this
  pass.

## Environment blockers encountered this pass

None for the test/typecheck reconciliation itself — both customer-app and
super-admin fresh installs and test runs completed successfully in WSL.
(A live-backend-reachability blocker from UX-07 Pass 3f, affecting only the
authenticated Playwright visual sweep, is carried forward as a known
limitation — not re-attempted in this consolidation pass, since UX-08's
scope is reconciliation, not new visual-evidence capture.)
