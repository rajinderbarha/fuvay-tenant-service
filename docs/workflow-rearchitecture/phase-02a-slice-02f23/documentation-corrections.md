# Documentation Corrections — Slice 2F-23

## 1. Six canonical rows were literally `UNVERIFIED` (corrected)

`submit_reply`, `flag_review`, `provider_run_report`,
`generate_launch_campaign`, `submit_campaign_review` and
`update_asset_provider_notes` carried `guard_status = UNVERIFIED` in the
canonical CSV. Workstream 1 forbids leaving any row UNKNOWN or UNVERIFIED.

Each was replaced with its runtime-observed value
`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`, plus a precise
`verification_level` note. Numerator and denominator were asserted unchanged
at edit time (207 before, 207 after) and are re-asserted by
`test_no_canonical_row_remains_unverified`.

This matters beyond bookkeeping: `UNVERIFIED` concealed that **six routes
have no authorization check at all**, including the two now selected for
implementation. The vague label understated live exposure.

## 2. The queue's severity ranking was wrong at the top

The 2F-22 carried-forward queue ranked `customer_reviews.provider_router`
at **rank 1 of the non-selected set with severity MEDIUM**, described as
"public-facing content / provider impersonation risk on submit_reply".

Direct source reading shows it is **CRITICAL** and that the more serious
route is the *other* one. `flag_review` has no object-ownership check at all
(`_get_review` filters by primary key only) and writes
`review.status = "flagged"`, so any authenticated principal can mutate any
review in any tenant. The prior queue characterised the module by its
impersonation risk and missed the cross-tenant IDOR entirely.

This is the second consecutive slice in which a carried-forward queue
severity proved understated on direct inspection (2F-22 corrected the same
kind of understatement for package purchase). The pattern argues for
re-deriving severity from source at every selection slice rather than
inheriting it — which is what the mission already requires and what was done
here.

## 3. Three WS6 risk hypotheses are disproved by source

Per the instruction not to preserve descriptions the source contradicts:

- **marketing_automation** — no bulk targeting, no audience isolation model,
  no sender identity, no consent/suppression handling, no dispatch, and **no
  external delivery of any kind**. All three routes write draft rows or flip
  a review status, tenant-scoped in SQL.
- **media.new_router** — cross-tenant MediaAsset use is **already prevented**
  by the access-policy layer (`assert_can_delete`), closed by the 2F-18
  series. The residual gap is persona scope, not IDOR.
- **profile.router** — role or tenant mutation through profile fields is
  **not possible**; `UpdateBusinessProfileRequest` is a strict allow-list with
  no role, tenant, status or verification field.

## 4. Vocabulary difference recorded, NOT rewritten

13 rows read `ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE` in the canonical CSV while
the runtime tool computes `PERMISSION_ONLY_NOT_SCOPE_AWARE`. Both denote
unprotected; neither is in the VERIFIED set. The labels come from different
eras of the tooling vocabulary. They were left alone: a difference is not
evidence of an error, and changing 13 rows without row-level evidence would
be churn.

## 5. Self-correction during this slice

The first draft of `remaining-route-inventory.csv` packed two values into
`primary_persona` (`"tenant_owner (intended); currently ANY authenticated"`).
This slice's own test `test_every_row_has_exactly_one_persona` failed on it —
correctly, since the quality gate requires exactly one persona per row. The
data was fixed by splitting out a separate `current_effective_access` column
rather than by relaxing the test.

## 6. Historical artifacts NOT rewritten

2F-19's (26 rows / 10 modules) and 2F-21's (20 rows / 9 modules) slice CSVs
were left intact despite the global total having advanced, per the mission's
explicit instruction that point-in-time artifacts must not be rewritten.

## 7. Slice-2D canaries untouched
As required.

## 8. Forward annotation added to Slice 2F-22

Per the convention established across this initiative (2F-21 annotated 2F-20;
2F-22 annotated 2F-21), a forward-annotation section was appended to
`phase-02a-slice-02f22/approval-gate.md`. It records that 2F-22's closure was
re-verified **by test** (`test_package_commerce_closure_still_intact`) rather
than assumed, that the indirect-change audit found zero coupling, that
coverage stands unchanged at 207/226, and which module 2F-23 selected next.

This slice's own mission did not list the annotation among its 25 required
files — it is added to keep the chain of record continuous, and no 2F-22
finding was altered.
