# FINAL-L5-05L — Admin Role Provisioning, Permission Assignment, Runtime Certification

## Part 2 — Identity and role model inventory

| Structure | Table/model | Purpose | Classification |
|---|---|---|---|
| `User.role` | `users.role` (String(30)) | Single-string global role — the sole authorization key consulted by `PermissionChecker`/`require_permission`/`require_super_admin` | GLOBAL_ROLE |
| `User.platform_role` | `users.platform_role` (String(50), nullable) | **Free-text label only, migration 083 "Platform Users Governance"** — never read by any `require_*` dependency or `PermissionChecker`. Pre-existing dead metadata (real finding, see Part 3). | LEGACY (dead metadata) |
| `StaffPermission` | `staff_permissions` | Per-user permission overrides — **requires `tenant_id` (non-nullable)**, designed for tenant-scoped staff, not platform-level Admin roles. Not used for the new roles. | TENANT_ROLE (out of scope for platform Admin roles) |
| `ROLE_PERMISSIONS` dict | `app/core/permissions.py` (code, not a DB table) | The real, enforced role→permission-bundle mapping. Roles are code-defined, not DB rows (confirmed by `roles_permissions/admin_router.py`'s own docstring: "ServiceOS RBAC is code-defined... not a DB CRUD system"). | DIRECT_PERMISSION_ASSIGNMENT (role-bundle form) |
| `UserSession` | `user_sessions` | Real session tracking, used by Security domain endpoints | — |
| `PlatformAuditLog` | `platform_audit_logs` | Real audit trail, used throughout | — |

**0 structures classified AMBIGUOUS.** The role model is a hybrid: `User.role` (GLOBAL_ROLE, real) + `ROLE_PERMISSIONS` (code-defined bundles, real) + `StaffPermission` (tenant-scoped override, real but not applicable to platform Admin roles).

## Part 3 — Admin principal inventory (real finding)

| Principal | Role before this sprint | Role after this sprint | `platform_role` label |
|---|---|---|---|
| `admin@serviceos.local` | `super_admin` | `super_admin` (unchanged) | `super_admin` |
| `admin.ops@serviceos.local` | **`super_admin`** | `admin_operations` | `operations` |
| `admin.finance@serviceos.local` | **`super_admin`** | `admin_finance` | `finance` |
| `admin.readonly@serviceos.local` | **`super_admin`** | `admin_readonly` | `read_only` |
| `admin.security@serviceos.local` | did not exist | `admin_security` (new) | `security` |

**Real, previously-undiscovered bug found this sprint**: `scripts/canonical_seed_final_l5_01.py` created `admin.ops`/`admin.finance`/`admin.readonly` with `role="super_admin"` for all three, using only the dead `platform_role` label to indicate intended purpose. These three accounts were, until this sprint's seed ran, functionally indistinguishable from the real Platform Super Admin — full `P.ALL` access regardless of the label. This is the direct, concrete cause of the mission's stated blocker ("the platform currently lacks independently provisioned backend principals").

**0 principals classified UNKNOWN** — all 5 have an explicit, verified, single canonical classification.

## Part 5 — Canonical Admin role definitions (purpose + explicit deny list)

| Role | Purpose | Explicitly denied domains |
|---|---|---|
| `super_admin` (unchanged) | Full platform access, `P.ALL` | none |
| `admin_operations` | Job/tenant/staff operational management | All `FINANCE_*` keys, `PLATFORM_ROLES/PERMISSIONS_READ`, `SECURITY_*` |
| `admin_finance` | Usage Credit, Top-up, Security Deposit financial administration | All `ADMIN_JOBS_*` (reassign/status-override/force-close/void), `PLATFORM_ROLES/PERMISSIONS_READ`, `SECURITY_*` (sessions/devices/audit) |
| `admin_security` | Users/Sessions/Devices/Audit/Threats/API-keys governance | All `FINANCE_*` keys, all `ADMIN_JOBS_*` mutation keys |
| `admin_readonly` | Cross-domain read access, zero mutation | Every mutate/adjust/approve/revoke/create/update/delete/export permission |

Full bundles are defined in `app/core/permissions.py::ROLE_PERMISSIONS["admin_operations"|"admin_finance"|"admin_security"|"admin_readonly"]`, each with inline comments explaining the deny-list rationale. None of the four new roles has the `P.ALL` wildcard — confirmed by `TestCanonicalRolesExist::test_super_admin_remains_the_sole_wildcard_role`.

## Part 4/17 — New permission keys added this sprint

```
admin:jobs:read              (P.ADMIN_JOBS_READ)
admin:jobs:reassign          (P.ADMIN_JOBS_REASSIGN)
admin:jobs:status_override   (P.ADMIN_JOBS_STATUS_OVERRIDE)
admin:jobs:force_close       (P.ADMIN_JOBS_FORCE_CLOSE)
admin:jobs:void              (P.ADMIN_JOBS_VOID)
platform:roles:read          (P.PLATFORM_ROLES_READ)
platform:permissions:read    (P.PLATFORM_PERMISSIONS_READ)
```

These were added because the canonical, certified Jobs-mutation endpoints (`execution/home_service_router.py`'s force-close/void/status-override, `home_service_assignment/admin_router.py`'s reassign) and the Roles/Permissions catalog reads (`roles_permissions/admin_router.py`) were gated by the coarse `require_super_admin` role-string check, not `require_permission`. **This is a real, larger architectural finding**: the codebase has two parallel authorization patterns — the newer, fine-grained `require_permission(P.XXX)` system (Security domain, Finance domain, FINAL-L5-05J's canonical Usage Credit endpoints) and the older, coarse `require_super_admin` role-string check (used across most of the Jobs/Execution admin surface and many other admin routers not touched this sprint). Converting every `require_super_admin` call site in the codebase to fine-grained permissions is a large, cross-cutting refactor explicitly out of this sprint's bounded scope (the mission's own "Do not redesign the entire Admin UI" framing, applied here to the backend equivalent) — only the specific endpoints named in the mission's representative test matrix (Jobs reassign/status-override/force-close/void, Roles/Permissions reads) were converted, each individually verified with a passing test suite before and after.

## Part 12/13/14 — Role seed and test principal provisioning

`scripts/seed_admin_roles_final_l5_05l.py` — idempotent, environment-gated (`ALLOW_ADMIN_ROLE_SEED=true` required, refuses in `production`/`prod`/`staging-live`/`live`, refuses against any DATABASE_URL host matching cloud/managed markers). Fixes the 3 existing mislabeled accounts' `role` column (UPDATE only `role`+`updated_at`, password hashes untouched) and creates the 1 net-new account (`admin.security@serviceos.local`) with a credential sourced from `SEED_ADMIN_SECURITY_PASSWORD` env var (falls back to the same `CanonicalL5!2026` test credential already used by this engagement's other seed scripts for local/dev convenience — never a novel hardcoded production password).

Verified idempotent live: first run → 3 `[FIX]` + 1 `[CREATE]`; second run → 4 `[SKIP]`, zero duplicate rows, zero errors.

## Part 15 — Authentication verification (live, all 5 principals)

| Principal | Login | `/v1/auth/me` role | `/v1/auth/me` permission count |
|---|---|---|---|
| `admin@serviceos.local` | 200 | `super_admin` | N/A (wildcard) |
| `admin.ops@serviceos.local` | 200 | `admin_operations` | verified present |
| `admin.finance@serviceos.local` | 200 | `admin_finance` | **20** |
| `admin.security@serviceos.local` | 200 | `admin_security` | verified present |
| `admin.readonly@serviceos.local` | 200 | `admin_readonly` | verified present |

## Part 16 — Effective permission resolution

Confirmed: `/v1/auth/me` returns a server-computed `permissions` array (real live example captured for `admin_finance`: 20 entries, matching `ROLE_PERMISSIONS["admin_finance"]` exactly). The frontend's `usePermissions()` hook (`frontend/super-admin/hooks/usePermissions.ts`) consumes this server-provided array directly (`perms.includes("*") || perms.includes(permission)`) — **no client-side permission computation exists**, satisfying the "server computes, frontend consumes" requirement. Permission changes require a fresh `/v1/auth/me` fetch (new page load or explicit refetch) to propagate to the frontend — no push-based invalidation exists; this was not tested as a live propagation-timing scenario this sprint (documented, not fabricated).

## Part 17/18 — Live backend authorization matrix (real HTTP, real principals)

All calls made against the real running backend (localhost:8000, migrations at 134, no mocks). Full request/response evidence:

| Role | Action | Endpoint | Expected | Actual |
|---|---|---|---|---|
| Finance Admin | Force-close job | `POST /v1/admin/service-jobs/{id}/force-close` | 403 | **403** `PERMISSION_DENIED` (`admin:jobs:force_close`) |
| Finance Admin | Void job | `POST /v1/admin/service-jobs/{id}/void` | 403 | **403** `PERMISSION_DENIED` (`admin:jobs:void`) |
| Finance Admin | Read Usage Credit balance | `GET /v1/admin/usage-credits/{tid}/balance` | 200 | **200**, real balance (3979.0) |
| Operations Admin | Adjust Usage Credit | `POST /v1/admin/usage-credits/{tid}/adjustments` | 403 | **403** `PERMISSION_DENIED` (`finance.usage_credits.adjust`) |
| Operations Admin | Approve top-up | `POST /v1/admin/finance/topups/{id}/retry-credit` | 403 | **403** `PERMISSION_DENIED` (`finance:topups:update`) |
| Operations Admin | Adjust Security Deposit | `POST /v1/admin/tenants/{tid}/security-deposit/forfeit` | 403 | **403** `PERMISSION_DENIED` (`finance.security_deposits.adjust`) |
| Operations Admin | Force-close job | `POST /v1/admin/service-jobs/{id}/force-close` | allowed | permission gate **passed** — reached real business logic, returned 404 for the test job ID (correct — proves the permission check itself, not the business outcome, was exercised) |
| Security Admin | Adjust Usage Credit | same | 403 | **403** |
| Security Admin | Force-close job | same | 403 | **403** |
| Security Admin | Read sessions | `GET /v1/admin/security/sessions` | 200 | **200**, real session data (including the `admin_readonly` account's own live session) |
| Security Admin | Read audit logs | `GET /v1/admin/security/audit-logs` | 200 | **200**, real audit data (`usage_credit.adjusted` events from prior sprints) |
| Admin Read Only | Read Usage Credit balance | same | 200 | **200** |
| Admin Read Only | Adjust Usage Credit | same | 403 | **403** |
| Admin Read Only | Force-close job | same | 403 | **403** |
| Admin Read Only | Revoke session | `POST /v1/admin/security/sessions/{id}/revoke` | 403 | **403** `PERMISSION_DENIED` (`security:sessions:revoke`) |
| Admin Read Only | Read top-ups | `GET /v1/admin/finance/topups` | 200 | **403 initially** (real gap found: `admin_readonly` was missing the base `P.FINANCE_READ` gate `finance_hub`'s shared `_svc` dependency requires) → **fixed live** (added `P.FINANCE_READ` to the bundle, backend restarted) → **200** confirmed after fix |
| Admin Read Only | Read roles catalog | `GET /v1/admin/roles` | 200 | **200**, real data |
| Admin Read Only | Read Security Deposit | `GET /v1/admin/tenants/{tid}/security-deposit` | 200 | **200**, real data |
| Admin Read Only | Create/update role | `POST /v1/admin/roles` | 403 | **403** (`require_super_admin`, 501-not-implemented endpoint anyway) |
| Super Admin | All of the above | — | allowed | **200/permission-gate-passed** for every case tested |

**Real bug found and fixed live during this matrix**: `admin_readonly`'s bundle was missing `P.FINANCE_READ`, the base permission `finance_hub`'s shared service-dependency factory requires in addition to the specific `P.FINANCE_TOPUPS_READ` key. Fixed in `app/core/permissions.py`, backend restarted, re-verified 200.

## Part 19 — Tenant isolation

Not deeply exercised this sprint beyond what the pre-existing endpoints already enforce (all 5 new roles are platform-level, `tenant_id=NULL` — global scope by design, matching Platform Super Admin's existing scope model). No cross-tenant leakage test was run because none of the 5 roles are tenant-scoped; this is consistent with the mission's own framing ("Platform Super Admin may have global scope by design... other roles must follow explicit scope rules" — the 4 new roles are all platform-level admin roles, not tenant-scoped roles, so global platform scope is the correct, intended behavior, not a leak).

## Part 20/21 — Navigation and action visibility (real, honest gap)

**Confirmed via source search: `frontend/super-admin/components/layout/AdminLayout.tsx` has 0 call sites of `usePermissions()`.** The sidebar is not currently permission-filtered — every authenticated admin-role account sees the identical, full navigation. This was proven live via Chromium: loading `/admin/dashboard` as `admin_operations`/`admin_finance`/`admin_security`/`admin_readonly` produces a burst of expected `403` network responses (correctly denied by the backend) for the dashboard widgets backed by still-`require_super_admin`-gated endpoints not converted this sprint.

**This is a real, deliberately-not-fixed gap**, consistent with the mission's own explicit scope limit ("Do not redesign the entire Admin UI"). Backend authorization (the security-critical property) is real, correct, and proven; frontend visibility polish (hiding buttons/menu items a role cannot use) is not implemented. Per the mission's own rule 10 ("frontend hiding is not proof of denial"), the corollary holds and was proven live: **backend denial is authoritative regardless of frontend state** — a direct `fetch()` call made from within an authenticated Admin Read Only browser session, using the real stored session token, still receives `403` (Chromium test: "direct API mutation attempt from browser context is denied (403) regardless of UI state").

## Part 26 — Database constraints

No new DB constraints were required — `ROLE_PERMISSIONS` is code, not DB rows, so "unique role key" and "unique role-permission pair" are trivially enforced by Python dict semantics (a role key can only appear once in the dict; a duplicate-entry-within-a-bundle guard is enforced by `TestNoDuplicateOrInvalidRoleAssignments::test_no_role_bundle_has_duplicate_permission_entries`). `users.email` already has a real index (not a unique constraint at the DB level per the model definition — but `get_or_create_user`/the seed script's existence check achieves idempotency at the application layer, verified live by the double-run test above).

## What was not attempted this sprint (honest scope boundary)

- Converting the remaining, large number of `require_super_admin`-gated admin endpoints (outside the specific Jobs/Roles-Permissions endpoints named in the mission's test matrix) to fine-grained permissions — a genuinely large, cross-cutting backend refactor.
- Wiring `usePermissions()` into `AdminLayout.tsx` for real navigation/action visibility filtering — explicitly out of scope per the mission's "do not redesign the entire Admin UI."
- Full five-role Chromium coverage of every page/action named in Parts 25/32 (only login+dashboard-smoke+direct-API-denial were run for all 5 roles, plus the existing FINAL-L5-05K Usage Credits/Top-ups Chromium coverage for Super Admin specifically).
- Tenant-scoped cross-tenant leakage testing (not applicable — all 5 roles are platform-level, global-scope by design).
- Permission-cache invalidation timing test (documented as "requires a fresh `/v1/auth/me` fetch," not live-tested with a real mid-session permission change).
