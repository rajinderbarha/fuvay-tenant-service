# Slice 2F-25A Approval Gate

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

**Scope of this claim, stated precisely:** it applies to the **legacy review
engine (`app.engines.review`)** — its 15 mounted routes, its four previously
unresolved capabilities, and its service layer. It is **not** a claim about
the application as a whole, and it is **not** a claim that the canonical
mutation denominator is complete. Both exclusions are enforced mechanically
by the verifier.

## The six unapproved points — all justified, all addressed

| # | Point | Resolution |
|---|---|---|
| 1 | Privacy closure with three reads unscoped | All three now scoped: aggregate (tenant), job-request (customer/tenant), customer-list (tenant for non-customers). |
| 2 | Verifier success with known gaps | A real verifier now exists (25 checks), fails on each named condition, and its discriminating power is itself tested. |
| 3 | `create_request` FULLY_PROTECTED without parent proof | Parent `field_ops.Job` resolved in-tenant; customer **derived** from the Job; `CUSTOMER_MISMATCH` on substitution; ownership precedes the duplicate check. |
| 4 | Application-wide denominator completeness | Labelled **CURRENT_CANONICAL_COVERAGE** throughout; the verifier fails if any document claims completeness. |
| 5 | Contradictory environment statements | Corrected in `environment-test-evidence.md` with measured state, per-group service usage, and what genuinely remains unavailable. |
| 6 | The final status | Re-earned on evidence, with its scope explicitly bounded above. |

## SECURITY — CLOSED (legacy engine)

Mutation lookups scoped; personas scope-aware; client tenant authority
removed; **`create_request` parent ownership now proven** rather than assumed.
The mission's bar — *no full security closure while create_request lacks
exact parent ownership* — is met by proving the lineage, not by asserting it.

## DOMAIN INTEGRITY — CLOSED (legacy engine)

Duplicate behaviour explicit and ordered after ownership (closing a
cross-tenant existence oracle); state transitions explicit; aggregates
untouched by flag/reply; no partial state on any rejection path.

## PRIVACY — CLOSED (legacy engine)

All four private capabilities scoped. Missing and unauthorized are externally
equivalent within each persona (`residual-error-privacy-equivalence.md`), with
the one cross-persona asymmetry disclosed rather than smoothed. Field-level
classification in `residual-field-privacy.csv` confirms `flagged_reason`,
`flagged_by`, `resolved_by` and `idempotency_key` are never serialized.

## CURRENT_CANONICAL_COVERAGE

**212 protected of 229 currently known.** Unchanged — no route added, removed
or reclassified; `create_request` now earns the status it previously held on
assumption. 17 currently unprotected, 7 currently queued modules.

## Regression

Zero new failures, zero new errors. Run twice under a **stable, measured**
environment; failing node IDs identical between runs. +36 passed = exactly the
new tests. No environment-resolved test attributed to an application change —
nothing resolved environmentally, because the stack was already up and stayed
up.

## A regression I introduced in 2F-25, found and repaired here

`field_ops.service` creates the review request on job close and passed **no
tenant context**. 2F-25's tenant pinning therefore raised
`TENANT_ACCESS_DENIED` on every job close — swallowed by `except Exception`
and logged as a warning. **Review requests silently stopped being created.**

Confirmed empirically before fixing. The node-ID comparison could not see it:
the exception is caught and no test covered the path. Found by enumerating
every caller of the changed method — which 2F-25's own service-bypass report
failed to do, listing only the HTTP route. This is the strongest evidence in
this slice that exact node-ID comparison is necessary but not sufficient.

## Honest disclosures

- **My own documentation failed my own verifier.** `current-canonical-coverage.md`
  contained the forbidden completeness label inside a sentence disclaiming it.
  A blunt check cannot distinguish a claim from a denial; the wording was
  changed rather than the check weakened.
- **Another prose-matching assertion, self-caught** — a test asserted
  `"ServiceJob" not in src` and failed against its own docstring saying
  ServiceJob is not used. Both the test and the verifier now strip docstrings
  and comments before matching.
- **This slice's tests are deterministic doubles, not live integration**, even
  though infrastructure was available. Security claims rest on SQL-predicate
  inspection and no-write assertions, not executed cross-tenant requests.
- **Same-tenant granularity remains coarse** on two reads; narrowing would be
  invented policy.
- **`_recompute_aggregate` was not re-derived**, so whether hidden/rejected
  reviews contribute to aggregates is unproven — one reason the aggregate read
  is not claimed public.

## Preserved

Canonical `customer_reviews` closure; legacy mutation scoped lookups; legacy
`POST /v1/reviews` 410; Package Commerce; compliance; platform-notifications;
Booking, quote-checklist, invoice-lineage, field_ops closures; `PartsRequest`
ServiceJob-only; Booking/ServiceBooking and field_ops.Job/ServiceJob separate;
canonical roles only; no new role, permission or migration; `readonly@`
untouched; Migration 144 unapplied; **Slice-2D canaries untouched** (file
count unchanged by this slice).

## Scope discipline

No persona sweep performed. No module selected or implemented. No model merge,
record migration or deletion. No 410 restored. No new policy invented for
public aggregates, job-status gating, technician assignment or review-request
visibility — each is recorded as a product decision. Three application files
changed: `app/engines/review/service.py`, `app/engines/field_ops/service.py`
(the regression repair), and one verifier script added.

## Stop condition

Stops at the Slice 2F-25A approval gate. The application-wide persona-based
sweep — the highest-value next inventory action — has **not** begun.

## Forward annotation (added by Slice 2F-26)
Slice 2F-26 performed the application-wide persona-based sweep this slice
deferred. The prediction was correct and the blind spot was **eight times
larger** than the /v1/reviews case that exposed it: **28 further tenant
mutations had never been counted**, 26 of them unprotected -- on /v1/auth,
/v1/media, /v1/me, /v1/bookings, /v1/commerce, /v1/enterprise and /v1/rag.

CURRENT_CANONICAL_COVERAGE advanced 212/229 -> **214/257**, unprotected
17 -> **43**, queued modules 7 -> **11**. The largest new module is
`app.engines.auth.router` (12 routes: MFA, password change, staff invite,
staff permission updates, deactivation, impersonation, API keys).

This slice's own arithmetic was therefore *incomplete*, not incorrect -- and
its insistence on the CURRENT_CANONICAL_COVERAGE label rather than a final
figure was vindicated.

Two of this slice's findings were also generalised by 2F-26:
- the swallowed-exception risk it identified (field_ops job close) is now
  covered by standing behavioural invariants, because exact node-ID comparison
  provably cannot detect that class of regression;
- the non-vacuity traps it hit (docstring matching, whole-statement SQL
  matching) are now encoded as negative fixtures in the application-wide
  verifier.

Final status for 2F-26: `APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED`.
See `../phase-02a-slice-02f26/approval-gate.md`.
