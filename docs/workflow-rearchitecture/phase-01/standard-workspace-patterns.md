# Standard Workspace Patterns

Ten reusable patterns. Every operational workspace answers: what record, what status, what happened, what's missing, what's blocking, who's responsible, recommended action, allowed actions, what happens after, how to recover from failure.

1. **Role dashboard** (Home) — status snapshot + shortcuts. Existing: `/admin/dashboard`, `/dashboard`, `/staff/dashboard`, mobile Home.
2. **My Work queue** — see `my-work-architecture.md`. New pattern, not yet built anywhere.
3. **List page** — filterable record list with status badges and a primary action per row. Existing pattern already used everywhere (tenants, jobs, complaints lists).
4. **360-degree detail page** — single record, all related data in tabs (Level 2 disclosure). Closest existing example: Tenant 360 view in super-admin (ADMIN_TENANT_E2E_05_TENANT_DETAIL_360_REPORT.md confirms this pattern already exists for tenants) — extend the same pattern to ServiceJob and Complaint detail pages.
5. **Guided setup wizard** — linear multi-step flow with save-as-draft. New pattern needed for Provider Service & Pricing Setup (currently 5 disconnected pages) and Business Onboarding (currently exists as separate steps without a unifying wizard shell).
6. **Approval workspace** — summary + readiness checklist + approve/request-changes/reject actions + history. New pattern needed for Business Onboarding Approval (currently split across 2 duplicate pages).
7. **Exception-resolution workspace** — see `booking-exception-resolution-workflow.md`. New pattern, does not exist today (booking exceptions are currently only visible as raw list rows, no dedicated resolution UI confirmed).
8. **Case-resolution workspace** — closest existing example: Complaint detail flow (propose/resolve/reject, L5-24 notify wired). Reuse this shape for the exception-resolution workspace above.
9. **Advanced settings** — Level 3 disclosure area for raw IDs, permission internals, deprecated-endpoint banners, engine toggles. Existing candidates: `/admin/engines`, `/admin/security`, staff `/staff/security/sessions`.
10. **Audit timeline** — chronological event list tied to a record. Existing: `AuthAuditLog`/`TenantAuditLog` tables + `/admin/audit-logs` page; needs a per-record embedded version (Level 2 tab) rather than only a standalone global log page.

## Progressive disclosure levels (applies to all patterns above)
- **Level 1 (default):** summary, status, risk, missing requirements, responsible party, recommended action, primary actions only.
- **Level 2 (tabs/drawers):** related records, services, team, pricing, documents, communication, finance, history.
- **Level 3 (advanced, opt-in):** raw audit events, internal IDs, permission/engine internals, diagnostics, deprecated-endpoint status. Never shown by default — this is where the legacy-engine complexity documented in `canonical-pipeline-report.md` gets hidden from normal operators without deleting anything.
