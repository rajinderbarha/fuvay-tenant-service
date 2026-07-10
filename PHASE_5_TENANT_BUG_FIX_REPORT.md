# Phase 5 — Tenant Onboarding Bug Fix Report

## Bugs found and fixed

1. **CRITICAL: Approve/Reject were completely broken for every tenant, via
   a wrong class name import.** `provider_portal/admin_router.py`'s
   `approve_provider_onboarding` and `reject_provider_onboarding` — the
   exact endpoints the Tenant 360 frontend's Approve/Reject buttons call —
   did `from app.engines.tenant_engine.admin_service import
   TenantAdminService`, but the real class is named `AdminTenantService`.
   Every single approve/reject click from the admin UI would have raised an
   `ImportError` and returned a `500`. Fixed both imports; live-confirmed
   approve and reject both now succeed with real state transitions.

2. **Missing authentication/authorization on approve/reject/request-changes.**
   All three endpoints used `Depends(get_current_user)` — any authenticated
   user, not `require_super_admin` — a real authorization hole on the exact
   endpoints that approve a business and issue 1000 real usage credits.
   Fixed to `require_permission(P.TENANT_APPROVE)` /
   `P.TENANT_REJECT` / `P.TENANT_REQUEST_MORE_INFO` (new permission
   constants added this sprint). Live-confirmed: a `tenant_owner` token
   (zero `tenants.*` permissions) now gets a real `403` on both the list
   and the approve endpoint.

3. **Reject silently accepted an empty reason.** No validation existed —
   `reject_verification(tenant_id, reason=payload.get("reason", ""))` would
   happily persist a blank reason. Added an explicit `422` check
   (`if not payload.get("reason"): raise HTTPException(422, ...)`).
   Live-confirmed: reject without a reason now returns `422`.

4. **CRITICAL: Package activation on approval silently failed for every
   tenant, via a query filter on a column that doesn't exist.**
   `activate_tenant_package_assignment`, `reject_tenant_package_assignment`,
   and `get_package_assignment_summary` (all in `package_commerce/service.py`)
   filtered on `TenantPackageAssignment.deleted_at.is_(None)` — but
   `TenantPackageAssignment` has no `deleted_at` column (unlike its sibling
   models `ServicePackage`/`PackageFeature`/`PackageLimit`, which do declare
   one). Every call raised `AttributeError: type object
   'TenantPackageAssignment' has no attribute 'deleted_at'`. Because
   `verify_tenant` wraps the activation call in a bare `try/except` that
   only logs a warning, **this failure was completely silent** — the tenant
   would show as "approved" while the package silently never activated and
   no credits were ever issued, with zero user-visible error. Removed the
   3 erroneous filter clauses. Live-confirmed: package assignment now
   correctly transitions to `status=active` with `starts_at`/`activated_at`
   set, and the wallet is credited.

5. **`request_id` was a hardcoded placeholder across the entire
   `provider_portal` router** (same class of bug fixed in
   `package_commerce` during Phase 4) — 22 occurrences of
   `request.headers.get("X-Request-ID", "—")`, never the real
   middleware-generated ID. Fixed all 22 to read
   `request.state.request_id` first. Live-confirmed real `req_xxxx` IDs now
   appear on every response from this router, including the queue list,
   detail, approve, and reject endpoints.

6. **Stale/inconsistent seed data**: the Demo AC Services
   `TenantPackageAssignment` row had `status="pending_approval"` — a
   literal string that does not exist anywhere else in the codebase's real
   status vocabulary (`"paid_pending_approval"` is the actual, consistently
   used value for a paid-and-awaiting-approval assignment). This alone
   would have caused `activate_tenant_package_assignment`'s status filter
   to never match this row, meaning approval would silently skip
   activation even after bug #4 was fixed. Corrected the fixture's status
   to `"paid_pending_approval"`.

7. **Stale/inconsistent seed data (second instance)**: the same assignment
   row had `included_spendable_credits = 0.00`, even though the real
   package (`Starter Home Services`) has `included_credit_amount = 1000`.
   The actual assignment-creation code (`create_package_assignment`)
   correctly snapshots this value at selection time — this specific row
   predates that snapshot or was seeded before the 1000-credit package
   config existed. Corrected the fixture's `included_spendable_credits` to
   `1000.00` to match the real package. Live-confirmed: after this fix (and
   #6), a full approve cycle correctly issued exactly 1000 credits.

## End-to-end proof (after all fixes, real backend + real Postgres)

```
Reset to baseline: tenant pending_setup/pending, wallet=0, assignment=paid_pending_approval
→ POST approve → tenant active/approved (real request_id)
→ wallet balance: 0 → 1000 (real package_activation ledger entry)
→ re-POST approve → 422 (idempotent, wallet still 1000, not 2000)
→ POST reject (no reason) → 422
→ POST reject (with reason) → tenant rejected (wallet unaffected, still 1000)
→ cleanup: wallet debited back to 0, tenant reset to pending_setup/pending
  (documented "Phase 5 certification test cleanup" reason on the ledger entry)
```

Final restored state matches the ticket's exact baseline scenario.

## Bugs found, not fixed (documented as blockers, correctly out of scope)

- **No dedicated backend "approval readiness gate" engine exists.** The
  closest things are (a) a frontend-only, client-computed checklist on the
  Tenant 360 Overview tab, and (b) a naive 5-field-weighted
  `profile_completion_percentage` SQL calculation enforced as a hard gate
  on approve (must be ≥100%). This does *not* check documents verified,
  security deposit received, service areas configured, or staff configured
  — only business_name/vertical/city/phone-or-email/owner_user_id. Building
  a proper multi-gate readiness engine (Module 11's full spec) is a
  genuine, non-trivial feature addition, not a "fix the bug" task — flagged
  here rather than fabricated as complete.
- **`request_changes_provider_onboarding` previously used raw SQL bypassing
  `AdminTenantService.request_changes` entirely** (diverging from the
  approve/reject endpoints, which do delegate). Fixed this sprint to
  delegate consistently — but the underlying question of whether
  `request_changes` should also affect approval readiness/gates was not
  further investigated (no gate engine exists to affect, per the point
  above).
- **`activate_tenant` (`tenant_engine/admin_router.py`, the simpler
  `/activate` endpoint)** bypasses `verification_status` and package
  activation entirely — a separate, dumber lifecycle entrypoint that
  duplicates part of `verify_tenant`'s job. Not consolidated this sprint
  (deciding which is canonical is a design decision, not a bug fix).
