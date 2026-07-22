# Global Coverage Update — Slice 2F-11 (Workstream 21)

## Existing inventory definition
`docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`
already contained all 11 `app.engines.execution.real_estate_router`
mutation routes **before this slice**, classified `TENANT_TECHNICIAN_MUTATION`
and `guard_status: UNVERIFIED` — confirmed by direct grep. Unlike
customer-facing complaint routes (Slice 2F-10, correctly excluded), this
module's routes were already part of the 182-route tenant-mutation
denominator.

## Are these routes already included in the denominator?
**Yes.** No double-counting risk — these 11 rows already existed in the
CSV; this slice updates their `guard_status`/`required_action`/
`verification_level` columns in place, adding zero new rows.

## Previous / corrected totals
- Previous tenant total: 182 (unchanged — no new rows added).
- Previous protected count: 106.
- **New protected count: 117** (106 + 11 newly protected).
- Routes newly protected: all 11 `real_estate_router` mutation rows
  (`agent_accept`, `agent_reject`, `agent_mark_contacted`,
  `agent_follow_up`, `agent_plan_site_visit`,
  `agent_complete_site_visit`, `agent_qualify`, `agent_disqualify`,
  `agent_convert`, `agent_close_lost`, `agent_add_note`) —
  `UNVERIFIED` → `TENANT_MUTATION_ROLE_SCOPE_AWARE`.
- Routes reclassified or excluded: none.

## Note on raw CSV row-count discrepancy
A direct recount of the CSV this slice performed found 185 total data
rows (not 182) and a `guard_status`-based protected count of 114 (not
106) using a simple accepted-status filter — a discrepancy from the
185→182 headline figures cited consistently across every prior slice's
approval-gate documents. This was **not investigated or reconciled
further this slice** — it predates this slice's own changes (confirmed
by checking the file's `FALSE_POSITIVE`/`PLATFORM_ADMIN_ONLY (corrected
Slice 2F-1A...)` rows, which suggest some rows are intentionally excluded
from the historical "182" headline count for reasons documented in
earlier slices, not reasons this slice's scope covers). This slice
reports its own delta (11 routes, `UNVERIFIED` → protected) against the
established, repeatedly-cited baseline (106/182 → 117/182) rather than
unilaterally recomputing the historical total from a raw row count,
consistent with the instruction not to change counts without runtime
evidence specific to this slice's own module.

## Customer route coverage
Unaffected — `customer_router`'s single `/tracking` read route was never
part of the tenant-mutation denominator (it is not a mutation at all,
GET only) and is not added to it now.

## Remaining counts
- Remaining unprotected (tenant-mutation denominator): 65 of 182 (76 − 11).
- Remaining unverified count for `app.engines.execution.real_estate_router`
  specifically: **0** (down from 11).
- Remaining module count: not recomputed this slice (would require a
  platform-wide re-audit beyond this module's scope) — unchanged
  methodology from every prior slice.
