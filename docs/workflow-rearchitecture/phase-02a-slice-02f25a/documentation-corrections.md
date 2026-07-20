# Documentation Corrections — Slice 2F-25A

All six unapproved points were justified. Each is corrected here.

## 1. Privacy closure was over-claimed (2F-25)
2F-25 asserted "PRIVACY — CLOSED for review content, with named residuals"
while three mounted reads were unscoped. Naming a residual does not close it,
and the `list_by_customer` residual in particular was a **cross-tenant
customer-data read**, not a benign gap. All three are now scoped, and the
claim is re-made on that basis.

## 2. "Runtime verification exits zero" was unsupported (2F-25)
There was no verifier script. The claim rested on a test suite that did not
test the residual reads. A real verifier now exists, fails on each named
condition, and its discriminating power is itself tested.

## 3. create_request was classified FULLY_PROTECTED prematurely (2F-25)
Tenant pinning was mistaken for ownership proof. `job_id` and `customer_id`
remained client-supplied and unverified, and the global duplicate check leaked
foreign job numbers. Parent lineage is now proven; the classification is
retained on evidence rather than assumption.

## 4. Denominator completeness was implied more strongly than warranted
2F-25 did flag the blind spot, but its coverage section read as a settled
figure. This slice labels it **CURRENT_CANONICAL_COVERAGE** throughout, and
the verifier fails if any document claims application-wide completeness.

## 5. The environment statements contradicted each other (2F-25)
`known-limitations.md` said "No live database or HTTP server" while
`regression-report.md` documented the stack being up. The first was stale
boilerplate that should have been retracted when the measurement changed.
Corrected in `environment-test-evidence.md`, with the measured state, the
per-group breakdown, and what genuinely remains unavailable.

## 6. The final status was over-claimed (2F-25)
It asserted privacy closure on the strength of 1-3. This slice re-earns the
same status for the legacy engine specifically, with the scope of the claim
stated explicitly in `approval-gate.md`.

## 7. A regression 2F-25 introduced, not previously reported
`field_ops.service` job close silently stopped creating review requests
(`TENANT_ACCESS_DENIED`, swallowed). Found by enumerating **every** caller of
`create_review_request` — which 2F-25's own bypass report failed to do,
listing only the HTTP route. Confirmed empirically, then repaired.

## 8. Another prose-matching assertion, self-caught
This slice's first-draft test asserted `"ServiceJob" not in src` and failed
against its own docstring saying ServiceJob is NOT used — the same trap 2F-24
hit with `Depends(get_current_user)`. Fixed by stripping docstrings and
comments before matching, in both the test and the verifier.

## 9. Forward annotation added to Slice 2F-25
