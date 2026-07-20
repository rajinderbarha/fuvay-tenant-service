# Global Coverage Reconciliation — Slice 2F-10 (Workstream 21)

## Existing inventory definition
`docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`
is explicitly scoped to routes auto-classified `TENANT_USER_MUTATION` —
i.e. tenant-owner/staff/provider-facing mutations. Confirmed by direct
inspection: every row's `auto_classification` column reads
`TENANT_USER_MUTATION`; zero rows reference `complaints.customer_router`
or any other `*_router` module whose persona is `customer`.

## Are customer complaint routes already included?
**No.** Grepped the full CSV for "customer" and "complaint" — the only
complaint-related rows present are the 9 `complaints.provider_router`
routes (Slice 2F-9). No `customer_router` route of any kind appears.

## Previous total / protected count
182 total, 106 protected (unchanged going into this slice — confirmed by
re-reading `phase-02a-slice-02f9/approval-gate.md` and
`phase-02a-slice-02f9b/approval-gate.md`, both citing 106/182).

## Corrected total / protected count
**Unchanged: 182 total, 106 protected.** Customer self-service routes are
correctly *not* part of this denominator, and this slice does not add
them to it — the inventory's own definition (tenant-facing mutations
only) is accurate and was not mislabeled "tenant-only" while secretly
including customer routes (it never did). No double-counting risk exists
because nothing was added.

## Customer complaint routes: tracked separately, not merged in
This slice's own `customer-complaints-final-route-inventory.csv` (15
routes, 8 of them genuine mutations) is the correct, separate inventory
for `complaints.customer_router`. All 8 mutation routes are now verified
via the runtime tool (`--verify-module
app.engines.complaints.customer_router` → 0 unverified, exit 0), using a
newly added `CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED` guard-status
classification (see `scripts/workflow_rearchitecture/inventory_mutation_routes.py`)
that correctly distinguishes "customer-role gated, not tenant-scope
applicable" from "genuinely unverified."

## Routes newly protected / reclassified
- 15 `customer_router` routes: role gate added (`require_customer`),
  where none existed before. Not counted toward the 106/182 tenant figure
  (correctly out of that denominator's scope), but fully closed and
  documented in this slice's own inventory.
- 0 routes reclassified or excluded from the existing 182.

## Remaining counts (unchanged from Slice 2F-9B)
- Remaining unprotected (tenant-mutation denominator): 76 of 182.
- Remaining module count: not recomputed this slice (out of scope —
  would require a platform-wide re-audit, not a customer-router slice).
- Remaining unverified count for `complaints.customer_router`
  specifically: **0** (down from 8, all fixed this slice).

## No inventory description correction was needed
The existing CSV's definition was already accurate and did not claim to
include customer self-service routes — no wording fix was required here,
unlike Slice 2F-9A's correction of Slice 2F-9's own doc claims.
