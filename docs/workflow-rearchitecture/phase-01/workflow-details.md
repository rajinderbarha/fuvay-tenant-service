# Workflow Details

Full step-by-step detail for every workflow in `workflow-inventory.csv`, grouped by category. Format per workflow: entry point, preconditions, status before/after, branches, error/retry/cancel/escalation paths, notifications, audit events, completion state, verification.

## Business Workflows

### Business registration → activation (full chain)
- **Entry point:** Public signup form (guest) → `/v1/tenants/onboarding/signup` (or `/v1/public/*`).
- **Preconditions:** none (guest).
- **Canonical record:** `Tenant` + `TenantOnboardingRequest`.
- **Status flow:** `pending_review` → (admin: `request_changes` → `pending_review` again, or `reject` → `rejected`, or `approve` → `verified`) → `activate` → `active` → (`suspend` → `suspended` → `reactivate` → `active`) → (`terminate` → `archived`).
- **Branches:** incomplete profile blocks submission; missing documents blocks verification; missing package/security-deposit blocks activation (exact gating rules UNVERIFIED — not traced in this pass, recommend confirming against `tenant_engine/service.py` before building the approval workspace).
- **Notifications:** onboarding submitted/approved/rejected — assumed wired (not directly verified this pass; SOURCE_INFERRED).
- **Audit events:** `TenantAuditLog` entries with `actor_role` snapshot.
- **Frontend pages:** `frontend/tenant-portal` `/onboarding`, `/onboarding-status`, `/setup/checklist`; `frontend/super-admin` `/admin/tenants/onboarding`, `/admin/onboarding/providers`.
- **Verification:** SOURCE_VERIFIED (routers/models exist); end-to-end status-transition gating UNVERIFIED.

## Service Configuration Workflows

### Provider service & pricing setup (see dedicated reference doc `provider-service-pricing-workflow.md` for full detail)
Summary: category → service → pricing model → options → brands → base/range price → geo overrides → service areas → availability → review → publish. Currently spread across ~15 separate tenant-portal pages (`/tenant/setup/services`, `/provider/service-areas`, `/provider/pricing`, `/provider/service-coverage`, `/tenant/setup/availability`, etc.) rather than one guided flow. RUNTIME_VERIFIED per HS2-HS6 reports (each step individually verified); the *guided, single-flow* wrapper does not exist yet — that's the Phase 2+ opportunity.

## Team Workflows
Staff/technician invite → onboard → role/permission assign → skill/availability setup → activate. All steps exist as separate pages under Team nav; no guided wizard. SOURCE_VERIFIED per role-navigation-matrix.

## Booking and Job Workflows

### Booking creation → job completion (canonical chain)
- **Entry:** Customer app `BookingAssistant` → `BookingDraft` → media/address/serviceability → `Pricing`/`Bargain` (auto Low/Mid/High) → `BookingReview` → `BookingSuccess`.
- **Canonical record:** `ServiceBooking` + `ServiceJob`, created atomically at confirmation (`final_records/confirm_router.py`).
- **Status flow:** `draft` → `confirmed`/`matched` → `assigned` → `on_the_way` → `arrived`/`reached_site` → `inspection` → (`quote_required` if parts needed → customer approves via quote_checklist) → `in_progress`/`work_done` → `completed`.
- **Branches:** no provider match → exception workflow (see booking-exception-resolution-workflow.md); customer cancels/reschedules at any pre-completion state (delivered L5-29).
- **Notifications:** booking confirm → customer+provider (L5-27); job assign → technician (L5-25); quote actions → other party (L5-21); invoice ready → customer (L5-26); review submitted → provider, reply → customer (L5-22).
- **Audit events:** status_history table on ServiceJob.
- **Completion state:** `completed` → commission deducted exactly-once (RUNTIME_VERIFIED) → review eligible.
- **Verification:** RUNTIME_VERIFIED end to end (HS7/HS8/HS9/HS10 reports).

## Exception Workflows
See `booking-exception-resolution-workflow.md` for the full unified detail (provider not assigned, rejected, SLA risk/breach, cancellation, reschedule, rework, complaint).

## Finance Workflows
Package creation (admin) → package purchase/assignment (tenant, canonical `TenantPackageAssignment`) → security deposit (legacy endpoints 410'd; canonical replacement UNVERIFIED) → credit activation → credit top-up/manual adjustment (`usage_credits`, canonical) → commission deduction (automatic on job completion) → customer service credit (admin-issued goodwill, L5-28) → credit ledger review (both admin and tenant views, RUNTIME_VERIFIED).

## Governance Workflows
Login/MFA/session management → role/permission management (code-based, no real mutation capability yet) → account restriction → audit investigation (AuthAuditLog/TenantAuditLog) → compliance export/erasure (DPDP, `compliance` engine, RUNTIME_VERIFIED per L5-15) → security incident review (admin_security role, partially wired per canonical-role-model.md).

---
For the full API/endpoint list backing each workflow, see `api-workflow-coverage-matrix.csv`. For per-record next-action logic, see `status-next-action-registry.csv`.
