# Alternate Customer Complaint Route Audit — Slice 2F-10 (Workstream 14)

## Method
Searched `complaints.provider_router`, `complaints.admin_router`,
`customer_credits`, `package_commerce`, `finance_hub`, `rework`/`refund`
service files, `customer_reviews`, booking/ServiceJob routers, and any
legacy dispute router for a capability equivalent to any
`customer_router` mutation.

## Findings

| Customer capability | Alternate route found | Disposition |
|---|---|---|
| Create complaint | none — `complaints.provider_router`/`admin_router` have no complaint-creation endpoint of any kind | CANONICAL_CUSTOMER_COMPLAINT_WRITE |
| Accept/reject resolution | none — resolution *creation* is provider-only (`provider_offer_resolution`); decision is customer-only | CANONICAL_CUSTOMER_DECISION |
| Settlement accept/reject | `complaints.provider_router`'s `respond_to_settlement` is the provider-side twin, structurally distinct persona, own ownership checks (Slice 2F-9-closed) | CANONICAL_CUSTOMER_DECISION (customer side) / CANONICAL_PROVIDER_COMPLAINT_WRITE (provider side) — not a weaker alternate, a different actor on the same shared, cross-checked `_get_settlement_proposal` |
| Refund request | `provider_review_refund` (provider_router) is a distinct capability — *reviewing*, not *requesting* — not an alternate path to the same mutation | DISTINCT_CAPABILITY |
| Rework | No standalone customer rework route exists at all (see `rework-refund-boundary.md`); provider-side schedule/start/complete are distinct capabilities, not alternates | DISTINCT_CAPABILITY |
| Complaint ratings | `customer_reviews` engine (Sprint 24, closed in Slice L5-13) is a wholly separate review system, not a complaint-resolution rating — confirmed distinct model/table, not touched | DISCONNECTED (by design, not a gap) |
| Complaint administration | `complaints.admin_router`, confirmed `require_super_admin`-gated throughout (re-verified via Slice 2F-9's finding, unmodified) | CANONICAL_PLATFORM_ADJUDICATION |

## No weaker live customer-facing route found
Every genuine customer complaint capability has exactly one route
(`customer_router`) reaching it; no alternate, legacy, or
compatibility-shim route was found that reaches the same service method
with weaker checks. This satisfies the mission's requirement that "a
weaker live customer-facing route must be fixed or block approval" — none
exists to fix.
