# Phase 2 Acceptance Criteria

## 1. Navigation and route reconciliation
- [ ] Super-admin rendered sidebar (`AdminLayout.tsx NAV_GROUPS`) matches `lib/nav-config.ts` — zero drift.
- [ ] All ~10 previously-orphaned pages (real-estate, coaching, bookability, reports, ai, ai-chat, service-invoices, provider-wallets, commission-records, payments, financial-events) are reachable via nav or explicitly marked HIDDEN_BUT_SUPPORTED with a documented reason.
- [ ] Confirmed-duplicate nav entries removed: tenant-portal `/provider/reviews`, `/provider/marketing`, `/provider/chat`, `/staff/home-services/jobs`.

## 2. Role-specific navigation
- [ ] Each of the 10 roles sees only the nav items defined for it in `final-role-navigation-matrix.csv` — no irrelevant modules visible.
- [ ] admin_operations/finance/security/readonly see a permission-filtered subset of the super_admin shell, not a separate app (per architectural gap noted in canonical-role-model.md — do not attempt to fully close the `require_super_admin` gating gap in Phase 2, only ensure the frontend nav degrades gracefully to what each role can actually reach today).

## 3. My Work foundation
- [ ] `GET /v1/{role}/my-work` returns items matching the schema in `my-work-contract.md` for at least: business_verification_pending, quote_awaiting_decision, low_credit_balance, complaint_open, job_assigned_pending_accept.
- [ ] My Work is rendered as the second nav item (after Home) for every role.
- [ ] Every item's primary_action navigates to a real, permission-checked destination.

## 4. Next-action presentation
- [ ] Each of the 10 domains in `next-action-contract.md` shows a consistent next-action panel on its detail page, using the same field set.
- [ ] `unsupported_reason` renders as an honest "not yet available" state, never a silently-missing button, wherever a domain has a known gap (e.g. Parts).

## 5. Business Onboarding and Approval
- [ ] Duplicate admin approval pages reduced to one canonical route (old route redirects).
- [ ] Approve/Reject/Request-Changes function against real Tenant status transitions.
- [ ] Security Deposit readiness shows "temporarily unavailable" state if unresolved, not a broken page.

## 6. Provider Service and Pricing Setup
- [ ] All 12 steps reachable in sequence from one wizard entry point, each step wrapping its existing working page/API unchanged.
- [ ] Publish step reuses the existing hardened readiness gate.
- [ ] Setup-progress endpoint accurately reflects real per-step completeness (spot-checked against at least 3 test tenants in varying completion states).

## 7. Booking Exception Resolution (conditional)
- [ ] Only ships if Decision 1 is CLOSED with a single canonical record designated.
- [ ] If shipped: workspace reads/writes only the canonical record; legacy Booking/field_ops Job are not surfaced.
- [ ] If not shipped: explicitly deferred in the Phase 2 release notes, not silently dropped.

## 8. Existing-page consolidation
- [ ] Each consolidation group in `page-consolidation-plan.md` results in one navigable entry point with the constituent pages as tabs/steps, verified functionally equivalent to before (no capability regression).

## 9. Advanced-page relocation
- [ ] All ADVANCED_SETTINGS-disposition pages are reachable only via an explicit "Advanced" affordance, not primary nav.

## 10. Non-canonical UI entry-point removal
- [ ] Every RETIRE-disposition route either 301-redirects to its canonical replacement or is removed from all nav/menus while remaining in the codebase (per approved product direction #7 — code isn't deleted, just not surfaced).

## Cross-cutting
- [ ] No visual/component/styling change shipped in Phase 2 (verified via diff review — only routing, data-fetching, and content changes).
- [ ] No regression in any of the RUNTIME_VERIFIED workflows identified in Phase 1 (spot-check booking creation → completion, quote approval, complaint resolution, credit deduction).
