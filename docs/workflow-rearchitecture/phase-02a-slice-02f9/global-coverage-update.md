# Global Coverage Update — Workstream 20

## Reconciliation method
Re-ran the runtime mutation inventory tool with no module filter, then
recomputed the tenant-facing denominator and the file's own
"fully_protected" convention.

## Corrected totals

| Metric | Previous (Slice 2F-8) | After this slice |
|---|---|---|
| Total tenant-facing mutations | 182 | **182** (unchanged — runtime-reconfirmed, no denominator correction) |
| Protected tenant-facing mutations | 97 | **106** (+9) |
| Remaining unprotected | 85 | **76** |

## Why the count changed
All 9 mounted mutations in `app.engines.complaints.provider_router` were
previously `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` — zero role,
permission, or access-scope guard of any kind. All 9 are now gated with
`require_tenant_owner_mutation` (no `COMPLAINT_*`/`REWORK_*`/`REFUND_*`
permission exists anywhere in the registry, so no permission was
granted — the narrowest existing composed dependency was reused
instead).

## Routes newly protected (9)
`respond_to_complaint`, `offer_resolution`, `schedule_rework`,
`start_rework`, `complete_rework`, `review_refund`, `submit_ai_answers`,
`create_settlement_proposal`, `respond_to_settlement`.

## Routes reclassified or excluded
None — all 9 were already correctly counted as `TENANT_USER_MUTATION`
in the denominator; only their guard status changed.

## Remaining module count
15 tenant-facing modules remain with at least one unprotected mutation
(down from 16 before this slice) — `complaints.provider_router` is now
fully closed.

## Remaining unverified count
0 within `complaints.provider_router` (9/9 verified, exit 0).

## Files updated
- `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`:
  updated in place — all 9 complaint rows corrected from `UNVERIFIED` to
  `TENANT_MUTATION_ROLE_SCOPE_AWARE`.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`:
  updated in place — `complaints.provider_router`'s row (0/9 → 9/9,
  0% → 100%) and the running TOTAL row (97/182 → 106/182, 53.3% → 58.2%).
