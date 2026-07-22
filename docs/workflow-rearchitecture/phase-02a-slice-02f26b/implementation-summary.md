# Implementation Summary — Slice 2F-26B

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

Coverage remains **214 / 257**. Canonical CSV hash **`45244cd9540456db`** —
byte-identical to the frozen slice-start value. Zero canonical edits, zero
application files modified.

The status is unchanged, but the **foundation is now repaired and proven**,
which is what this slice was for.

## Both named blockers are fixed and fixture-guarded

### BLOCKER 2 — guard-alias resolution: FIXED, 0 unresolved

A resolver now takes the dependency callable from the **live route object**
and unwraps aliases, wrappers, `functools.partial` and closure cells.

Resolution progressed 253 unresolved → 191 → 146 → **0**, through three
distinct mechanisms discovered by reading the source rather than guessing:

| Pattern | Resolution |
|---|---|
| Router-local alias (`_provider_guard = require_owner_or_office_staff_mutation`) | live callable identity |
| Real named guard with inline role tuple | AST extraction of the `user.role not in (...)` tuple |
| Factory guard (`_check.__name__ = f"require_{permission.replace(':','_')}"`) | **exact reverse index** built from the real permission set |
| Role set held in a module constant | live constant lookup |

Guessing where separators had been failed on three-segment permissions
(`admin:jobs:read`) and on dotted ones (`marketing.automation.read`, which
contain no colons at all). The reverse index removed the guessing entirely.

**Fixture:** `POST /v1/provider/notifications/mark-all-read` — the route
2F-26A would have wrongly removed from the closed platform-notifications
module — now resolves through `_provider_guard` to
`require_owner_or_office_staff_mutation`, roles
`staff | super_admin | tenant_owner`, persona **TENANT_PROVIDER_MUTATION**.

### BLOCKER 1 — principal vs target tenant: FIXED

Tenant values are now classified by **origin**, never by symbol presence:
`PRINCIPAL_TENANT`, `PLATFORM_ADMIN_TARGET_TENANT`, `CLIENT_ASSERTED_TENANT`,
`UNKNOWN_TENANT_ROLE`.

**Fixture:** `POST /v1/tenants/{tenant_id}/suspend` — the route 2F-26A wrongly
called tenant/provider — now classifies `PLATFORM_ADMIN_TARGET_TENANT` →
**PLATFORM_ADMIN_MUTATION**.

A third test asserts the two routes diverge, so the `tenant_id` symbol alone
can never decide persona again.

## A material discovery about the permission model

**146 guard symbols reference permissions that do not exist in
`ROLE_PERMISSIONS` at all** — `catalog:tiers:write`, `packages.read`,
`setup_templates:write`, `marketing.automation.read` and others.

Reading `PermissionChecker.has` (resolution order: super_admin → role wildcard
→ exact → **StaffPermission runtime override** → engine wildcard), those
guards admit:

- `super_admin` unconditionally, and
- **any staff principal carrying a matching per-user StaffPermission override**

So their admitted set is **not statically determinable**. The resolver records
them as `{super_admin}` with confidence `STATIC_ONLY_RUNTIME_EXTENSIBLE`
rather than asserting a complete role set.

This is a genuine finding about the authorization model, not a tooling
limitation, and it affects any future persona reconciliation.

## Control fixtures and closed-module canaries: 26/26 passing

Controls cover platform-admin-on-tenant, aliased provider guard, customer
self-service, generic-prefix legacy tenant mutation, `require_tenant_owner_mutation`,
and a mutating GET. Canaries cover platform_notifications, customer_reviews,
legacy review, Package Commerce and compliance — each asserted still mounted,
still classified TENANT_PROVIDER, and still present in the canonical CSV.

## The classifier now fails to "manual", not to a guess

`GET /v1/commerce/tenants/{tenant_id}/deposit` admits a **mixed** role set
(`admin_finance` + `tenant_owner`), takes its tenant from the path, and its
ownership check lives in the service (`_assert_owns_tenant_deposit`). The
classifier returns `REQUIRES_MANUAL_ADJUDICATION`.

That is the correct, safe outcome — and it is asserted as such. The previous
adjudicator guessed in exactly this situation and was wrong.

## Why still BLOCKED

The mission's strict edit gate requires, before any canonical change: every
control passing, every canary passing, all aliases resolved, **and a 20-route
validation sample at 100% manual agreement**.

The first three now hold. The 20-route sample was **not** completed in this
slice. Under the gate, that alone forbids canonical edits — so none were made
and the hash is unchanged. The eleven hidden-side-effect candidates were
likewise not individually adjudicated.

Reporting anything other than BLOCKED would misrepresent a foundation slice as
a reconciliation.

## What the next slice can now rely on

A resolver with **zero unresolved guards**, tenant-authority direction
modelled explicitly, control fixtures and closed-module canaries that fail
loudly, and a classifier that declines to guess. The remaining work —
20-route sample, eleven side-effect candidates, then the 123 — has a trustworthy
base for the first time.
