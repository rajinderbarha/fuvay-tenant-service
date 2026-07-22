# Phase 2 Implementation Order

1. **Nav/route reconciliation** (zero backend risk) — fix super-admin drift, retire confirmed duplicate nav entries. Ship first: immediate visible value, no dependency on any open decision.
2. **Aggregation endpoints** — build `/v1/{role}/my-work`, `/v1/tenant/setup-progress`, `/v1/admin/businesses/{id}/approval-summary` (read-only, additive).
3. **My Work + next-action presentation** — render the queue and the per-domain next-action panel using step 2's endpoints.
4. **Role-specific navigation shells** — apply `final-role-navigation-matrix.csv` groupings across all 5 apps.
5. **Page consolidation** (tabs/drawers/merges with no backend dependency) — Business 360, Finance Home, Reporting merge, duplicate-entry retirement.
6. **Business Onboarding & Approval workspace** — requires picking the canonical of the two existing admin review pages (implementation-time confirmation, not a new open decision).
7. **Provider Service & Pricing Setup wizard** — wraps existing pages; ship without templating if setup-template engine reconciliation isn't done yet.
8. **Advanced-page relocation** — move ADVANCED_SETTINGS-disposition pages behind their new affordance.
9. **Booking Exception Resolution workspace** — only after Decision 1 closes. If still open, this step is deferred whole to Phase 3.
10. **Cleanup pass** — confirm no visual regressions, confirm RUNTIME_VERIFIED workflows still function, confirm redirects work for every RETIRE-disposition route.

## Sequencing rationale
Steps 1-5 have zero dependency on any of the 10 decisions in this document remaining open — they can start immediately upon approval. Steps 6-7 depend only on implementation-time confirmations (which existing page is more complete), not new product decisions. Step 9 is the only step gated on an unresolved architectural decision (Decision 1), so it is deliberately last and explicitly conditional.
