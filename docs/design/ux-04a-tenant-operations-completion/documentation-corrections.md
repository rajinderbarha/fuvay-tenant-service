# Documentation Corrections (UX-04A)

No new source code fix outside `frontend/tenant-portal`'s primary scope
was required this pass (unlike UX-04 baseline, which needed 2 fixes
touching `frontend/packages/design-system` and a UX-03 file). This pass's
only "infrastructure" addition — vitest config, tsconfig types,
package.json devDependencies — is squarely within
`frontend/tenant-portal`, the primary scope, and is additive (adds test
capability) rather than corrective. See `prerequisite-bug-fix-report.md`
confirming the 2 baseline fixes are unchanged.

One correction to UX-04 baseline's own `original-scope-reconciliation`
framing: this pass's fuller reconciliation (`original-scope-reconciliation.csv`)
found that items 10 (Inspection) and 16 (Invoice) — labeled at UX-04
baseline as "type/fixture ready, no route" — were closer to done than
baseline's own docs suggested; both were completed in under an hour this
pass once identified, indicating baseline's time-budget triage was
conservative rather than the gaps being genuinely hard.
