# Aggregation (Backend-for-Frontend) Endpoint Recommendations

All proposed endpoints are **read-only aggregations** of existing data — no new business logic, no new writes. Not implemented in this phase.

## 1. `GET /v1/{role}/my-work`
- **Role:** super_admin, tenant_owner, staff, technician, customer (one implementation, role-scoped by existing auth dependency).
- **Aggregates:** `Tenant.status`, `ServiceJob.status` + SLA fields, `Complaint.status` + SLA loop state, `quote_checklist` pending items, `UsageCreditLedger` low-balance flag.
- **Response sections:** urgent[], requires_action[], waiting[], scheduled[], recently_completed[], escalated[], failed[] — each item matching the schema in `my-work-architecture.md`.
- **Permissions:** reuses existing `require_permission`/scope services per record type — no new permission model needed.
- **Tenant scoping:** existing `TenantScopeService`/`StaffScopeService`/`CustomerScopeService`, unchanged.
- **Partial-data handling:** if one source query fails, return partial results with a `sections_unavailable` array rather than 500ing the whole page.
- **Pagination:** cap each section at N=20 with a "view all" link to the underlying list page.
- **Caching:** short TTL (30-60s) acceptable given this is a queue, not a ledger of record.
- **Why it reduces complexity:** today there is no single queue; users must check 5-10 separate pages to find what needs attention.

## 2. `GET /v1/admin/businesses/{tenant_id}/approval-summary`
- **Role:** super_admin.
- **Aggregates:** Tenant profile completeness, document status, service/pricing/coverage/team readiness flags, package status, security-deposit status (pending blocker resolution), prior review history from `TenantAuditLog`.
- **Why:** replaces the two current duplicate onboarding-review pages with one data source; feeds the Business Approval workspace (Reference Workflow 1).

## 3. `GET /v1/tenant/setup-progress`
- **Role:** tenant_owner.
- **Aggregates:** completion status of each of the 12 Provider Service & Pricing Setup steps (categories, services, pricing, brands, areas, availability, publish-readiness).
- **Why:** feeds the guided wizard's progress indicator without the frontend having to independently call 6+ engines and infer completeness client-side.

## 4. `GET /v1/{role}/service-jobs/{id}/360`
- **Role:** super_admin, tenant_owner, staff, technician, customer (permission-scoped).
- **Aggregates:** ServiceJob + assignment + quote_checklist + invoice_payment + usage_credit_deduction + customer_reviews entry, all keyed by job id.
- **Why:** feeds the Booking Exception Resolution workspace's 360-degree job view without stitching together 5 separate API calls per page load; also the natural place to surface a "which chat engine has this thread" pointer once the chat-canonicalization decision (gap #4) is made.

## 5. `GET /v1/admin/finance/tenant-risk-summary`
- **Role:** super_admin, admin_finance.
- **Aggregates:** low-credit tenants, pending deposit issues, overdue invoices, open dispute claims — across `usage_credits`, `package_commerce`, `invoice_payment`, `customer_credits`.
- **Why:** currently these live across ~6 separate finance pages; this powers a Finance risk panel on the admin Home dashboard.

## Explicitly not recommended
No aggregation endpoint is proposed to paper over the booking/job model split (item 1 in workflow-gaps-and-blockers.md) or the chat-engine split (item 4) — those are data-model decisions that must be resolved at the source, not hidden behind a BFF that queries three different tables and hopes they agree.
