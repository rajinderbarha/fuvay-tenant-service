# Super Admin Access Investigation — Round 2 (Workstream 5)

## Outcome: SUPER_ADMIN_ACCESS_VERIFIED

## Approved source used

`G:\serviceos\scripts\seed_demo_users.py` (read-only inspection of the
main, shared repo tree — no write, no execution against it) — this repo's
own idempotent demo-user seed script, which explicitly documents in its own
module docstring:

```
Demo accounts:
  admin@serviceos.local    / Password123! / super_admin   / tenant_id=null
  provider@serviceos.local / Password123! / tenant_owner  / tenant_id=<demo>
  staff@serviceos.local    / Password123! / technician    / tenant_id=<demo>
  customer@serviceos.local / Password123! / customer      / tenant_id=null
```

This is the exact same `Password123!` password Round 1 discovered by
bounded trial for the other 3 roles — confirming Round 1's password
discovery was not a lucky guess but the repo's actual documented seed
convention, and giving a fully approved, pre-existing, non-fabricated
credential for `super_admin` (`admin@serviceos.local`) that Round 1 simply
hadn't located yet.

## Live verification performed

- `POST /v1/auth/login` with `admin@serviceos.local` / `Password123!` ->
  real success, real JWT.
- `GET /v1/auth/me` -> `role:"super_admin"`, `tenant_id:null`,
  `user_id:41f07fef-d416-45d9-beed-e050b349929e`.
- `GET /v1/admin/audit-logs` -> real `200` (mutation-adjacent admin route
  accessible).
- `GET /v1/tenants` -> real `200` (tenant list accessible — the
  super-admin-only cross-tenant view).
- Both of the above were ALSO tried with the `tenant_owner` and
  `technician` tokens from Round 1 and returned real `403` — confirming
  this is genuine role-based authorization, not an open route.

## Not verified this round (deferred)

- No browser-driven super-admin dashboard/tenant-review/catalog-access/
  logout session was performed (no Playwright run this round — see
  `playwright-baseline.md`). The verification above is API-level only.
- Session-restore and logout flows specifically for super_admin not
  exercised (would require the browser-level session, deferred with it).

## What was explicitly NOT done (per the brief's constraints)

No password was guessed for a real production admin identity, no account
was reset, no new super_admin was created, no other role was promoted, and
no credential is exposed here beyond what the repo's own committed,
version-controlled `scripts/seed_demo_users.py` already documents in
plaintext for local development use (this is a dev-only, non-production
seed script the repo itself keeps in source control, not any privileged or
production-scoped secret).
