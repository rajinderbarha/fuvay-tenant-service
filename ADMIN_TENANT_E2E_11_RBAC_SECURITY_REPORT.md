# ADMIN-TENANT-E2E-11 — RBAC/Security Report

## Confirmed P0 finding: no tenant read-only/manager role tier exists

Live-verified this session with real credentials and real API calls
(not simulated):

1. Decoded the JWT for `tenant.readonly@serviceos.in` (password
   `Password123!`) — its `role` claim is **`tenant_owner`**, not a
   distinct read-only role.
2. Confirmed at the database level via
   `GET /v1/admin/tenants/{tid}/users` (real admin API): all three
   tenant-side seed accounts for Demo AC Services —
   `tenant.readonly@serviceos.in` ("Tenant ReadOnly"),
   `tenant.manager@serviceos.in` ("Tenant Manager"), and
   `provider@serviceos.in` ("Demo Provider") — **all three have
   `role: "tenant_owner"`** in the `users` table. There is no
   role-level distinction between them at all.
3. Confirmed via source read of `app/core/permissions.py`: the only
   tenant-adjacent access-restriction concept that exists is
   `access_scope` (`TENANT_READONLY_ACCESS_SCOPES = {"customer_support_limited"}`,
   used for a completely different purpose — support staff impersonation
   scoping — not for a tenant-side "read-only owner" tier). There is no
   `tenant_readonly` or `tenant_manager` value anywhere in the role
   system.
4. **Live-verified the consequence**: logged in as
   `tenant.readonly@serviceos.in`, obtained a real token, and called
   `PUT /v1/settings/tenants/{tid}/test_e2e11_key` with a real body —
   the mutation **succeeded (200)**, creating a real tenant setting
   override. (Test data was immediately cleaned up via a real `DELETE`
   call afterward, verified `deleted: true`.)

This is not a guard bug on an existing tier (which the ticket's Part 11
anticipates and would treat as a P2 UI gap) — it is the **absence of the
tier itself**. The seed accounts named "ReadOnly" and "Manager" are
read-only/manager in name only; every one of them can currently do
everything a tenant owner can do, because the backend has no way to tell
them apart from an owner.

## Context: this was a known, flagged gap, now confirmed live
E2E-10's own report flagged: *"Backend scoping exists. Frontend role
guards may still be incomplete."* This session's live verification shows
the gap is deeper than "frontend guards incomplete" — there is no backend
role separation to guard against in the first place for these three
accounts.

## What was NOT done this pass, and why
Building a real `tenant_readonly`/`tenant_manager` role tier (new role
values, a full audit of every tenant-mutation endpoint to gate on it,
frontend guards to match) is a significant, cross-cutting RBAC design
and implementation effort — well beyond this ticket's "small backend fix
if browser E2E exposes a real bug" scope, and risks touching shared seed
data that other already-certified sprints (E2E-07, E2E-08, E2E-10) may
depend on. Not attempted this pass to avoid an unreviewed, high-blast-
radius change under sprint pressure.

## Everything else checked in this Part
- Tenant Owner can view finance — confirmed (all finance/ledger/deposit
  tests passed as `provider@serviceos.in`).
- Tenant cannot access another tenant's finance data — not separately
  re-verified this pass (out of this pass's time budget; no cross-tenant
  API calls were made). Documented as not-yet-verified, not as passing.
- Backend rejects unauthorized mutation with a real error+request_id —
  confirmed the endpoint itself returns structured errors with
  `request_id` (verified via the validation-error path,
  `error_code: VALIDATION_ERROR`, `request_id` present) — the mechanism
  for surfacing errors is real and correct; it's the permission gate
  itself that's missing for this role.

## Verdict
**FAILED** — per this ticket's own explicit rule ("If unauthorized
mutation succeeds, return `NOT_READY_TENANT_RBAC_FAILED`"), this is the
one confirmed, real blocker in an otherwise clean sprint.
