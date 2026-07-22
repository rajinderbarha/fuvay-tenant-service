# Test Report — Slice 2F-6B

## Frontend tests (new)
`frontend/tenant-portal/lib/api.persona.test.ts` — 13 direct unit tests
for the 2 new helper functions (`canManageProviderInvoices`,
`canIssueProviderInvoice`) and their `isCanonicalStaffRole` building
block, covering every persona in the approved matrix (tenant_owner,
staff, technician, customer, guest, read-only access scope, unknown
role).

Run via: `npx tsc lib/api.ts lib/api.persona.test.ts --module commonjs
--target es2020 --outDir <tmp> --skipLibCheck --esModuleInterop && node
--test <tmp>/api.persona.test.js`
Result: **13 passed**, 0 failed.

(`npx tsx --test` — the natural on-the-fly TS runner — failed
repeatedly in this environment due to an npm cache-cleanup permission
error unrelated to this code; the tsc-compile-then-`node --test`
sequence above is the verified working equivalent, using only tools
already available in this repository, no new dependency installed.)

## Frontend type checking
`npx tsc --noEmit -p tsconfig.json` — 0 errors attributable to
`lib/api.ts` (the only file changed). Full command output filtered for
the changed file; project-wide pre-existing errors (if any, in
unrelated files) were not evaluated as part of this slice's scope.

## Frontend linting
`npx next lint` could not be executed in this environment (the `next`
CLI's argument parsing produced an "Invalid project directory" error
unrelated to this change — a pre-existing environment/tooling issue, not
something this slice introduced or could resolve within its narrow
scope). `eslint` was also attempted directly but this project has no
`eslint.config.js` (v9 format) or legacy `.eslintrc` file, so a fresh
run cannot lint against project rules without first authoring a config
— out of scope for this slice. Documented as a known limitation rather
than silently skipped.

## Backend regression (unchanged, re-run for confirmation)
- `python -m pytest tests/test_phase2f6_invoice_payment_provider_authorization.py tests/test_phase2f6a_invoice_payment_integrity.py -q`
  → **68 passed**, 0 failed.
- Module verification: `total_routes: 4`, `unverified_count: 0`, exit 0.

## Relevant permission/access-scope tests
`python -m pytest tests/test_phase2d_tenant_access_model.py tests/test_phase2e_effective_permissions.py -q`
→ **27 passed**, 0 failed (these are the same "living count" guardrail
tests corrected in Slice 2F-6 — re-confirmed still green, no backend
file touched this slice).

## Totals (frontend and backend reported separately, per instruction)
- Frontend: 13 passed, 0 failed (new suite only — no existing frontend
  test suite exists in this app to re-run).
- Backend: 68 (2F-6/2F-6A) + 27 (permission/access-scope) = **95 passed**, 0 failed.

## Not run
The broader repository-wide backend partition (`phase2f`/`invoice`/
`payment`/`sprint23`/etc., ~1165 tests in Slice 2F-6A's own report) was
not re-run in full this slice, since no backend file was modified and
Slice 2F-6A already proved that partition green immediately prior to
this slice. Re-running the narrower, directly-relevant subset (above)
is sufficient evidence that nothing regressed.
