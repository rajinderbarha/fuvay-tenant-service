# Decision 10.1 — Business Onboarding and Approval: Final Contract

## Canonical records
`Tenant`, `TenantOnboardingRequest` (tenant_engine.models). No competing implementation found.

## Canonical endpoints
- Signup: `POST /v1/tenants/onboarding/signup` (public)
- Admin review/approve/reject/request-changes: `/v1/admin/tenants/*` and/or `/v1/tenants/*` — **implementation review required** to pick one of the two currently-duplicate surfaces as canonical before Phase 2 (see page-consolidation-plan.md, Business Approval Workspace).
- Self-service profile/docs/services setup: `/v1/tenant/*` (portal_router)

## Role ownership
- tenant_owner: submission, profile completion, resubmission after request-changes.
- super_admin (or admin_operations once wiring is extended): review, approve, reject, request-changes, activate, suspend, reactivate, terminate.

## Entry routes
- Provider: `/onboarding` → `/onboarding-status` → Setup Wizard (see provider-setup-final-contract.md) → `/profile`, `/documents`.
- Admin: Business Approval Workspace (consolidated route TBD from the two current pages).

## Step sequence (provider side)
1. Business information, 2. Address/region, 3. Owner/manager details, 4. Documents, 5-8. Services/pricing/coverage/team (handed off to Provider Setup workflow), 9. Package, 10. Security deposit (BLOCKED, see backend-blockers.md), 11. Review & submit.

## Status transitions
`pending_review → verified → active → (suspended ↔ active) → archived`, with `rejected` and `request_changes → pending_review` loop. Exact field-level gating rules for each transition remain UNVERIFIED (not traced to service-layer code in this pass) — recommend confirming during Phase 2 kickoff, not blocking nav/workspace scaffolding.

## Available actions (admin approval workspace)
Approve, Request Changes, Reject — each permission-filtered (`require_permission` once admin_operations wiring is extended per Phase 1 architectural gap; today effectively `require_super_admin` only).

## Error recovery
Request Changes returns tenant to `pending_review` with feedback attached (via `TenantAuditLog` history) rather than requiring full resubmission from scratch.

## Notifications / audit
SOURCE_INFERRED notification wiring on submit/approve/reject (following the established L5 pattern); `TenantAuditLog` with `actor_role` snapshot is confirmed (SOURCE_VERIFIED).

## My Work integration
Item type: business_verification_pending (super_admin), business_changes_requested (tenant_owner). Per my-work-contract.md schema.

## Next-action behavior
Per next-action-contract.md "Business onboarding" and "Business approval" sections.

## Backend blockers
1. Two duplicate admin review surfaces need reconciliation to one canonical route (not a backend code change — a frontend routing decision, but requires confirming which backend surface each currently calls).
2. Security deposit step 10 is blocked pending resolution of the 410'd legacy endpoints (see backend-blockers.md).
3. Exact status-transition gating rules unverified — low risk to proceed, but should be confirmed before building strict frontend validation.

## Frontend limitations for Phase 2
Ship the Business Approval Workspace against whichever of the two existing admin pages is confirmed to be the actively-used one; do not build a third parallel implementation.

## Acceptance criteria
- One canonical Business Approval Workspace exists (old duplicate route redirects, does not disappear).
- Approve/Reject/Request-Changes all function against real `Tenant` status transitions.
- Workspace shows profile/document/service/pricing/coverage/team/package readiness pulled from real data, with Security Deposit readiness explicitly marked "temporarily unavailable" if step 10's blocker is unresolved at ship time.
- My Work surfaces pending approvals for super_admin and pending changes-requested for tenant_owner.
