# Remediation Readiness Decision

## Disposition: NOT_READY_MUTATION_GAPS

## Prerequisite checklist (Workstream 12's 10 items)

| # | Prerequisite | Status |
|---|---|---|
| 1 | All mounted tenant-user mutation routes classified | **Partial** — all 185 tenant-facing routes have an automated guard-status classification (real, live data); per-endpoint domain/ownership semantics were not individually hand-verified for all 185 (only the 10 already-protected + representative samples) |
| 2 | All applicable mutation routes protected | **No** — 10 of 185 (5.4%) |
| 3 | Alternate mutation paths protected | **No** — the job-execution/field_ops overlap identified in `alternate-route-bypass-report.md` remains unresolved |
| 4 | Read-only direct API test matrix passes | **N/A** — cannot pass a test matrix against guards that don't exist yet; see `tenant-readonly-test-matrix.csv` |
| 5 | Authorized mutation regressions pass | **Yes**, for the 1 already-protected domain (pre-existing, not re-broken); not applicable to the other 175 since no new guard was added to them |
| 6 | Session revocation on access reduction works | **Yes** — implemented and tested this slice for permission reductions specifically |
| 7 | Tenant isolation passes | **Yes** — structurally, confirmed via `update_permissions`'s tenant-ownership check remaining intact |
| 8 | Effective permissions work | **Yes** — confirmed Slice 2E, re-confirmed this slice (365/365 regression) |
| 9 | Rollback plan exists | **Yes** — same pattern as Slice 2D's `manager@` remediation (documented, not yet needed since no remediation occurred) |
| 10 | Migration 144 can be applied after remediation | **Not yet** — blocked on prerequisite #2 first, then on `readonly@`'s actual remediation |

**2 of 10 fully satisfied, 1 partial, 1 N/A pending the others, 6 blocked directly or indirectly by prerequisite #2 (mutation-guard coverage).**

## Why NOT_READY_MUTATION_GAPS specifically (not one of the other dispositions)
- Not `NOT_READY_SESSION_GAP` — the session gap (for permission reductions) was closed this slice.
- Not `NOT_READY_PERMISSION_GAP` — effective-permission calculation itself works correctly (Slice 2E).
- Not `NOT_READY_UNVERIFIED_ROUTES` — the routes aren't unclassified, they're classified as *unprotected* (a stronger, more actionable finding than "unknown").
- Not `PRODUCT_DECISION_REQUIRED` — there's no ambiguity about what needs to happen (apply the guard consistently); it's an engineering-completion gap, the same category Slice 2E already correctly identified, now precisely quantified rather than resolved.

## What would change this disposition
Extending `require_tenant_mutation_permission` (or an equivalent, carefully-scoped guard) across the 175 currently-unprotected tenant mutation endpoints, one router module at a time, each with its own regression tests proving authorized tenant_owner/staff/technician behavior is preserved. Given the scale (24 router modules, several containing a mix of genuinely-different personas per the technician/tenant-owner distinction), this is realistically several future slices' worth of work, not one.

## readonly@demo-ac-services.local — unchanged
Confirmed via live query: role distribution identical to the start of this slice. 7 sessions remain unrevoked (unchanged — no remediation attempted, so nothing to revoke).
