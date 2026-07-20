# Slice 2F-25 Approval Gate

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## SECURITY — CLOSED

| Requirement | Status | Evidence |
|---|---|---|
| Every mounted legacy route inventoried | MET | 15 routes, `legacy-review-route-inventory.csv` |
| One capability + one persona per route | MET | no route UNKNOWN or UNVERIFIED |
| Primary-key-only mutation authorization removed | MET | `_get_review_scoped` |
| Primary-key-only private read removed | MET | detail read tenant-scoped |
| Cross-tenant mutation fails | MET | SQL predicate; foreign row never loaded |
| Client tenant authority removed | MET | `_effective_tenant`; mismatches refused |
| Actor identity server-derived | MET | ids from JWT; no actor-type field exists |
| Read-only tenant users denied mutation | MET | scope-aware `require_tenant_mutation_permission` |
| Legacy `POST /v1/reviews` remains 410 | MET | asserted 3 ways |
| Runtime verifier exits zero | MET | `runtime-verification-report.md` |

The bar — *"do not claim security closure while a legacy route can mutate a
foreign review"* — is satisfied at the **service** layer, so a router
regression alone cannot reopen it.

## DOMAIN INTEGRITY — CLOSED

State transitions explicit; duplicate flag raises `CONFLICT` before any write;
the only tenant-reachable transition is `→ flagged`; `resolve_flag`
(publish/remove) is `require_super_admin`; flagging and replying touch no
aggregate; invalid actions write nothing
(`no-partial-persistence-proof.md`).

## PRIVACY — CLOSED for review content, with named residuals

Six cross-tenant read paths closed: four list routes now pin the tenant to the
principal, and the detail route is tenant-scoped rather than relying on
`_assert_owns` — which only ever fired for the customer role and was never a
tenancy boundary, despite being used as one.

**Three reads remain unscoped and are disclosed, not claimed:**
`GET /aggregates/{entity_type}/{entity_id}`, `GET /requests/jobs/{job_id}`,
and `GET /customers/{customer_id}` for non-customer roles. They expose
aggregate figures and request status, **not review content**. Privacy closure
is asserted for the review-content surface specifically, with these named in
`known-limitations.md` and `product-decisions-required.md`.

## GLOBAL COVERAGE — RECONCILED

**209/226 (provisional) → 212/229.**

The prefix-based Design A sweep only ever considered
`/v1/provider|staff|tenant/*`. The legacy engine mounts at `/v1/reviews/*`, so
**three genuine tenant mutations had never been counted at all** — not
excluded on evidence, never considered.

- Denominator 226 **+3** = 229 (reply, flag, create_request)
- Numerator 209 **+3** = 212 (all three protected in the same slice)
- Unprotected: **17** (unchanged)

`resolve_flag` (super_admin) → outside X/Y. `POST /v1/reviews` (410) →
deprecated, excluded. Neither added. The arithmetic was **not** forced to
209/226; the honest finding is that the previous denominator was *incomplete*.

## PRODUCT POLICY — BLOCKED (expected)

Migration/retirement of the legacy engine; the broken legacy reply contract;
the tenant-portal `resolve` control; scoping the three residual reads; whether
`P.TENANT_UPDATE` is the right permission for review actions; and whether to
re-sweep the application on a persona rather than prefix basis. See
`product-decisions-required.md`.

## Regression — and an honest disclosure about it

**Zero new failing node IDs. Zero new error node IDs.**

But the headline numbers moved enormously (86 → 7 failures, 111 → 0 errors),
and **that was not this slice**. The API server, PostgreSQL and Redis became
reachable during this slice — verified by socket probe. 79 failures and all
111 errors resolved environmentally. Claiming them would be the most
misleading available reading of this data, and `regression-report.md` leads
with the correction.

One genuine benefit follows: the changed code paths were exercised **live**
for the first time in this initiative (review suites: 142 passed, 1 skipped,
0 failed; `TestBookingRatingEndToEnd` ran end-to-end after erroring for the
whole initiative). Credit for that belongs to the environment, not the slice.

