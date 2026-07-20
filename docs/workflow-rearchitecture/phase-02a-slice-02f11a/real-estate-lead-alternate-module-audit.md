# `app.engines.real_estate_lead` Alternate Module Audit — Slice 2F-11A (Workstream 9)

**This is an audit and classification only — no implementation change was
made in this module, per the mission's explicit prohibition.**

## Mounted
Yes — `app/main.py` mounts:
- `app.engines.real_estate_lead.customer_router` (prefix
  `/v1/customer/real-estate/lead-drafts`, 11 routes: 1 POST create-draft,
  1 GET, 1 PUT, 8 further POST action routes).
- `app.engines.real_estate_lead.admin_router` (prefix
  `/v1/admin/real-estate`, 10 routes: 4 GET list/detail, 6 mutation
  routes — all confirmed `require_super_admin`-gated).

## Model
`RealEstateLeadDraft` (table not the same as `real_estate_leads`) —
`customer_id`, `guest_session_id` (supports anonymous/guest drafting),
`selected_tenant_id`, `selected_agent_id`, full requirement fields
(`budget_min/max`, `bedrooms`, `bathrooms`, etc.) AND raw contact fields
(`customer_name`, `customer_phone`, `customer_email`,
`preferred_contact_time`) directly on the draft — plus
`RealEstateLeadDraftEvent` (a parallel event-log model, distinct from
`RealEstateLeadExecutionEvent`).

## Relationship to `execution.real_estate_router`'s `RealEstateLead`
**Distinct model, distinct table, distinct lifecycle stage.**
`RealEstateLead.draft_id` (a foreign key on the *execution* model, per
its own docstring: "Final real estate lead created from a confirmed
draft") is the only structural link — a `RealEstateLeadDraft` is
converted into a `RealEstateLead` at some confirmation step (not audited
this slice — confirmation happens via `app.engines.final_records`, per
Slice 2F-11's earlier finding, out of scope here). No route in either
`real_estate_lead.customer_router` or `real_estate_lead.admin_router`
reads or mutates `RealEstateLead` directly — confirmed by grep (no
`RealEstateLead` import in either file, only `RealEstateLeadDraft`/
`RealEstateLeadDraftEvent`).

## Capability overlap classification
**DISTINCT_MODEL_DISTINCT_CAPABILITY** — `real_estate_lead` handles
pre-confirmation customer *intake* (starting a draft, answering
requirement questions, selecting a tenant/agent, submitting); no route
here performs the post-confirmation lead-execution lifecycle
(accept/reject/contact/qualify/convert/close-lost) that
`execution.real_estate_router` implements. There is zero overlapping
capability to compare strength against.

## Authorization pattern (documented, not modified)
`real_estate_lead.customer_router`'s 11 endpoints do not use FastAPI
`Depends()` for authentication at all — they call `get_current_user(r)`
directly inside the function body (an unusual pattern, distinct from
every other router in this codebase, which uses `Depends(get_current_user)`).
This is **not modified this slice** — it operates on `RealEstateLeadDraft`
only, has zero capability overlap with the security boundary this slice
(and Slice 2F-11) closed, and the module has its own dedicated, currently
passing test suite (`tests/test_sprint18_real_estate_lead.py`, 76 tests,
re-run this slice with no failures). Per the mission's explicit
constraint, a modification here is permitted only when it "bypasses the
newly approved security boundary" — since there is no overlapping
capability, no such bypass exists.

## Admin router
Already `require_super_admin`-gated throughout (all 10 routes) — a
platform-only surface, correctly stronger than any tenant-facing
concern.

## Final disposition
`DISTINCT_MODEL_DISTINCT_CAPABILITY` — `real_estate_lead` is
**REQUIRES_FUTURE_DEDICATED_SLICE** if its own authorization pattern is
ever to be independently audited/hardened; that is explicitly out of
scope for this narrow follow-up ("do not implement
app.engines.real_estate_lead as a new workstream").
