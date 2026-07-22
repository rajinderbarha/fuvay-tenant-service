# Reference Workflow 1 — Business Onboarding & Approval

## Provider-side setup (tenant_owner, guest→tenant_owner)
1. Business information — `/onboarding` (guest signup) → `/profile`
2. Address & service region — `/provider/service-areas`
3. Owner/manager details — `/profile` (staff section)
4. Verification documents — `/documents`
5. Services — `/tenant/setup/services`
6. Pricing — `/provider/pricing`
7. Service areas (coverage detail) — `/provider/service-coverage`
8. Team setup — `/provider/staff`
9. Package — `/finance/package`
10. Security deposit — `/finance/security-deposit` (BLOCKED_BY_BACKEND_GAP: underlying legacy endpoints are 410'd, canonical replacement UNVERIFIED — resolve before wiring this step)
11. Review and submission — `/onboarding-status`

All 11 steps exist today as separate pages (SOURCE_VERIFIED). Recommendation: wrap in a single guided wizard shell (Standard Pattern 5) with a persistent progress indicator — the `ONBOARDING_CHECKLIST_ITEMS` list already in `TenantLayout.tsx` is the seed for this.

## Admin approval workspace (super_admin, Standard Pattern 6)
Should include, per the spec and matched to existing data:
- Business summary — from `Tenant`
- Profile readiness — computed from profile completeness fields
- Document readiness — from documents/media
- Service readiness — from admin_catalog tenant enablement
- Pricing readiness — from pricing engine
- Coverage readiness — from TenantServiceArea
- Team readiness — from staff count
- Package status — from `TenantPackageAssignment` (canonical)
- Security-deposit status — BLOCKED_BY_BACKEND_GAP (see above)
- Risks — SOURCE_INFERRED, no dedicated risk-scoring field found for onboarding specifically (trust_quality risk scoring exists post-activation, not pre-approval)
- Requested changes / previous review history — `TenantAuditLog`
- Actions: Approve / Request Changes / Reject

**Current state:** this workspace's functionality is split across two pages — `/admin/tenants/onboarding` and `/admin/onboarding/providers` — which appear to duplicate the same underlying review capability (SOURCE_INFERRED, not confirmed which is authoritative). **Decision needed before Phase 2**: pick one as canonical, retire/redirect the other, per `page-disposition-matrix.csv`.

## Status model (SOURCE_VERIFIED at Tenant level, exact transition guards UNVERIFIED)
`pending_review → verified → active → (suspended ↔ active) → archived`, with `rejected` and a `request_changes → pending_review` loop.

## Notifications / audit
Notification wiring for onboarding submit/approve/reject was not directly re-verified in this pass (SOURCE_INFERRED it exists, following the pattern of every other L5 notify fix); recommend confirming before building the approval workspace UI copy. Audit: `TenantAuditLog` with `actor_role` snapshot (SOURCE_VERIFIED).

## Next actions after this workflow
Activation triggers Provider Service & Pricing Setup (Reference Workflow 2) if not already completed during onboarding.
