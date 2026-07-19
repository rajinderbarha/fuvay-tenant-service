# Design Governance Rules (UX-04B)

Same rules as UX-04/04A, re-verified: no raw hex colors in any new UX-04B
component (grep-confirmed); no new status registry; canonical roles only
(`staff-home`, `FieldOpsJobDetail`, `PartsRequestList` all grep-confirmed
free of `dispatcher`/`manager`/`tenant_manager`); pipeline separation
enforced at the type level AND now test-enforced
(`provenance.test.ts`); PartsRequest ServiceJob-only and no technician
install authority re-asserted as executable tests in both
`PartsRequestSummary.test.tsx` (UX-04A) and `PartsRequestList.test.tsx`
(new, UX-04B). One new rule this pass: a real, found accessibility issue
is never silently dropped from a test suite — it is either fixed, or
explicitly excluded with an inline comment and a cross-referenced doc
explaining why (see `keyboard-a11y.spec.ts`'s `KNOWN_EXCLUDED_RULES`).
