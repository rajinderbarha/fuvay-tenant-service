# Database Constraint Report — Slice 2D

## Pre-application checklist (Workstream 9)

| Check | Result |
|---|---|
| Zero invalid `users.role` values | **No — 1 remains** (`readonly@demo-ac-services.local` = `tenant_readonly`) |
| All legitimate scopes represented | Yes — the 10 canonical roles cover platform, tenant, and self-scoped (customer/guest) roles; confirmed no legitimate value exists outside this set (Slice 2C finding, unchanged) |
| Tests and seeds use canonical roles | Yes for the seed script (fixed this slice); tests use canonical roles throughout (confirmed by the regression suite, 278/278 passing) |
| Invitation paths validate roles | Yes — `VALID_TENANT_ROLES` (tenant_engine) and `VALID_PLATFORM_ROLES` (auth/service.py), both confirmed correct in Slice 2C and unchanged |
| Service-level paths validate roles | Yes for the 2 audited write paths; the seed script (the one previously-unvalidated path) is now fixed |
| Existing migrations remain compatible | Yes — migration 144 makes no change to any other table or column |

## Live execution this slice

```
$ alembic upgrade head
RuntimeError: Migration 144 aborted: users.role contains values outside the 10
canonical RBAC roles: 'readonly@demo-ac-services.local'='tenant_readonly'.
Remediate these accounts first ...
```

Confirmed via `alembic current` (unchanged at revision 143) that no schema change occurred. This is the **correct, required outcome** per Workstream 9's explicit instruction: "If either invalid account remains unresolved, do not apply migration 144. Report it as blocked."

## Comparison to Slice 2C
In Slice 2C, this same migration aborted naming **2** accounts. This slice, it aborts naming exactly **1** — the manager@ account's remediation is reflected immediately in the migration's live detection query, proving the detection logic works incrementally and correctly as accounts are resolved one at a time.

## Downgrade / re-upgrade cycle
**Not executed** — the migration has never been successfully applied (it aborts every time, by design, while `readonly@` remains invalid), so there is no applied state to downgrade from. A downgrade/re-upgrade cycle will be meaningfully testable only after migration 144 successfully applies for the first time.

## Status
**Blocked, correctly, on the 1 remaining account.** No workaround was attempted (e.g., weakening the detection query, excluding this specific account, or force-applying with `--sql`/raw DDL bypassing the migration's own logic) — the migration's refusal is the intended safety behavior, not a bug to route around.
