# field_ops Quote Alternate Audit

## Routes inspected
`create_job_quote`, `send_job_quote`, `approve_job_quote`, `reject_job_quote`, `respond_to_quote` (all in `app/engines/field_ops/router.py`, backed by `app/engines/field_ops/service.py`'s `FieldOpsService` methods of the same names, operating on the `JobQuote` model in `app/engines/field_ops/models.py`).

## Per-route findings
| Route | Model/table | Parent pipeline | Customer decision semantics | Amount | Authorization | Financial effect | Frontend callers |
|---|---|---|---|---|---|---|---|
| `create_job_quote` | `field_ops.JobQuote` (distinct table) | `field_ops.Job` | n/a (creation) | Server-computed from labour/parts/visit_fee/tax/discount inputs, negative-amount validated (pre-existing) | Tenant/staff mutation-scope-aware (closed in Slice 2F-14 series, part of field_ops.router 28/28) | None built | tenant-portal (provider quote creation for field_ops jobs) |
| `send_job_quote` | Same | Same | n/a (provider action) | n/a | Same | None | Same |
| `approve_job_quote`/`reject_job_quote` | Same | Same | Distinct: provider-side "quote request approval" step (a DIFFERENT concept from `quote_checklist`'s customer decision) | n/a | Same, closed | None | Same |
| `respond_to_quote` | Same | Same | Customer approve/reject of a `field_ops.JobQuote` — already `require_customer`-gated with `customer_id` server-derived (closed in a prior slice, re-confirmed via source read this slice) | n/a | `require_customer`, closed | None | frontend/customer-app (a distinct customer-facing surface from `quote_checklist`'s customer_router) |

## Classification: **DISTINCT_MODEL_DISTINCT_CAPABILITY**

`field_ops.JobQuote` is an entirely separate table (`job_quotes` — confirmed distinct from `service_job_quotes`), with its own quote-number generator, its own status vocabulary (`"draft"/"sent"/"approved"/"rejected"` — plain strings, not `quote_checklist`'s richer `QS_*` state machine), its own amount-field set (`labour_amount`/`parts_amount`/`visit_fee`/`discount_amount`/`tax_amount`/`pre_approval_limit`), and is exclusively tied to `field_ops.Job` (never `ServiceJob`). There is **no ID overlap possible** between `JobQuote.id` and `ServiceJobQuote.id` (independent UUID primary keys on independent tables) — a quote ID from one system can never be substituted into the other's routes.

## Why this is not reopened
Per this slice's explicit boundary instruction ("Do not reopen field_ops solely because names are similar"), and because:
1. The model, table, and parent pipeline are all distinct.
2. `field_ops.router`'s quote routes were already closed (Slice 2F-14 series; re-confirmed this slice via the unchanged `field_ops.router` 28/28 runtime verification).
3. No same-record bypass exists — the two systems never reference the same row, so a "weaker route reaching the same record" is structurally impossible.

**No weaker same-record route was found.** This audit confirms the boundary rather than finding a defect to fix.
