# Phase 2 Scope Lock

## In scope
1. Navigation and route reconciliation (fix super-admin nav/route drift — ~10 orphaned pages re-added to sidebar; retire ~8 confirmed-duplicate nav entries in tenant-portal).
2. Role-specific navigation per `final-role-navigation-matrix.csv` for all 10 roles' rendered shells (super_admin, admin_operations/finance/security/readonly reuse the same shell permission-filtered, tenant_owner, staff, technician, customer).
3. My Work foundation: one new aggregation endpoint per role family + one rendered queue page per app, per `my-work-contract.md`.
4. Next-action presentation: surfaced on every detail page listed in `next-action-contract.md`'s 10 domains, using the contract's response shape.
5. Business Onboarding and Approval reference workflow: consolidated approval workspace, wizard-style provider submission flow, per `business-onboarding-final-contract.md`.
6. Provider Service and Pricing Setup reference workflow: guided 12-step wizard wrapping existing pages, per `provider-setup-final-contract.md`.
7. Existing-page consolidation per `page-consolidation-plan.md` and `final-page-disposition-matrix.csv` (tabs, drawers, merges — no backend change).
8. Advanced-page relocation (Level 3 disclosure) per the ADVANCED_SETTINGS dispositions in the final page matrix.
9. Removal of non-canonical UI entry points that are confirmed dead or duplicate with zero remaining value (e.g. retired nav entries for `/provider/reviews`, `/provider/marketing`, `/provider/chat`, `/staff/home-services/jobs`).

## Conditionally in scope
10. Booking Exception Resolution reference workflow — **only proceeds once Decision 1 (booking/job canonical pipeline) is closed** per `booking-job-canonical-decision.md`. If unresolved at Phase 2 start, this item moves to Phase 3 and Phase 2 ships items 1-9 only.

## Explicitly out of scope for Phase 2
- Any visual/design-system change (colors, typography, spacing, components, themes).
- Any new business logic beyond the read-only aggregation endpoints (My Work, setup-progress, approval-summary, job-360, finance-risk-summary).
- Parts Request/Approval UI (no backend entity — see `quote-parts-scope-decision.md`).
- Backend consolidation of the duplicate engines (setup-templates, customer-flow, chat, finance-prefix collisions) beyond what's needed to pick one canonical read path per capability — full backend engine retirement is a separate backend workstream, tracked in `backend-blockers.md`, not a Phase 2 frontend deliverable.
- Mobile customer-app legacy 19-screen stack consolidation.
- Mobile staff-app feature-parity build-out (skills/service-areas/availability/documents/sessions) — tracked as a backlog item, not blocking Phase 2's web-first delivery.
- (Security deposit workflow is RESOLVED, not blocked — verification confirmed `finance_hub`'s `/v1/admin/finance/deposits*` is the live canonical replacement. Deposits tab ships normally in Phase 2 Finance Home.)

## Reuse constraint
Phase 2 reuses the existing component/design system unchanged. No new design language, no new visual patterns beyond the 10 Standard Workspace Patterns already defined in Phase 1.
