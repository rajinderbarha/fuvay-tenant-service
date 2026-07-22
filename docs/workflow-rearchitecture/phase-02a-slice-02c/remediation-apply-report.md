# Remediation Apply Report

## No data mutation was approved or performed this slice.

Both confirmed invalid-role accounts (`manager@demo-ac-services.local`, `readonly@demo-ac-services.local`) remain in their original state:
- `manager@demo-ac-services.local`: `role='tenant_manager'`, unchanged.
- `readonly@demo-ac-services.local`: `role='tenant_readonly'`, unchanged.

This is confirmed by a live database query run immediately before writing this report:

```
role           | count
---------------+------
admin_finance  | 1
admin_operations | 1
admin_readonly | 1
admin_security | 1
customer       | 4
staff          | 1
super_admin    | 3
technician     | 5
tenant_manager | 1   <- unchanged
tenant_owner   | 6
tenant_readonly| 1   <- unchanged
```

Identical to the distribution recorded in Slice 2B's audit and at the start of this slice — zero rows changed.

## Why no apply occurred
Per `remediation-decision-register.md`, both accounts were classified `MANUAL_ROLE_CONFIRMATION_REQUIRED`:
- Account 1's only available evidence is name-similarity, which this slice's rules explicitly forbid treating as sufficient for automatic remapping.
- Account 2 has no canonical role to map to at all — this is a registry gap, not an investigation gap.

The remediation script (`scripts/workflow_rearchitecture/remediate_invalid_roles.py`) was built, and its safety guards were exercised live against the real database (see `remediation-dry-run-report.md`), but it was never invoked with `--apply --confirm` against a real, approved mapping.

## What would need to happen before an apply report shows a real change
1. A human with knowledge of the `demo-ac-services` tenant confirms account 1 is intended as `staff`.
2. A product decision is made about account 2 (map to `staff` accepting broader-than-"read-only" access, build a real tenant-read-only role, or deactivate the account) — see `remediation-decision-register.md`'s cross-account note.
3. Only then would a future slice run the script with `--apply --confirm` and produce a report showing actual before/after values, the `auth_audit_logs` row ids created, and session-revocation results (per `token-session-impact.md`).

## Database integrity guard status
Migration 144 (the CHECK constraint) also could not be applied, for the same underlying reason — it detected these same 2 accounts and aborted by design (see `database-integrity-guard.md`). The database remains at revision 143.
