# MODULE-L5-01C — Final Report

## 1. Final Status

**`NOT_PROVEN_ARCHITECTURE_BLOCKER`**

Identity & Access cannot be honestly certified `IDENTITY_L5_PROVEN` against the current
architecture. The certification's own top-line acceptance criterion — "all 10 canonical
roles are runtime-classified" for the specific named set `super_admin, platform_admin,
support_admin, tenant_admin, tenant_owner, manager, staff, technician, customer, guest`
— is unsatisfiable because four of those roles (`platform_admin`, `support_admin`,
`tenant_admin`, `manager`) are **not implemented or enforced anywhere**, and three
mutually-inconsistent role registries coexist with no single source of truth. Reconciling
this — plus the absent multi-tenant-membership / tenant-switching model that Section 13.10
requires as mandatory runtime proof — is a major identity/role/permission/membership/
migration redesign that cannot be performed safely inside one sprint. This is reported as
an architecture blocker (an explicitly allowed outcome) rather than fabricating role
evidence or forcing a risky live-role migration to manufacture a green certification.

## 2. Central Finding

ServiceOS has **three competing role vocabularies**, and none of them matches the
certification's required canonical 10-role set:

| Registry (file) | Role set | Purpose |
|---|---|---|
| `app/core/permissions.py` → `ROLE_PERMISSIONS` (the **actually-enforced** set) | `super_admin, tenant_owner, staff, technician, customer, guest, admin_operations, admin_finance, admin_security, admin_readonly` | Runtime permission enforcement |
| `app/engines/auth/constants.py` → `ROLES` (+ `ROLE_HIERARCHY`, `AUDIENCE`) | `super_admin, tenant_owner, staff, customer, guest` (5 only — missing `technician` and all `admin_*`) | Token audience/hierarchy — **stale** |
| `app/engines/roles_permissions/service.py` | `super_admin, platform_admin, finance_admin, operations_admin, support_admin, compliance_officer, tenant_owner, tenant_manager, technician` | Admin role-editor display registry |

These do not even agree on naming: the enforced set uses `admin_operations`/`admin_finance`/
`admin_security`/`admin_readonly`, while the role-editor registry uses `operations_admin`/
`finance_admin`/`support_admin`/`compliance_officer`/`platform_admin`. The mission's mandatory
question "Are duplicate role or permission registries present?" answers **YES**, and Section
6's requirement of "one documented source of truth … for roles [and] permissions" is **not
met**.

Against the required canonical list:
- **Match by name:** `super_admin, tenant_owner, staff, technician, customer, guest` (6).
- **Absent / not enforced (no permission map, cannot be assigned to a user):** `platform_admin`,
  `support_admin`, `tenant_admin`, `manager` (4). The enforced set instead has four
  differently-named platform roles (`admin_operations`, `admin_finance`, `admin_security`,
  `admin_readonly`) with no analogue in the required list.

A role that cannot be assigned and has no permission map cannot be runtime-classified
(one allowed action / one denied action / tenant-boundary / lifecycle / audit) as Sections
13.14 and 32 require. This is not a workload gap — it is a definitional/architectural one.

## 3. Verified Starting Baseline

- **Expected commit:** `10d8a4f`
- **Actual starting commit:** `10d8a4f9aa653f0dcdf7b7bf7ad18bd2b72577f0` — matches.
- **Working-tree state:** clean at start (ignoring the concurrent, unrelated
  `mobile/customer-app/*`, `docs/customer-app/*`, `e2e/docs/*` changes owned by a different
  session). This sprint's only net change is this report document.
- **Branch divergence:** `0` ahead, `0` behind `origin/master`.
- **Authorization-guard starting result:** `e2e/admin_router_auth_guard.py` →
  `ADMIN_ROUTER_AUTH_GUARD_PASSED`, 0 findings. The platform-admin authorization
  vulnerability class from MODULE-L5-01B remains closed.

## 4. Scope Examined

Full factual inventory of the Identity & Access implementation (canonical models, routers,
services, tables) across `app/engines/auth/`, `app/dependencies/auth.py`,
`app/core/permissions.py`, and `app/engines/roles_permissions/`. Direct-grep verification of
the three role registries, the enforced 10-role key set, and the absence of any
tenant-membership / tenant-switch code. Ran the identity-focused test subset (168 tests) and
re-evaluated the four pre-existing version failures. This was **not** a re-run of MODULE-L5-01B's
authorization remediation (Rule: do not restart proven work without evidence of regression —
none found).

## 5. Canonical Identity Architecture

- **User/principal:** `app/engines/auth/models.py::User` (table `users`). Single row per
  principal; `role` (String(30)) and `tenant_id` (nullable UUID) live directly on the row.
  Account-state columns exist and are rich: `is_active`, `account_status`, `is_verified`,
  `is_mfa_enabled`, `mfa_required`, `locked_until`, `lock_reason`, `failed_login_attempts`,
  `deactivated_at`, `force_password_change`, `temporary_password_active`, etc.
- **Authentication:** single login code path — `app/engines/auth/router.py::login`
  (`POST /v1/auth/login`) → `AuthService.login`. No duplicated customer/tenant/platform login
  routers. (Good: no competing auth implementations — the duplication problem is in *roles*,
  not authentication.)
- **JWT:** created in `app/engines/auth/utils.py::create_access_token` (claims `sub`, `jti`,
  `iat`, `exp`, `iss="serviceos"`, `aud`, `role`, `tenant_id`, `session_id`, `device_id`,
  `mfa_enabled`, …); validated/consumed by `app/dependencies/auth.py::get_current_user`
  (Redis blacklist + per-session revocation check → `UserContext`). Confirmed canonical.

## 6. Canonical Session Architecture

`UserSession` (`user_sessions`), `RefreshToken` (`refresh_tokens`), `RefreshTokenFamily`
(`refresh_token_families`) in `app/engines/auth/models.py`. Refresh **rotation and reuse/theft
detection are genuinely implemented** (`AuthService` refresh path checks `rt.is_used`, calls
`family.invalidate("theft_detected")`, writes `AuthAuditLog "token.theft_detected"`, publishes
`auth.token_theft_detected`). Redis session-revocation keys in
`app/engines/auth/constants.py`, consumed in `get_current_user`. This layer is architecturally
sound and is **not** the blocker.

## 7. Canonical Role, Permission and Policy Architecture

`app/core/permissions.py` is the enforcement source of truth: `class P` (typed
`engine:resource:action` constants), `ROLE_PERMISSIONS` (role→grants), `PermissionChecker`
with wildcard/engine/resource resolution and per-user `StaffPermission` overrides, and FastAPI
factories `require_permission` / `require_any_permission` / `require_tenant_mutation_permission`.
**Roles are a fixed string enum on `User.role`** — there is **no per-tenant custom-role
mechanism** (`StaffPermission` provides only per-user permission *overrides*, not custom roles).
No ABAC policy registry with subject/resource/attribute/explicit-deny precedence was found;
authorization is RBAC + per-user overrides. This directly blocks Sections 7.21 (Custom Roles)
and 7.22 (ABAC), whose mandatory proofs ("prove a tenant cannot create a custom role with
platform authority", "explicit-deny respected") reference capabilities that do not exist.

## 8. Tenant Membership and Switching — ARCHITECTURAL GAP

No `TenantMembership`/`tenant_users` table exists; `User.tenant_id` is a single nullable
column (one tenant per user). No tenant-switching or principal-switching endpoint exists
(grep for `tenant_membership|switch.?tenant|switch_principal|tenant_users` → **0 files**).
Section 13.10 requires as **mandatory runtime proof**: "user with two memberships switches
tenant … suspended membership cannot be selected". This is impossible to prove — and unsafe
to infer — under a single-`tenant_id` model. Sections 7.17, 7.18, and the §11 matrix rows
`switch tenant` / `switch principal` are likewise unsatisfiable without a membership-model
redesign.

## 9. Why this is an ARCHITECTURE_BLOCKER (not workload, not requirement-absence)

To reach `IDENTITY_L5_PROVEN` as specified, the following redesign is required, and each item
is individually a "major unsafe identity/role/permission/membership/migration redesign that
cannot responsibly be completed in this sprint":

1. **Unify three role registries into one canonical set** — this changes enforced role
   strings, requires migrating the `role` value on every existing `users` row, and updating
   every `require_*`/permission consumer. Role-string changes on live enforcement are exactly
   the class of change that silently causes lockouts and privilege-escalation bugs; doing it
   under time pressure in one sprint is unsafe.
2. **Introduce the four missing named roles** (`platform_admin`, `support_admin`,
   `tenant_admin`, `manager`) with authored permission maps, or formally decide the canonical
   naming differs from the mission list — a requirement/architecture decision, not a
   mechanical fix.
3. **Add a tenant-membership schema** (new table, migration, backfill from `User.tenant_id`,
   token/`UserContext` changes) plus tenant-switching endpoints and cache-isolation — to make
   Section 13.10's mandatory multi-membership switching provable.
4. **Add custom-role and ABAC subsystems** (Sections 7.21, 7.22) that currently do not exist.

Doing any of these hastily would violate the mission's own safety constraints ("do not weaken
security controls", "unsafe to infer"). This is the textbook definition of
`NOT_PROVEN_ARCHITECTURE_BLOCKER`.

## 10–30. Domain Results (current-state, honestly scoped)

The following identity domains **are implemented and appear architecturally sound** (source-
and test-verified this sprint; full 10-role runtime matrix is blocked by §9): login (single
path), logout/revocation (Redis + session revoke), access-token validation (iss/aud/exp/jti),
refresh rotation + theft detection, password lifecycle + reset tokens (`PasswordResetToken`,
single-use), OTP (`OTPRecord`, hashed, attempt-limited), MFA (`MFASecret`/`MFABackupCode`,
TOTP + backup codes), lockout (`failed_login_attempts`/`locked_until`, thresholds in
constants), sessions/devices (`UserSession`), login history/security events (`LoginEvent`,
`AuthAuditLog`), user directory + suspension/offboarding (three route surfaces:
`admin_security_router`, `admin_customers_router`, `platform_users_router`), and genuine
impersonation (`create_impersonation_token`, `/v1/auth/impersonate`, gated by
`P.PLATFORM_IMPERSONATE`).

The following are **absent / blocked**: custom roles (§7.21), ABAC policy engine (§7.22),
tenant membership (§7.17), tenant/principal switching (§7.18), and the four unimplemented
named roles (§5). These cannot be marked "proven" and are not marked so.

Per the certification's honesty rules, I am **not** filling Sections 10–30's individual
"Result: PROVEN" fields with runtime evidence I did not produce for all 10 named roles, and
**not** producing a 40-layer matrix or role×capability matrix with inferred values — the
mission explicitly forbids inferred values, and the blocked role/membership architecture means
those matrices cannot honestly reach `unknown = 0`.

## 31. 40-Layer Matrix Result

Not produced with completed values. Producing it honestly requires the §9 redesign
(all-10-role classification + membership model). A matrix built now would contain inferred /
`unknown` / `not-implemented` cells for the four absent roles, custom-roles, ABAC, membership,
and tenant-switching layers — violating the "unknown must equal zero" gate. Reported as
**blocked**, not fabricated.

## 32. Role Coverage Result

- **Runtime-classifiable (implemented, enforced):** `super_admin`, `tenant_owner`, `staff`,
  `technician`, `customer`, `guest` — plus the enforced platform roles `admin_operations`,
  `admin_finance`, `admin_security`, `admin_readonly`.
- **Not classifiable (do not exist / not enforced):** `platform_admin`, `support_admin`,
  `tenant_admin`, `manager`.

Because the required canonical set and the enforced set overlap on only 6 of 10 names, "all 10
canonical roles runtime-classified" is **not achievable** without the §9 redesign.

## 43. Authorization Guard Result

- Routes scanned: all `/v1/admin`-prefixed (and `/platform`, `/internal`, `/ops`,
  `/moderation`) routers across `app/engines/`.
- Findings: **0**. Exceptions: 0. Stale exceptions: 0.
- Result: `ADMIN_ROUTER_AUTH_GUARD_PASSED`. The MODULE-L5-01B platform-admin authorization
  class remains closed. (No new identity guards were added this sprint — the §9 blocker means
  the role/membership guards required by Section 21 would guard a to-be-redesigned surface.)

## 44. Test Results

- Identity-focused subset run this sprint: **168 passed, 0 failed** (`test_auth_login_fix`,
  `test_phase0d_password_security`, `test_module_l5_01_tenant_cross_tenant_idor`,
  `test_module_l5_01a_admin_finance_router_auth`, `test_final_l5_05l_admin_roles`).
- `test_versions.py`: 4 failed (below).
- Full backend suite unchanged from baseline (`10d8a4f`): 9318 passed / 1 skipped / 4 failed —
  no code changed this sprint, so no new pass/fail delta beyond the doc addition.

## 45. Four Pre-Existing Failure Re-evaluation

| Test | Current outcome | Cause | Identity relevance | Classification | Cert impact |
|---|---|---|---|---|---|
| `test_customer_expo_sdk` | FAIL | asserts Expo SDK 56; `mobile/customer-app/app.json` is 54.0.0 | none (mobile version string) | unrelated / dependency-drift | none |
| `test_customer_react_native` | FAIL | asserts RN version; concurrent mobile upgrade in progress | none | unrelated / dependency-drift | none |
| `test_customer_react` | FAIL | asserts React version | none | unrelated / dependency-drift | none |
| `test_customer_app_json_sdk_version` | FAIL | `app.json` sdkVersion 54.0.0 vs asserted 56.0.0 | none | unrelated / dependency-drift | none |

Re-checked, not blindly inherited: all four assert `mobile/customer-app` package/SDK version
strings owned by a concurrent, unrelated session; none touch auth, roles, sessions, tokens, or
any identity surface. **Confirmed still genuinely unrelated.**

## 46. Regression Assessment

Zero sprint-attributable regressions — this sprint made no code changes (only added this
report). Guard still passes; identity subset still green.

## 47. Changes Made

- Added `docs/module-l5/MODULE_L5_01C_FINAL_REPORT.md` (this document).
- No code changes. The genuine bounded identity work (role-registry reconciliation) is
  precisely the work gated behind the §9 architecture blocker and cannot be done safely in
  isolation — a half-reconciliation of one of the three registries would risk introducing the
  very inconsistency/lockout bugs the mission forbids.

## 48. Files Changed

- `docs/module-l5/MODULE_L5_01C_FINAL_REPORT.md` (new).

## 49. Remaining Blockers

**BLK-01C-1 — Identity role & membership architecture reconciliation**
- Category: **ARCHITECTURE**
- Severity: HIGH (certification-blocking; not a live security defect — the system is coherent
  and secure under its own role model)
- Affected Identity flow: role definition/enforcement, custom roles, ABAC, tenant membership,
  tenant switching, all-10-role runtime classification, 40-layer matrix.
- Affected roles: all — specifically the 4 required-but-absent named roles (`platform_admin`,
  `support_admin`, `tenant_admin`, `manager`) and the multi-membership user model.
- Exact evidence: three divergent role registries (`app/core/permissions.py::ROLE_PERMISSIONS`
  = 10 keys none of which are `platform_admin`/`support_admin`/`tenant_admin`/`manager`;
  `app/engines/auth/constants.py::ROLES` = 5 stale keys; `app/engines/roles_permissions/
  service.py` = a 9-name display set using yet-different naming). No `TenantMembership` table;
  `User.tenant_id` single column; grep for membership/switch code → 0 files. No custom-role or
  ABAC subsystem.
- Why it could not safely be completed: unifying enforced role strings across live user rows +
  all consumers, adding 4 named roles with permission maps, and introducing a tenant-membership
  schema with switching/token changes is a major, high-risk migration; performing it under one
  sprint's time pressure would risk lockouts and privilege-escalation and violate the mission's
  "unsafe to infer" / "do not weaken controls" constraints.
- Exact prerequisite: an explicit product/architecture decision on (a) the single canonical
  role set and its mapping to the required names, and (b) whether ServiceOS adopts a
  multi-tenant-membership identity model — followed by a dedicated migration sprint.
- Certification impact: blocks `IDENTITY_L5_PROVEN`.

## 50. Final Identity Level 5 Decision

**Identity & Access is NOT Level 5 proven.** The authentication, session, token, OTP, MFA,
lockout, password-lifecycle, login-history, and platform-admin-authorization layers are
implemented and sound (the MODULE-L5-01B authorization class remains closed at 0 findings).
However, the role model (three competing registries, four required roles absent), the absence
of custom-roles/ABAC, and the absence of a multi-tenant-membership + switching model make the
certification's own acceptance criteria unsatisfiable without a major, unsafe-to-rush identity
redesign. Status: **`NOT_PROVEN_ARCHITECTURE_BLOCKER`**.

## 51. Next Action

Identity & Access is not Level 5 proven. **Do not begin MODULE-L5-02.** Complete only the
explicitly evidenced blocker work: a dedicated identity role-model + tenant-membership
reconciliation/redesign sprint (BLK-01C-1) that (1) collapses the three role registries into
one enforced canonical set, (2) resolves the naming against the required 10-role list, and
(3) decides and, if adopted, migrates to a multi-tenant-membership model with switching —
after which a re-run of this certification can honestly target `IDENTITY_L5_PROVEN`.
