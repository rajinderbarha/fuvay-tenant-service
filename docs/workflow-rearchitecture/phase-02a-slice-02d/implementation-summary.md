# Phase 2A Slice 2D — Implementation Summary

## Outcome in one sentence
The tenant access model was investigated to the point of a conclusive architectural finding — `StaffPermission` per-user overrides are schema-complete but never wired into request-time authorization, and the read-only mutation guard is only wired into 2 of ~16 tenant routers — which correctly forecloses "manager" and "read-only" personas as safe representations today. Given that evidence, **one of the two affected accounts was safely remediated this slice** (disabled, not granted unproven access); the other remains genuinely blocked pending a real architecture decision.

## Workstream 1 — Tenant access model (the central finding)
Traced the full authorization stack: `ROLE_PERMISSIONS` (flat per-role bundles) → `PermissionChecker.has()` (role bundle + optional per-user `overrides` dict) → `require_permission`/`require_tenant_mutation_permission` (route dependencies) → `get_current_user` (builds `UserContext` entirely from JWT claims, no DB query).

**Critical finding:** `UserContext.permission_overrides` is declared, consulted by `PermissionChecker.has()` when populated, and backed by a real, schema-complete `StaffPermission` table (tenant-scoped, supports both grants and explicit denials) — but **zero code anywhere ever populates it**. `get_current_user` builds `UserContext` purely from JWT payload fields, none of which include per-user overrides. This means the architecture's own documented design intent (per-user staff permission grants) has never been wired into a live request. Confirmed by reading `get_current_user`'s full source and grepping the entire `app/` tree for any assignment to `permission_overrides` — none exists.

**Second finding:** `require_tenant_mutation_permission` (the access_scope-based mutation-denial guard) is real and correctly designed, but is called from only **2 files** across the ~16 tenant-facing router files in the codebase. A "genuinely read-only" persona relying on this guard would be read-only only on those 2 engines and fully mutation-capable everywhere else.

Full persona-by-persona model in `tenant-access-model.md`.

## Workstream 2 — Manager persona decision
**REPRESENT_AS_STAFF_PERMISSIONS is the architecturally correct target — but BLOCKED** until the override-wiring gap above is closed. Not `NEW_ROLE_ARCHITECTURE_REQUIRED` (no new role needed, the mechanism already exists in schema) and not `PRODUCT_DECISION_REQUIRED` (intent is already clear from code comments — this is an engineering completion gap, not an ambiguous product question). See `manager-persona-decision.md`.

## Workstream 3 — Tenant read-only decision
**EXISTING_ARCHITECTURE_CANNOT_ENFORCE_READ_ONLY comprehensively today.** The mechanism (`access_scope` + `require_tenant_mutation_permission`) is real where applied, but its 2-of-16 coverage means it cannot be trusted as a platform-wide guarantee. See `tenant-readonly-decision.md`.

## Workstream 6/7 — Account dispositions and remediation (executed, not just planned)
- **manager@demo-ac-services.local**: zero logins, zero sessions, zero audit activity ever — no active use to protect. Disposition: `DISABLE_DEMO_ACCOUNT`. **Executed this slice** via the (extended) remediation script: role corrected to `staff` (a required canonical placeholder, not a capability grant — the account is deactivated), `is_active=false`, `deactivated_at`/`deactivation_reason` recorded, 0 sessions to revoke (none existed), 1 `auth_audit_logs` row created. Verified live: role distribution now shows zero `tenant_manager` rows.
- **readonly@demo-ac-services.local**: 7 real logins, 7 unrevoked sessions — real usage. Disposition: `MANUAL_CONFIRMATION_REQUIRED` / `RETAIN_BLOCKED_PENDING_PRODUCT_DECISION`. **Not touched** — no safe mapping exists (mapping to `staff` would grant real mutation capability, violating "read only"; no other canonical role fits). See `affected-account-final-disposition.md`.

## Workstream 5 — Seed script hardening (executed)
`scripts/canonical_seed_final_l5_01.py`:
1. Added a `CANONICAL_ROLES` guard inside `get_or_create_user()` that raises `ValueError` before any database call if the role isn't one of the 10 canonical values.
2. Removed the `manager@`/`readonly@` demo-persona creation entirely (per Workstream 5's explicit instruction: "read-only demo users must not be created until the access model is proven") — replaced with a plain `staff@demo-ac-services.local` account representing what `staff` actually grants today.
3. Fixed a related, previously-undiscovered instance of the *same* bug class: this script still seeded 3 admin demo accounts with `role="super_admin"` (relying on a separate follow-up script, `seed_admin_roles_final_l5_05l.py`, to fix it after the fact). Now seeds `admin_operations`/`admin_finance`/`admin_readonly`/`admin_security` directly.

## Workstream 9 — Migration 144
**Still not applied — correctly.** After remediating `manager@`, ran `alembic upgrade head` live: it now aborts naming only the one remaining account (`readonly@demo-ac-services.local`), confirming the migration's detection logic correctly narrows as accounts are resolved. Database remains at revision 143.

## Workstream 10 — Integrity guard
New standalone script `scripts/workflow_rearchitecture/check_role_integrity.py` — read-only, prints only a count by default (account emails only shown with an explicit `--detail` opt-in), exit code 1 if any invalid role exists (CI/cron-friendly). Deliberately **not** wired into application startup (see `integrity-guard-decision.md` for why).

## Workstream 11 — Intelligence KB field
Added an in-code docstring/comment on the `allowed_roles_json` model column making its DISPLAY_ONLY status unmissable to any future developer, plus a regression test proving no authorization code path consults it. Database field itself not renamed (compatibility risk not fully assessed this slice, per the brief's own caution).

## Non-negotiable rules compliance
No new RBAC role added. No `tenant_manager`/`tenant_readonly` mapped to `staff` as a live capability grant (the one `staff` mapping applied was to a *disabled* account, explicitly documented as not a capability grant). `admin_readonly` never used for a tenant account. No convenience grants of `tenant_owner`/`super_admin`. The actively-used account was not silently disabled. Migration 144 not applied while an invalid record remains. All changes transactional, audited, reversible (rollback = re-run script with old role + `is_active=true`, or restore from the audit log's recorded previous state). Booking/job pipelines and UI untouched. All prior regression tests pass (278/278 total, up from 260).
