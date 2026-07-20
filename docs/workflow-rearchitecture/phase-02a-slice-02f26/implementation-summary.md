# Implementation Summary — Slice 2F-26

## Final status: APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED

## The finding

The prefix-based inventory identified tenant routes by
`/v1/tenant|provider|staff`. Slice 2F-25 proved that misses real capabilities
(three tenant mutations under `/v1/reviews`). This slice rebuilt the inventory
from **actual persona, capability and side-effect evidence** and found the
blind spot was far larger:

**28 further tenant/provider mutations had never been counted. 26 of them are
unprotected.**

| | before | after |
|---|---|---|
| denominator | 229 | **257** |
| numerator (protected) | 212 | **214** |
| unprotected | 17 | **43** |
| queued modules | 7 | **11** |

The unprotected queue more than doubled. The largest new module is
`app.engines.auth.router` (12 routes): MFA confirm/disable, password change,
staff invite, **staff permission updates**, staff deactivate, impersonation,
API-key create/revoke/patch — credential- and permission-mutating surfaces a
prefix sweep never looked at.

## Method

`sweep_2f26.py` walks the fully constructed app and, for every route,
AST-analyses the handler **and the service methods it calls** for persistent
and external side effects, plus the full transitive dependency chain.
`classify_2f26.py` assigns behaviour and persona. Persona comes from the
**authoritative tenant source** — does the handler derive its tenant from the
authenticated principal and then mutate? — never from the URL.

`adjudicate_2f26.py` then requires **two-source evidence** (tenant derivation
AND a persistent side effect) before any route may enter the denominator.

## Scale

**2299 mounted routes** (excl. HEAD/OPTIONS) from one production factory
(`create_app()`, 81 `include_router` calls, no conditional mounts). The
pre-existing tool reported 1186 because it filters to POST/PUT/PATCH/DELETE
before looking — the filter that makes a mutating GET invisible.

| Behaviour | Count |
|---|---|
| READ_ONLY | ~1029 |
| DATABASE_MUTATION | ~977 |
| **READ_ONLY_POST / PUT / PATCH** | **145** |
| HEALTH_OR_DIAGNOSTIC | 51 |
| DATABASE_AND_EXTERNAL_MUTATION | 41 |
| **MUTATING_GET** | **31** |
| EXTERNAL_SIDE_EFFECT | 18 |

1058 genuine mutations by side effect versus 1186 by HTTP method — the two
sets differ in **both** directions.

## Four bugs in my own tooling, fixed before trusting any output

1. **`for r in app.routes` returns 207 wrappers and zero routes.** FastAPI
   nests included routers behind `_IncludedRouter.original_router`. The first
   run produced an *empty* inventory; reported as-is that would have been a
   silent "no routes found".
2. **Prefix-based persona disagreed with 149 of 229 canonical rows** — evidence
   the classifier was wrong, not the CSV. Replaced with the
   authoritative-tenant-source rule; disagreement fell to 55.
3. **`record_platform_audit` sat in both the external and audit marker sets**,
   so the audit-only rule never fired and pure reads looked like mutations.
4. **Depth-2 following resolved service methods by bare name**, so a read
   handler calling `svc.get_deposit()` picked up writes from an unrelated
   same-named method in another engine. Restricted to same-engine following.

A fifth issue was a **path-form mismatch**: child routers report `route.path`
without the parent `/v1` prefix, so the same route appeared as *both* a missing
canonical row and an unmatched one. Normalized at every comparison site.
Without that fix the denominator would have moved wrongly in both directions.

## A route my tooling was right about and I was wrong about

I flagged `GET /v1/commerce/tenants/{tenant_id}/deposit` as a likely false
positive — a GET classified as a mutation. Reading the source:
`get_deposit_status()` calls `_get_or_create_deposit()`. It **lazily creates a
database row**. A genuine mutating GET, and exactly the class of route a
method-based inventory can never see. It is now in the denominator.

## What was NOT done

**Nothing was removed.** 55 canonical rows disagreed with the classifier;
adjudication shows they are predominantly tool limitations (indirect tenant
derivation, service-layer delegation), not evidence a capability is absent.
Workstream 6 forbids removal without exact evidence, so zero rows were removed.

**No authorization was implemented.** The 26 newly discovered unprotected
routes raise the denominator only.

## Final status
`APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED` — see `approval-gate.md`.
