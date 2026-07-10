# Phase 3 — Pricing & Rules Remaining Blockers

None of these are hard-gate failures per the ticket's own rules (backend,
frontend, and integration all pass; audit logs work). The only blocker
affecting the final recommendation is the environment's lack of browser
automation tooling.

1. **No true interactive browser session was ever launched** — same
   environment constraint as every prior sprint this session. Steps 34-35
   of the manual smoke script (console errors, visual NaN/undefined check)
   remain unverified. This is the sole reason the final recommendation
   cannot be the unqualified READY status.

2. **Bargain evaluation has no explicit ceiling behavior above max_price.**
   The ticket's Module 5 scenario table says an offer of ₹1300 (above
   max_price 1200) should be "rejected or normalized... depending on
   policy" — this implementation currently accepts any offer at or above
   the floor with no upper bound check. Not a hard-gate violation (the
   ticket explicitly allows either behavior), but worth a product decision
   in a future sprint on whether bargain offers should also be capped by
   `max_price`.

3. **Audit trail for new pricing modules isn't surfaced in the dedicated
   `/admin/audit-logs` UI page.** The mutations are genuinely recorded
   (`master_data_audit_log`, confirmed live), but that specific frontend
   page's 3 tabs (Engine/Security/Auth Audit) read from different,
   separate audit tables — the same "3 parallel audit systems" fragmentation
   flagged in Phase 1B. Data integrity is not at risk; discoverability via
   that one UI page is limited. A future audit-consolidation sprint should
   address this platform-wide, not just for pricing.

4. **Small/Large pricing tier multipliers are placeholder values**
   (0.85/1.2), not a finalized business decision — seeded this sprint
   purely to satisfy the Module 1 hard gate's existence check. Product/
   finance should review and adjust these before they're used in any real
   pricing calculation.

5. **Cross-vertical "Pricing Tiers" catalog module injection** for
   Coaching/Real Estate/Beauty/Restaurant/Product Marketplace/Professional
   Services (each shows it in their own vertical's sidebar section) is
   pre-existing Phase 2 behavior, not addressed this sprint — the ticket's
   hard gate is scoped to Home Services specifically, which is correct.
   Worth revisiting if the "Pricing is a global engine, never a vertical
   submenu" principle should apply to all verticals, not just Home
   Services.

6. **Provider override tenant-scoping is enforced by the `tenant_id`
   column and query filters, not by row-level security or a service-layer
   ownership check tied to the acting admin's own tenant context** (this
   is an *admin*-facing CRUD surface, so cross-tenant visibility is
   intentional for Super Admin — but if a future "tenant-portal-facing"
   version of this API is built, it will need real tenant-scoping
   enforcement, not just a filterable column).
