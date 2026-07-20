# Implementation Summary — Slice 2F-26A

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

The status correction applied to Slice 2F-26 was right, and it remains right
after this slice's work. **No canonical row was added or removed.** The
canonical CSV hash is byte-identical to the frozen slice-start value
(`45244cd9540456db`).

`CURRENT_CANONICAL_COVERAGE` stays **214 / 257**, 43 unprotected, 11 modules.

## Why blocked — two named, reproducible root causes

I built a branch-level adjudicator and iterated it three times. Each iteration
produced verdicts that **failed hand-verification**. The failures are not
random; they trace to two specific defects that heuristics cannot fix.

### Root cause 1 — "references `tenant_id`" is not "scopes to the caller's tenant"

To resolve thin delegating handlers I followed the service layer and accepted
a method referencing `tenant_id` as tenant-scoping evidence. That inference is
**inverted for admin routes that operate ON a tenant identified by path
parameter**.

Concrete failure, verified by reading the source:

```
POST /v1/tenants/{tenant_id}/suspend   ->  Depends(require_super_admin)
```

The adjudicator classified it `TENANT_PROVIDER_MUTATION` because
`suspend_tenant()` references `tenant_id`. It is a **platform-admin** route.
Accepting that verdict would have added a super-admin route to the
tenant/provider denominator.

Distinguishing "filters by the caller's tenant" from "acts upon a tenant named
in the path" requires dataflow analysis tying the predicate back to the
authenticated principal — not a text match.

### Root cause 2 — custom per-router guards defeat static role resolution

My `ADMITS` map covers the shared dependencies. Routers also define **local
guard aliases**:

```
# platform_notifications/provider_router.py:26
_provider_guard = require_owner_or_office_staff_mutation
```

`_provider_guard` is not in the map, so `admitted_roles()` silently degraded to
the `get_current_user` superset, and the route was judged on weaker evidence.

Concrete failure: `POST /v1/provider/notifications/mark-all-read` was
classified `PLATFORM_INTERNAL_MUTATION` — a verdict that would have **removed
a genuine provider tenant row** from the canonical CSV.

That route belongs to the platform-notifications closure approved in the 2F-18
series. Removing it would have silently reopened a closed module in the
inventory.

## What the adjudication did establish (work product, not conclusions)

Five per-route evidence artifacts are written and are usable input for a
future slice:

| Artifact | Rows | Status |
|---|---|---|
| `mixed-persona-route-inventory.csv` | 123 | evidence recorded; verdicts NOT applied |
| `held-candidate-resolution.csv` | 7 | all resolve to TENANT_PROVIDER; NOT applied |
| `classifier-disagreement-adjudication.csv` | 55 | dispositions recorded; NOT applied |
| `mutating-get-revalidation.csv` | 31 | 14 intentional tenant, 11 admin, 3 customer, 1 internal, 2 product-decision |
| `read-only-nonget-revalidation.csv` | 145 | **11 HIDDEN_SIDE_EFFECT_FOUND** — genuine finding needing follow-up |

Each row carries admitted roles, actor derivation, tenant derivation (and
whether it came from handler or service), role-branching, db writes and
external effects.

## The one finding I would act on first

**11 of the 145 "read-only" POST/PUT/PATCH routes show side-effect evidence.**
If confirmed per route, they are mutations currently excluded from the
inventory entirely — a population that has never been persona-classified. This
is the same shape as the generic-prefix blind spot, in a different dimension
(method-declared-read-only rather than prefix).

## Why I did not apply the verdicts anyway

Applying them would have added ~76 routes (including verified platform-admin
routes) and removed ~30 (including a verified provider route from a closed
module). Both directions corrupt the canonical record.

This initiative's recurring failure mode has been confident output from an
unvalidated pass. I have now hand-verified this adjudicator's output three
times and found it wrong each time. Publishing a fourth iteration without
verification would repeat it.

## What a future slice needs

1. Enumerate every custom guard alias per router and resolve its role set
   (mechanical, tractable).
2. Replace the tenant heuristic with dataflow: does the tenant predicate trace
   to the authenticated principal, or to a path/body parameter?
3. Re-run; hand-verify a statistically meaningful sample per verdict class
   before applying anything.

## Scope

Zero application files modified. Zero canonical rows changed. No module
selected. All prior closures intact.
