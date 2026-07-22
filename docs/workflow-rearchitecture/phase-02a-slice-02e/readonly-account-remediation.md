# Read-Only Account Remediation — Slice 2E

## Status: NOT remediated — all 9 prerequisites evaluated, several fail

Per Workstream 10's explicit 9-point checklist:

| # | Prerequisite | Status |
|---|---|---|
| 1 | Canonical `staff` role is valid for the tenant | Yes |
| 2 | Read-only access scope is enforced | **No** — see `tenant-readonly-implementation.md` |
| 3 | Effective mutation permissions are empty or explicitly denied | Achievable in principle now (the wiring fix makes deny-overrides work), but not applied — moot without #4 |
| 4 | All supported tenant mutation APIs reject direct calls | **No** — only 1 of 16 router files enforce this |
| 5 | Tenant isolation is proven | Yes, structurally (unrelated to this account specifically) |
| 6 | Navigation reflects read-only access | N/A — no frontend change made (see `frontend-access-alignment.md`) |
| 7 | Session revocation is available | Yes — built in Slice 2D's remediation script |
| 8 | Audit recording is available | Yes — built in Slice 2D's remediation script |
| 9 | Rollback is defined | Would be the same pattern as Slice 2D's `manager@` remediation |

**Since prerequisite #4 (and by extension #2/#3) fails, per Workstream 10's own explicit instruction ("if any prerequisite fails, leave the account unchanged and report why... do not partially remediate it"), `readonly@demo-ac-services.local` was left completely unchanged this slice.**

## No script changes were made to support this remediation
Since the remediation itself did not proceed, no extension to `remediate_invalid_roles.py` for access-scope/permission-configuration application was built this slice — building that machinery ahead of having a provably-safe target to apply it to would be premature (and per rule 5, applying `staff` to this account before proof is explicitly forbidden).

## Confirmed unchanged, live
```
role distribution: tenant_readonly = 1 (unchanged from Slice 2D)
sessions: 7, all unrevoked (unchanged)
```

## What would need to be true before this can proceed
Everything in `tenant-readonly-implementation.md`'s "exact blocker" — comprehensive mutation-guard coverage across the 15 currently-uncovered tenant router files.
