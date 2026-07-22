# Workflow Implementation Roadmap (post-approval)

Not authorized to start yet — sequencing recommendation only, pending review-gate sign-off.

## Step 0 — Decisions required from stakeholders (no code)
- Pick canonical booking/job model disposition (confirm zero callers of legacy Booking/field_ops Job, or plan their migration).
- Pick canonical chat engine.
- Pick canonical review stack confirmation for `/admin/reviews`.
- Resolve setup-templates and customer-flow engine duplication.
- Confirm security-deposit canonical replacement.

## Step 1 — Zero-risk cleanup (backend, no frontend change)
- Delete dead `brands/admin_router.py`, `brands/provider_router.py` (never mounted).
- Fix super-admin nav/route drift (~10 pages) — pure frontend nav-config change, no backend touch.

## Step 2 — Aggregation endpoints (backend, additive only)
Build the 5 endpoints in `aggregation-endpoint-recommendations.md`, gated behind existing auth/scope services.

## Step 3 — My Work + Home
Ship My Work queue per role (`my-work-architecture.md`) using Step 2's endpoint. Highest user-visible impact per unit of work — directly answers "what requires attention."

## Step 4 — Simplified navigation
Apply `simplified-information-architecture.md` groupings; apply `page-disposition-matrix.csv` MERGE/MOVE_TO_TAB decisions for pages with no backend dependency (duplicate nav entries, finance page consolidation, insights page merge).

## Step 5 — Guided workflows
Business Onboarding wizard shell (Reference Workflow 1) and Provider Service & Pricing Setup wizard (Reference Workflow 2) — both wrap existing pages/APIs, no new backend logic beyond Step 2's progress-aggregation endpoint.

## Step 6 — Booking Exception Resolution workspace
Only after Step 0's booking/job model decision is finalized. Highest-value workspace but also highest-risk if built on the wrong record.

## Step 7 — Deferred/blocked items
Parts Request entity (needs backend design work, out of scope for pure workflow simplification), mobile staff-app parity, legacy customer-app screen consolidation.

## Explicit non-goals for this roadmap
No visual/design-system changes at any step. No backend business-logic changes beyond the additive read-only aggregation endpoints in Step 2.
