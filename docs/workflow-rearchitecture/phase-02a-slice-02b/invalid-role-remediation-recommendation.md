# Invalid Role Remediation Recommendation

**This document is a recommendation only. No remediation has been executed. Per the explicit instruction, invalid users are not silently migrated to `staff` or any other role — this requires separate, informed approval.**

## Affected records
| email | current (invalid) role | tenant | account state |
|---|---|---|---|
| manager@demo-ac-services.local | `tenant_manager` | demo-ac-services | active, verified |
| readonly@demo-ac-services.local | `tenant_readonly` | demo-ac-services | active, verified |

## Detection query (safe, read-only, re-runnable)
```sql
SELECT id, email, role, tenant_id, is_active, is_verified, created_at
FROM users
WHERE role NOT IN (
  'super_admin', 'tenant_owner', 'staff', 'technician', 'customer', 'guest',
  'admin_operations', 'admin_finance', 'admin_security', 'admin_readonly'
);
```
Run this periodically (or as a CI/deploy-time check) to catch any future drift — e.g., from another seed script or a direct DB edit that bypasses API-level validation.

## Safe mapping options

Both accounts were created by a demo seed script with clear, unambiguous intent from their `full_name` field and email local-part:

| Account | Evident intent | Recommended real role | Confidence |
|---|---|---|---|
| manager@demo-ac-services.local ("Tenant Manager") | A non-owner staff-level tenant user | `staff` | High — `staff` is the real canonical role for exactly this designation, and is what Slice 2's fixed `VALID_TENANT_ROLES` set now offers as the only non-owner option |
| readonly@demo-ac-services.local ("Tenant Read Only") | A read-only tenant-side viewer | **No exact canonical equivalent exists.** The 10 canonical roles have no "tenant read-only" concept — `staff` carries whatever permissions the `staff` role grants (not read-only), and `tenant_owner` is full access. Mapping to `staff` would grant more than "read only" implies; there is no safe automatic choice. | Low — cannot be automatically mapped |

## Cases that cannot be mapped automatically
`readonly@demo-ac-services.local` — as documented above, there is no canonical role matching "tenant-side read-only user." This is not a mapping-confidence problem to solve with more investigation; it's a genuine product gap: the 10 canonical roles simply don't have a read-only tenant-side concept (unlike the admin side, which has `admin_readonly`). Two real options exist, requiring a product decision:
1. Map to `staff` anyway, accepting this demo account gets more access than its name implies (acceptable for a demo/dev-only account, but sets a bad precedent if the detection query above ever finds a similar case in a non-demo environment).
2. Leave unmapped / deactivate the account, since it's demo data with no real user depending on it.

## User-impact analysis
- Both accounts are demo/seed data in a 4-tenant development database, not production accounts serving a real customer.
- Neither account has any `staff_permissions` override rows, uploaded data, or other dependent state found (not exhaustively checked beyond this table).
- Since both roles are already unrecognized by `ROLE_PERMISSIONS`, both accounts currently have **zero effective permissions** — remediation can only improve their access, never accidentally over-grant beyond whatever role they're mapped to (there is no risk of "taking away" access they currently rely on, because they have none).

## Rollback strategy
If remediation is approved and executed:
1. Record the `id` + prior `role` value for both accounts before any UPDATE (already captured above: `72640932-...` was `tenant_manager`, `05deaee8-...` was `tenant_readonly`).
2. A rollback is a single `UPDATE users SET role = '<prior value>' WHERE id = '<id>'` — trivially reversible since only the `role` column would change, no other field touched, no cascading data affected (0 `staff_permissions` rows).

## Required approval
This remediation should not be executed without explicit sign-off, because:
1. It touches persisted user data (even if demo data), which this slice's instructions explicitly reserve for separate approval.
2. The `readonly@` account has no safe automatic mapping — a product decision is needed on which of the 2 options above to take.

**Recommendation:** approve mapping `manager@demo-ac-services.local` → `staff` (high confidence, matches the fixed `VALID_TENANT_ROLES` set and the account's evident intent) in a future slice, and separately decide the `readonly@` account's disposition (map to `staff` accepting broader access, or deactivate/delete as unneeded demo data) before touching it.
