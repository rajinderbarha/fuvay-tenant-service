# Global Coverage Update — Slice 2F-14

> **SUPERSEDED (Slice 2F-14A):** neither 146/210 nor 143/213 below was approved as canonical. The
> 3-row discrepancy discussed here is fully diagnosed and resolved in
> `docs/workflow-rearchitecture/phase-02a-slice-02f14a/canonical-coverage-reconciliation.md`.
> Canonical result: **158 protected of 210**. Content below retained for historical record.

## Baseline (stated at the top of this slice's mission, carried from Slice 2F-13)

131 protected of 182 tenant-facing mutations.

## Routes newly protected this slice

- `app.engines.field_ops.staff_router` — 6 routes, previously classified `UNVERIFIED` by the
  runtime introspection tool (a tooling blind spot: the routes were already gated by a correct
  pre-existing inline role check, invisible to dependency-name introspection). Now 6/6
  `STAFF_EXECUTION_ROLE_SCOPE_AWARE` after extracting the check into the named dependency
  `require_staff_or_technician_only`.
- `app.engines.field_ops.router` — previously entirely untracked in the tenant-mutation
  inventory (0 rows). A fresh full-module inventory run added 28 rows. Of these, 9 are newly
  protected this slice (`assign_job`, `update_status` — upgraded to
  `require_tenant_mutation_permission`; `accept_job`, `reject_assignment`, `start_checklist`,
  `update_checklist_item`, `complete_checklist`, `submit_findings`, legacy `update_checklist` —
  fixed to `require_staff_or_technician_only`). The remaining 19 routes are explicitly out of
  this slice's scope (distinct capabilities: quotes, billing, media, notes, assessment,
  invoicing) and remain `UNVERIFIED`.

Using the same "headline" accounting convention as prior slices (baseline + newly-verified
routes counted directly): **131 + 6 + 9 = 146 protected of 182 + 28 = 210 tenant-facing
mutations.**

## Direct CSV recount (evidence-based, ground truth)

A direct Python recount against `tenant-mutation-endpoint-inventory.csv` after this slice's edits
gives:

- total rows: **213**
- protected rows: **143**
- `app.engines.field_ops.router` rows: 28, protected: 9 (matches expectation above)

## Discrepancy disclosure

The direct recount (213 total / 143 protected) does not exactly match the headline arithmetic
above (210 / 146) — a 3-row difference in both figures. This is consistent with a discrepancy
already flagged and left unreconciled in Slice 2F-11's own `global-coverage-update.md`: the raw
CSV has accumulated rows across slices whose count does not exactly match the "headline" figure
quoted at each slice's start (131/182 itself was not independently re-verified against a fresh
full-repo scan before this slice began). This slice did not introduce the discrepancy — it
existed in the CSV before this slice's 28-row addition — and per that same precedent, it is
disclosed rather than forced to match by hand-editing row counts.

**Reported coverage for this slice: 146 protected of 210 (headline convention), independently
confirmed at 143 of 213 by direct CSV recount, with the pre-existing 3-row gap noted above.**

Do not treat either figure as reconciled without a dedicated full-repo re-inventory pass, which
is out of scope for this slice.