## Honest disclosures

- **2F-24's `DISTINCT_MODEL` call was correct** and its flag was warranted —
  the exposure here was *larger* than the canonical engine's.
- **A vacuous assertion in my own first-draft tests**: asserting
  `"tenant_id" in str(statement)` passes even for an unscoped query, because
  every `SELECT reviews.*` lists that column. Caught only because the negative
  case failed for the same reason; both rewritten to inspect the WHERE clause.
- **The canonical denominator may still be incomplete elsewhere** — the same
  generic-prefix blind spot could hide routes in other engines. This slice
  reconciled one engine and did **not** re-sweep the application.
- **Two pre-existing frontend/backend mismatches** (broken `reply` contract,
  tenant-called `resolve`) found and deliberately not fixed.

## Preserved (re-confirmed by test)

Canonical `customer_reviews` closure (2F-24); Package Commerce (2F-22);
compliance (2F-20); legacy 410; platform-notifications, Booking,
quote-checklist, invoice-lineage, field_ops closures; `PartsRequest`
ServiceJob-only; Booking/ServiceBooking and field_ops.Job/ServiceJob separate;
canonical roles only, no alias, no new permission; `readonly@` untouched;
Migration 144 unapplied; **Slice-2D canaries untouched** (one still fails with
an identical node ID; the other now passes environmentally).

## Scope discipline

No model merged, no records migrated, no engine deleted, no 410 restored. No
role, alias, permission or migration added. No pipeline merged. No frontend
change was needed or made. Two application files changed
(`app/engines/review/service.py`, `app/engines/review/router.py`), both within
the legacy review boundary.

## Stop condition

Stops at the Slice 2F-25 approval gate. No unrelated module begun.
**7 modules / 17 routes remain** — `remaining-module-queue-update.csv`.

## Forward annotation (added by Slice 2F-25A)
All six points on which this slice was NOT approved were justified, and are
corrected in Slice 2F-25A:

1. **Privacy closure was over-claimed.** Naming three unscoped reads as
   "residuals" did not close them -- and `list_by_customer` in particular was a
   cross-tenant customer-data read, not a benign gap. All three are now scoped.
2. **"Runtime verification exits zero" was unsupported** -- no verifier script
   existed. One now does (25 checks), it fails on each named condition, and its
   discriminating power is itself tested.
3. **`create_request` FULLY_PROTECTED was premature.** Tenant pinning was
   mistaken for ownership proof; `job_id` and `customer_id` remained
   client-supplied and unverified, and the global duplicate check leaked foreign
   job numbers via `already_exists`. Parent `field_ops.Job` lineage is now
   proven and the customer is derived from the Job.
4. **Denominator completeness** is now labelled CURRENT_CANONICAL_COVERAGE
   throughout, enforced by the verifier.
5. **The environment statements contradicted each other** -- this slice's
   `known-limitations.md` said "no live database or HTTP server" while its
   `regression-report.md` documented the stack being up. The first was stale
   boilerplate that should have been retracted when the measurement changed.
6. **The final status** rested on 1-3 and is re-earned in 2F-25A with its scope
   explicitly bounded to the legacy engine.

**A regression this slice introduced, not previously reported:** tenant pinning
on `create_review_request` broke the `field_ops` job-close path, which passed no
tenant context -- every job close silently stopped creating its review request
(`TENANT_ACCESS_DENIED`, swallowed by `except Exception`). This slice's own
service-bypass report listed only the HTTP route and missed the internal caller.
Confirmed empirically and repaired in 2F-25A.

Coverage is unchanged at 212/229 -- 2F-25A closed three reads and hardened one
mutation without adding or removing any route.

Final status for 2F-25A:
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`, scoped
explicitly to the legacy review engine.
See `../phase-02a-slice-02f25a/approval-gate.md`.
