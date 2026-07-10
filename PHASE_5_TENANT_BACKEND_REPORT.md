# Phase 5 — Tenant Onboarding & Approval Backend Report

## Architecture note (read first)

Like Phase 4, this is **not greenfield**. A full research pass confirmed
tenant onboarding/approval is ~95% built across three overlapping systems:
`tenant_engine` (the core Tenant model + lifecycle service,
`AdminTenantService`), `provider_portal` (a "New Business Requests"/
onboarding-queue wrapper that delegates into `tenant_engine`), and
`package_commerce` (package assignment activation + wallet crediting on
approval). The actual approve/reject buttons on the Tenant 360 frontend page
call into `provider_portal`'s wrapper endpoints — which had a **critical,
live-breaking bug** found and fixed this sprint (see bug-fix report).

## Module 1 — Tenant Onboarding Queue

Real routes: `GET /v1/admin/onboarding/providers/summary` (new-requests
summary), `GET /v1/admin/onboarding/providers` (full queue, computes
`review_status`/`onboarding_status`/`readiness_status`/`bookable_status` per
row), `GET /v1/admin/onboarding/providers/{tenant_id}` (detail). Frontend:
`/admin/tenants/onboarding` (narrower "new requests" view,
`verification_status='not_started'` only) + the main `/admin/tenants` list
(full lifecycle table).

Confirmed live: Demo AC Services appears in the onboarding detail endpoint
with `verification_status: "pending"`, `tenant_status: "pending_setup"`,
`selected_package_name: "Starter Home Services"`,
`package_status: "paid_pending_approval"` (fixed this sprint — was a
mismatched literal, see bug-fix report), `profile_completion_percentage: 100`
(after filling a missing contact field), `bookable_status: "pending_approval"`.

## Module 2 — Tenant 360 / Application Detail

Real route: `/admin/tenants/{tenant_id}` (2932-line page, ~20 tabs). Backing
endpoints: `GET /v1/admin/tenants/{tenant_id}` (overview), plus dedicated
per-tab endpoints for staff/users/service-areas/enabled-services/pricing/
packages/wallet/deposit/audit, all already wired to real data. Approval
readiness is currently a **frontend-only, client-computed checklist**
(Overview tab) — no dedicated backend `/approval-readiness` gate endpoint
exists (see Remaining Blockers).

## Modules 6/7 — Package Selection Review & Security Deposit Gate

Confirmed live and pre-existing: `TenantPackageAssignment` model correctly
encodes "package inactive, no credits, until approval" via its status
lifecycle and `starts_at`/`activated_at` nullability. `SecurityDeposit` is a
fully separate table/model — structurally impossible to mix with wallet
credits (confirmed no shared columns, no shared write path).

## Modules 12/13 — Approval Workflow & Bookability

**This is where the critical bugs lived — see `PHASE_5_TENANT_BUG_FIX_REPORT.md`
for full detail.** Summary of the live-verified, now-working end-to-end flow:

1. Pre-approval: tenant `status=pending_setup`, `verification_status=pending`,
   wallet balance `0`, assignment `status=paid_pending_approval`.
2. `POST /v1/admin/onboarding/providers/{id}/approve` → tenant
   `status=active`, `verification_status=approved`.
3. Package assignment activates: `status=active`, `starts_at`/`activated_at`
   set to now.
4. Wallet credited exactly `1000` (the package's `included_credit_amount`),
   with a real `package_activation` ledger entry
   (`balance_before:0, balance_after:1000`).
5. Re-running approve on an already-approved tenant → `422
   TENANT_VERIFICATION_INVALID_STATUS`, wallet balance unchanged (still
   `1000`, not `2000`) — idempotency confirmed at both the tenant-status gate
   level and the ledger's own `idempotency_key`.
6. `POST .../reject` without a `reason` → `422` (fixed this sprint — reason
   was not previously validated at all in this wrapper endpoint). With a
   reason → tenant `status=rejected`, `verification_status=rejected`, wallet
   balance unaffected.

Bookability is computed inline (`"bookable" if verification_status in
("approved","verified") and tenant_status=="active" else "pending_approval"`)
— confirmed correctly `"pending_approval"` before approval.

## Result: **Backend certified after fixing 4 critical/high-severity bugs** (detailed in `PHASE_5_TENANT_BUG_FIX_REPORT.md`). The core approve→activate→credit→ledger→audit chain is live-verified working end-to-end, idempotent, and correctly separates security deposit from usage credits.
